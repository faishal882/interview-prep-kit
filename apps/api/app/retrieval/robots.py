"""robots.txt handling per RFC 9309 (minimal: fetch once, parse Disallow, honour crawl-delay)."""
from __future__ import annotations

import re
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser


_cache: dict[str, tuple[RobotFileParser, float]] = {}


def robots_url(page_url: str) -> str:
    p = urlparse(page_url)
    return f"{p.scheme}://{p.netloc}/robots.txt"


def allowed(page_url: str, user_agent: str, fetch_text) -> tuple[bool, str]:
    """fetch_text(url) -> str | None. Returns (allowed, reason)."""
    host = urlparse(page_url).netloc
    if host not in _cache or time.time() - _cache[host][1] > 3600:
        rp = RobotFileParser()
        try:
            txt = fetch_text(robots_url(page_url))
        except Exception:
            txt = None
        if txt is None:
            rp.parse([])
        else:
            rp.parse(txt.splitlines())
        _cache[host] = (rp, time.time())
    rp = _cache[host][0]
    try:
        ok = rp.can_fetch(user_agent, page_url)
    except Exception:
        ok = True
    return (True, "") if ok else (False, "robots")


def crawl_delay(page_url: str) -> float:
    host = urlparse(page_url).netloc
    entry = _cache.get(host)
    if not entry:
        return 0.0
    try:
        d = entry[0].crawl_delay("*")
        return float(d) if d else 0.0
    except Exception:
        return 0.0
