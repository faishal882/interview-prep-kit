"""Safe fetcher: guard + robots + content-type/size/time limits + cache + backoff."""
from __future__ import annotations

import time
from urllib.parse import urlparse

import httpx

from .robots import allowed as robots_allowed
from .url_guard import validate_url

ALLOWED_TYPES = ("text/html", "text/plain", "application/xhtml+xml")
MAX_BYTES = 2 * 1024 * 1024
USER_AGENT = "trao-interview-prep/1.0 (+research)"
_cache: dict[str, dict] = {}
_last_hit: dict[str, float] = {}


def _host(url: str) -> str:
    return urlparse(url).netloc


async def fetch(
    url: str,
    *,
    allow_private: bool = False,
    client: httpx.AsyncClient | None = None,
    record: list[dict] | None = None,
    timeout_s: float = 15.0,
) -> dict | None:
    """Return {'url','final_url','text','links'} or None (skip recorded)."""
    if url in _cache:
        return _cache[url]
    ok, reason = validate_url(url, allow_private=allow_private)
    if not ok:
        _skip(record, url, reason)
        return None
    # per-host rate limit 1 rps
    host = _host(url)
    wait = 1.0 - (time.time() - _last_hit.get(host, 0))
    if wait > 0:
        import asyncio
        await asyncio.sleep(wait)
    # robots
    try:
        r_ok, r_reason = robots_allowed(url, USER_AGENT, lambda u: None)
        if not r_ok:
            _skip(record, url, r_reason)
            return None
    except Exception:
        pass
    own = client is not None
    cli = client or httpx.AsyncClient(timeout=httpx.Timeout(timeout_s, connect=5.0), max_redirects=3, headers={"User-Agent": USER_AGENT})
    try:
        last_exc: Exception | None = None
        for _attempt in range(3):
            try:
                resp = await cli.get(url)
                # redirect re-validation
                if str(resp.url) != url:
                    ok2, reason2 = validate_url(str(resp.url), allow_private=allow_private)
                    if not ok2:
                        _skip(record, url, "redirect-private")
                        return None
                if resp.status_code in (404, 410):
                    _skip(record, url, f"http-{resp.status_code}")
                    return None
                if resp.status_code >= 400:
                    last_exc = RuntimeError(f"http-{resp.status_code}")
                    import asyncio
                    await asyncio.sleep(0.5)
                    continue
                ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
                if ctype and ctype not in ALLOWED_TYPES:
                    _skip(record, url, "content-type")
                    return None
                body = resp.content
                if len(body) > MAX_BYTES:
                    _skip(record, url, "oversize")
                    return None
                text = resp.text
                links = _links(text, str(resp.url))
                page = {"url": url, "final_url": str(resp.url), "text": clean_text(text), "links": links}
                _cache[url] = page
                _last_hit[host] = time.time()
                return page
            except Exception as exc:
                last_exc = exc
                import asyncio
                await asyncio.sleep(0.5)
        _skip(record, url, f"fetch-failed: {last_exc}")
        return None
    finally:
        if not own:
            await cli.aclose()


def _skip(record: list[dict] | None, url: str, reason: str) -> None:
    if record is not None:
        record.append({"url": url, "reason": reason})


def clean_text(html: str) -> str:
    import re
    # strip scripts/styles, tags -> whitespace-collapsed text
    no_script = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", " ", no_script)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:20000]


def _links(html: str, base: str) -> list[dict]:
    import re
    from urllib.parse import urljoin
    out = []
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.S | re.I):
        href, anchor = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()[:200]
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        out.append({"url": urljoin(base, href), "anchor": anchor})
    return out
