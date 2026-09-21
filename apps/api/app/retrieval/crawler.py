"""Priority-queue crawler: public-suffix scope + exact ATS allowlist, one hop."""
from __future__ import annotations

import heapq
import ipaddress
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .link_ranker import score as rank_score
from .safe_fetch import fetch

# Hiring platforms recognised by exact domain (subdomains included) — never substring.
ATS_DOMAINS = ("greenhouse.io", "lever.co", "ashbyhq.com", "workable.com")

# Common multi-label public suffixes so e.g. a .co.uk company does not match
# every other .co.uk host. Full PSL intentionally not vendored.
MULTI_SUFFIXES = frozenset({
    "co.uk", "org.uk", "me.uk", "ac.uk", "gov.uk", "ltd.uk", "plc.uk", "net.uk", "sch.uk",
    "com.au", "net.au", "org.au", "edu.au", "gov.au", "asn.au", "id.au",
    "co.jp", "or.jp", "ne.jp", "ac.jp", "go.jp", "ed.jp", "gr.jp",
    "co.nz", "org.nz", "net.nz", "ac.nz", "govt.nz", "school.nz",
    "co.in", "org.in", "net.in", "gen.in", "firm.in", "gov.in", "ac.in",
    "com.br", "net.br", "org.br", "gov.br", "edu.br",
    "co.za", "org.za", "net.za", "ac.za", "gov.za",
    "com.cn", "net.cn", "org.cn", "gov.cn", "edu.cn",
    "com.tw", "org.tw", "net.tw", "edu.tw", "gov.tw",
    "co.kr", "or.kr", "ne.kr", "go.kr", "ac.kr",
    "com.mx", "org.mx", "gob.mx", "edu.mx",
    "com.ar", "org.ar", "net.ar", "gov.ar", "edu.ar",
    "com.sg", "org.sg", "net.sg", "edu.sg", "gov.sg",
    "com.hk", "org.hk", "net.hk", "edu.hk", "gov.hk",
    "co.th", "or.th", "go.th", "ac.th", "net.th",
    "com.ph", "net.ph", "org.ph", "gov.ph", "edu.ph",
    "com.my", "net.my", "org.my", "gov.my", "edu.my",
    "co.id", "or.id", "go.id", "ac.id", "net.id",
    "com.vn", "net.vn", "org.vn", "edu.vn", "gov.vn",
    "com.tr", "net.tr", "org.tr", "gov.tr", "edu.tr",
    "com.eg", "net.eg", "org.eg", "edu.eg", "gov.eg",
    "com.sa", "net.sa", "org.sa", "gov.sa", "edu.sa",
    "co.il", "org.il", "net.il", "gov.il", "ac.il",
    "co.ke", "or.ke", "ne.ke", "ac.ke", "go.ke", "sc.ke",
    "co.ug", "or.ug", "ne.ug", "ac.ug", "go.ug", "sc.ug",
    "com.et", "com.gh", "com.ng", "org.ng", "gov.ng", "edu.ng", "net.ng", "sch.ng",
    "com.om", "com.qa", "co.mz", "org.mz", "gov.mz", "ac.mz",
    "co.bw", "org.bw", "gov.bw", "ac.bw",
    "co.zw", "org.zw", "gov.zw", "ac.zw",
    "co.zm", "org.zm", "gov.zm", "ac.zm", "sch.zm",
    "co.tz", "or.tz", "ne.tz", "ac.tz", "go.tz", "com.tz", "me.tz",
})

MAX_LINKS_PER_PAGE = 200


def registrable_domain(host: str) -> str:
    """Registrable domain for scope checks (public-suffix aware, no network)."""
    h = (host or "").rstrip(".").lower().split("@")[-1].split(":")[0]
    try:
        ipaddress.ip_address(h)
        return h
    except ValueError:
        pass
    labels = [l for l in h.split(".") if l]
    if len(labels) < 2:
        return h
    two = ".".join(labels[-2:])
    if two in MULTI_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])
    return two


def is_hiring_platform(host: str) -> bool:
    """Exact-domain ATS allowlist — never a substring match."""
    h = (host or "").rstrip(".").lower().split(":")[0]
    return any(h == a or h.endswith("." + a) for a in ATS_DOMAINS)


def normalize_url(url: str) -> str:
    """Canonical form so trivially different URLs are fetched once.

    Note: trailing slashes are NOT stripped here — /page/ and /page can be
    different resources. Use dedupe_key() for seen-set comparisons.
    """
    p = urlparse(url)
    scheme = p.scheme.lower()
    host = (p.hostname or "").rstrip(".").lower()
    port = p.port
    default = 443 if scheme == "https" else 80
    netloc = host if port in (None, default) else f"{host}:{port}"
    path = p.path or "/"
    query = urlencode(sorted(parse_qsl(p.query, keep_blank_values=True)))
    return urlunparse((scheme, netloc, path, "", query, ""))


def dedupe_key(url: str) -> str:
    """Seen-set key: normalized, with a trailing slash ignored for non-root paths."""
    n = normalize_url(url)
    p = urlparse(n)
    if len(p.path) > 1 and p.path.endswith("/"):
        n = urlunparse((p.scheme, p.netloc, p.path.rstrip("/"), "", p.query, ""))
    return n


async def crawl(
    start_url: str,
    *,
    budget: int = 12,
    depth: int = 2,
    allow_private: bool = False,
    production: bool = False,
    client=None,
    cache=None,
    research_log: dict | None = None,
) -> tuple[list[dict], list[str]]:
    """Return (pages, pages_used_urls). Skips recorded into research_log['fetches'].

    The budget counts pages retrieved, not URLs queued or skipped. A shared
    cache may be passed so retried generations do not re-fetch pages.
    """
    skips: list[dict] = []
    pages: list[dict] = []
    seen: set[str] = set()
    start = normalize_url(start_url)
    base_host = urlparse(start).hostname or ""
    base_reg = registrable_domain(base_host)
    heap: list[tuple[float, int, str, str]] = [(0.0, 0, start, "")]
    while heap and len(pages) < budget:
        neg, d, url, _ctx = heapq.heappop(heap)
        key = dedupe_key(url)
        if key in seen:
            continue
        seen.add(key)
        if d > 0:
            h = urlparse(url).hostname or ""
            same = registrable_domain(h) == base_reg or (
                base_host in ("localhost", "127.0.0.1") and h == base_host
            )
            if not (same or is_hiring_platform(h)):
                skips.append({"url": url, "reason": "off-domain"})
                continue
        page = await fetch(url, allow_private=allow_private, production=production,
                           client=client, record=skips, cache=cache)
        if page is None:
            continue
        pages.append({**page, "depth": d})
        if d < depth:
            for link in page.get("links", [])[:MAX_LINKS_PER_PAGE]:
                lu = normalize_url(link["url"])
                if dedupe_key(lu) in seen:
                    continue
                s = rank_score(lu, link.get("anchor", ""))
                heapq.heappush(heap, (-s, d + 1, lu, link.get("anchor", "")))
    if research_log is not None:
        research_log.setdefault("fetches", []).extend(skips)
        research_log.setdefault("pages_fetched", []).extend([p["final_url"] for p in pages])
    return pages, [p["final_url"] for p in pages]
