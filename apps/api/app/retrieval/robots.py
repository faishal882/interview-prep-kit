"""robots.txt handling per RFC 9309 with the specified semantics.

- robots.txt is actually fetched per host and cached with expiry.
- Missing file (404 / other 4xx) allows crawling.
- Server error (5xx) or an unreachable file (network error, timeout) disallows.
- Crawl delay is parsed and honoured by the caller.
"""
from __future__ import annotations

import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

ROBOTS_TTL_S = 3600
ROBOTS_MAX_HOSTS = 1000

# host -> (parser, allows_everything_hint, fetched_at)
_cache: dict[str, tuple[RobotFileParser | None, bool, float]] = {}


def robots_url(page_url: str) -> str:
    p = urlparse(page_url)
    return f"{p.scheme}://{p.netloc}/robots.txt"


def _parse(text: str) -> RobotFileParser:
    rp = RobotFileParser()
    rp.parse(text.splitlines())
    return rp


def decide(status: int | None, text: str | None, page_url: str, user_agent: str) -> tuple[bool, str]:
    """Pure decision from a robots fetch outcome. status None = unreachable."""
    if status is None:
        return False, "robots-unreachable"
    if status >= 500:
        return False, "robots-error"
    if status == 200 and text:
        try:
            ok = _parse(text).can_fetch(user_agent, page_url)
        except Exception:
            ok = True
        return (True, "") if ok else (False, "robots")
    # missing (404) or any other 4xx, or empty 200: allow
    return True, ""


async def check(page_url: str, user_agent: str, fetch_status) -> tuple[bool, str, float]:
    """fetch_status(url) -> (status|None, text|None). Returns (allowed, reason, crawl_delay_s)."""
    host = urlparse(page_url).netloc
    now = time.time()
    entry = _cache.get(host)
    if entry is None or now - entry[2] > ROBOTS_TTL_S:
        try:
            status, text = await fetch_status(robots_url(page_url))
        except Exception:
            status, text = None, None
        rp = _parse(text) if status == 200 and text else None
        entry = (rp, status, now)
        _cache[host] = entry
        if len(_cache) > ROBOTS_MAX_HOSTS:
            oldest = min(_cache, key=lambda h: _cache[h][2])
            del _cache[oldest]
    rp, status, _ = entry
    allowed, reason = decide(status, None, page_url, user_agent) if rp is None else _decide_parsed(rp, page_url, user_agent)
    delay = 0.0
    if rp is not None:
        try:
            d = rp.crawl_delay("*") or rp.crawl_delay(user_agent)
            delay = float(d) if d else 0.0
        except Exception:
            delay = 0.0
    return allowed, reason, delay


def _decide_parsed(rp: RobotFileParser, page_url: str, user_agent: str) -> tuple[bool, str]:
    try:
        ok = rp.can_fetch(user_agent, page_url)
    except Exception:
        ok = True
    return (True, "") if ok else (False, "robots")


def allowed(page_url: str, user_agent: str, fetch_text) -> tuple[bool, str]:
    """Legacy sync helper over raw text (None = missing → allow). Kept for tests."""
    host = urlparse(page_url).netloc
    try:
        txt = fetch_text(robots_url(page_url))
    except Exception:
        return False, "robots-unreachable"
    if txt is None:
        return True, ""
    try:
        ok = _parse(txt).can_fetch(user_agent, page_url)
    except Exception:
        ok = True
    return (True, "") if ok else (False, "robots")


def crawl_delay(page_url: str) -> float:
    host = urlparse(page_url).netloc
    entry = _cache.get(host)
    if not entry or entry[0] is None:
        return 0.0
    try:
        d = entry[0].crawl_delay("*")
        return float(d) if d else 0.0
    except Exception:
        return 0.0


def clear_cache() -> None:
    _cache.clear()
