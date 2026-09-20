"""Priority-queue crawler: same registrable domain + ATS allowlist one hop."""
from __future__ import annotations

import heapq
from urllib.parse import urlparse

from .link_ranker import score as rank_score
from .safe_fetch import fetch

ATS_HOSTS = ("greenhouse.io", "lever.co", "ashbyhq.com", "workable.com")


def _registrable(host: str) -> str:
    parts = host.lower().split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host.lower()


async def crawl(
    start_url: str,
    *,
    budget: int = 12,
    depth: int = 2,
    allow_private: bool = False,
    client=None,
    research_log: dict | None = None,
) -> tuple[list[dict], list[str]]:
    """Return (pages, pages_used_urls). Skips recorded into research_log['fetches']."""
    skips: list[dict] = []
    pages: list[dict] = []
    seen: set[str] = set()
    base_host = urlparse(start_url).netloc
    base_reg = _registrable(base_host)
    # heap of (-score, depth, url, context)
    heap: list[tuple[float, int, str, str]] = [(0.0, 0, start_url, "")]
    while heap and len(pages) + len(seen) < budget + len(pages):
        neg, d, url, _ctx = heapq.heappop(heap)
        if url in seen or len(pages) >= budget:
            continue
        seen.add(url)
        if d > 0:
            h = urlparse(url).netloc
            same = _registrable(h) == base_reg or (base_host in ("localhost", "127.0.0.1") and h == base_host)
            ats = any(a in h for a in ATS_HOSTS)
            if not (same or ats):
                skips.append({"url": url, "reason": "off-domain"})
                continue
        page = await fetch(url, allow_private=allow_private, client=client, record=skips)
        if page is None:
            continue
        pages.append({**page, "depth": d})
        if d < depth:
            for link in page.get("links", []):
                lu = link["url"]
                if lu in seen:
                    continue
                s = rank_score(lu, link.get("anchor", ""))
                heapq.heappush(heap, (-s, d + 1, lu, link.get("anchor", "")))
    if research_log is not None:
        research_log.setdefault("fetches", []).extend(skips)
        research_log.setdefault("pages_fetched", []).extend([p["final_url"] for p in pages])
    return pages, [p["final_url"] for p in pages]
