"""Safe fetcher: guard + robots + manual redirects + streamed size cap + cache.

Every URL, including each redirect hop, is validated before it is requested.
Bodies stream and abort mid-download past the size limit. Outcomes are always
a page or a recorded skip reason.
"""
from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from urllib.parse import urljoin, urlparse

import httpx

from . import robots as robots_mod
from .url_guard import validate_url

ALLOWED_TYPES = ("text/html", "text/plain", "application/xhtml+xml")
MAX_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
MAX_LINKS_PER_PAGE = 200
USER_AGENT = "trao-interview-prep/1.0 (+research)"
HOST_MIN_INTERVAL_S = 1.0
CRAWL_DELAY_CAP_S = 10.0
CACHE_MAX_PAGES = 500
CACHE_TTL_S = 3600


class PageCache:
    """Bounded, expiring page cache (LRU-evicting)."""

    def __init__(self, maxsize: int = CACHE_MAX_PAGES, ttl_s: float = CACHE_TTL_S):
        self._data: OrderedDict[str, tuple[dict, float]] = OrderedDict()
        self._maxsize = maxsize
        self._ttl = ttl_s

    def get(self, key: str) -> dict | None:
        hit = self._data.get(key)
        if hit is None:
            return None
        page, at = hit
        if time.time() - at > self._ttl:
            self._data.pop(key, None)
            return None
        self._data.move_to_end(key)
        return page

    def put(self, key: str, page: dict) -> None:
        self._data[key] = (page, time.time())
        self._data.move_to_end(key)
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)


_cache = PageCache()
_host_locks: dict[str, asyncio.Lock] = {}
_host_last: dict[str, float] = {}
_locks_guard = asyncio.Lock()
_rate_interval_s = HOST_MIN_INTERVAL_S


async def _host_lock(host: str) -> asyncio.Lock:
    async with _locks_guard:
        lock = _host_locks.get(host)
        if lock is None:
            lock = asyncio.Lock()
            _host_locks[host] = lock
        return lock


def _host(url: str) -> str:
    return urlparse(url).netloc.lower()


def resolve_redirect(current_url: str, location: str | None) -> tuple[bool, str]:
    """Resolve a redirect target; (ok, url-or-reason) without requesting it."""
    if not location:
        return False, "redirect-no-location"
    target = urljoin(current_url, location)
    if urlparse(target).scheme not in ("http", "https"):
        return False, "redirect-scheme"
    return True, target


def _skip(record: list[dict] | None, url: str, reason: str) -> None:
    if record is not None:
        record.append({"url": url, "reason": reason})


async def _robots_fetch(url: str, client: httpx.AsyncClient, timeout_s: float) -> tuple[int | None, str | None]:
    try:
        resp = await client.get(url, timeout=timeout_s)
        ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
        if resp.status_code == 200 and ctype not in ("text/plain", ""):
            return resp.status_code, None
        body = resp.content
        if len(body) > 64 * 1024:
            return resp.status_code, None
        return resp.status_code, resp.text
    except Exception:
        return None, None


async def fetch(
    url: str,
    *,
    allow_private: bool = False,
    production: bool = False,
    client: httpx.AsyncClient | None = None,
    record: list[dict] | None = None,
    timeout_s: float = 15.0,
    cache: PageCache | None = None,
) -> dict | None:
    """Return {'url','final_url','text','links'} or None (skip recorded)."""
    from .crawler import normalize_url

    store = cache if cache is not None else _cache
    start = normalize_url(url)
    hit = store.get(start)
    if hit is not None:
        return hit
    ok, reason = validate_url(start, allow_private=allow_private, production=production)
    if not ok:
        _skip(record, start, reason)
        return None

    own = client is None
    cli = client or httpx.AsyncClient(
        timeout=httpx.Timeout(timeout_s, connect=5.0),
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT},
    )
    try:
        # robots: fetched per host, validated like any other URL
        async def _robots_status(u: str) -> tuple[int | None, str | None]:
            rok, _ = validate_url(u, allow_private=allow_private, production=production)
            if not rok:
                return None, None
            return await _robots_fetch(u, cli, min(timeout_s, 10.0))

        try:
            r_ok, r_reason, r_delay = await robots_mod.check(start, USER_AGENT, _robots_status)
        except Exception:
            r_ok, r_reason, r_delay = True, "", 0.0
        if not r_ok:
            _skip(record, start, r_reason)
            return None

        host = _host(start)
        lock = await _host_lock(host)
        async with lock:
            # per-host rate limit, safe under concurrency via the host lock
            wait = _rate_interval_s - (time.time() - _host_last.get(host, 0.0))
            if wait > 0:
                await asyncio.sleep(wait)
            if r_delay > 0:
                await asyncio.sleep(min(r_delay, CRAWL_DELAY_CAP_S))
            page = await _get_with_redirects(
                start, cli=cli, allow_private=allow_private, production=production,
                timeout_s=timeout_s, record=record,
            )
            _host_last[host] = time.time()
            if page is not None:
                store.put(start, page)
            return page
    finally:
        if own:
            await cli.aclose()


async def _get_with_redirects(
    url: str, *, cli: httpx.AsyncClient, allow_private: bool, production: bool,
    timeout_s: float, record: list[dict] | None,
) -> dict | None:
    current = url
    for _hop in range(MAX_REDIRECTS + 1):
        try:
            async with cli.stream("GET", current, timeout=timeout_s) as resp:
                if resp.status_code in (301, 302, 303, 307, 308):
                    ok, target_or_reason = resolve_redirect(current, resp.headers.get("location"))
                    if not ok:
                        _skip(record, current, target_or_reason)
                        return None
                    vok, vreason = validate_url(target_or_reason, allow_private=allow_private, production=production)
                    if not vok:
                        _skip(record, target_or_reason, f"redirect-{vreason}")
                        return None
                    current = target_or_reason
                    continue
                if resp.status_code in (404, 410):
                    _skip(record, current, f"http-{resp.status_code}")
                    return None
                if resp.status_code >= 400:
                    _skip(record, current, f"http-{resp.status_code}")
                    return None
                ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
                if ctype and ctype not in ALLOWED_TYPES:
                    _skip(record, current, "content-type")
                    return None
                # stream with mid-download cutoff
                chunks: list[bytes] = []
                size = 0
                async for chunk in resp.aiter_bytes(65536):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        _skip(record, current, "oversize")
                        return None
                    chunks.append(chunk)
                raw_html = b"".join(chunks).decode(resp.charset_encoding or "utf-8", errors="replace")
                links = _links(raw_html, current)
                return {
                    "url": url, "final_url": current, "text": clean_text(raw_html),
                    "links": links, "title": _title(raw_html), "site_name": _site_name(raw_html),
                }
        except Exception as exc:
            _skip(record, current, f"fetch-failed: {type(exc).__name__}")
            return None
    _skip(record, current, "too-many-redirects")
    return None


def clean_text(html: str) -> str:
    import re
    no_script = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", " ", no_script)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:20000]


def _title(html: str) -> str:
    import re
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    if not m:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()[:200]


def _site_name(html: str) -> str:
    import re
    m = re.search(
        r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if not m:
        m = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:site_name["\']', html, re.I)
    return (m.group(1).strip()[:200] if m else "")


def _links(html: str, base: str) -> list[dict]:
    import re
    from urllib.parse import urljoin
    out = []
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.S | re.I):
        if len(out) >= MAX_LINKS_PER_PAGE:
            break
        href, anchor = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()[:200]
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        out.append({"url": urljoin(base, href), "anchor": anchor})
    return out
