"""Hacker News discussion researcher (Algolia, keyless) + optional search API stub."""
from __future__ import annotations

import httpx
from ..retrieval.url_guard import validate_url


async def research(company: str, company_url: str, *, allow_private: bool = False, client: httpx.AsyncClient | None = None) -> dict:
    ok, reason = validate_url(company_url, allow_private=allow_private)
    if not ok:
        return {"queried": False, "reason": f"company url private ({reason}); discussion skipped", "threads": []}
    name = (company or "").strip()
    if not name:
        # derive label from host
        from urllib.parse import urlparse
        name = urlparse(company_url).netloc
    if not name:
        return {"queried": True, "reason": "nothing found", "threads": []}
    own = client is not None
    cli = client or httpx.AsyncClient(timeout=10)
    try:
        try:
            resp = await cli.get(
                "https://hn.algolia.com/api/v1/search",
                params={"query": f"{name} interview", "tags": "story", "hitsPerPage": 5},
            )
            if resp.status_code != 200:
                return {"queried": True, "reason": "nothing found", "threads": []}
            hits = resp.json().get("hits", [])
            threads = [
                {"title": h.get("title", ""), "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"}
                for h in hits[:3]
            ]
            if not threads:
                return {"queried": True, "reason": "nothing found", "threads": []}
            return {"queried": True, "reason": "", "threads": threads}
        except Exception as exc:
            return {"queried": True, "reason": f"nothing found ({exc})", "threads": []}
    finally:
        if not own:
            await cli.aclose()
