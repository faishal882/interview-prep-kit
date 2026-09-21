"""Page typing and company-name resolution for research enrichment."""
from __future__ import annotations

import re
from urllib.parse import urlparse

HIRING_SEGMENT = re.compile(r"career|jobs?|hiring|hired|interview|vacanc|opening|position|apply|join", re.I)
HIRING_TITLE = re.compile(r"\b(careers?|hiring|how we hire|interview process|join (us|our team)|work with us|open (roles|positions))\b", re.I)


def page_type(page: dict) -> str:
    """'hiring' for pages that actually describe hiring, else 'other'."""
    url = page.get("final_url") or page.get("url") or ""
    segments = (urlparse(url).path or "/").split("/")
    if any(HIRING_SEGMENT.search(seg) for seg in segments if seg):
        return "hiring"
    title = page.get("title") or ""
    if HIRING_TITLE.search(title):
        return "hiring"
    return "other"


def find_hiring_page(pages: list[dict]) -> str | None:
    """First hiring-typed page URL, or None when there is none."""
    for p in pages:
        if page_type(p) == "hiring":
            return p.get("final_url") or p.get("url")
    return None


def site_declared_name(pages: list[dict]) -> str:
    """The company's own site name: og:site_name, then <title>, from the start page first."""
    ordered = sorted(pages, key=lambda p: p.get("depth", 0))
    for p in ordered:
        name = (p.get("site_name") or "").strip()
        if name:
            return name
    for p in ordered:
        title = (p.get("title") or "").strip()
        if title:
            # strip common separators: "Acme — Careers" -> "Acme"
            head = re.split(r"\s*[|–—·•:]\s*", title)[0].strip()
            if head:
                return head
    return ""


def domain_label(company_url: str) -> str:
    host = (urlparse(company_url).hostname or "").lower()
    if not host:
        return ""
    from app.retrieval.crawler import registrable_domain
    reg = registrable_domain(host)
    first = reg.split(".")[0]
    return first[:1].upper() + first[1:] if first else ""


def resolve_company_name(jd_company: str, pages: list[dict], company_url: str) -> tuple[str, str]:
    """Return (name, source) with source in jd|site|domain|none."""
    if (jd_company or "").strip():
        return jd_company.strip(), "jd"
    site = site_declared_name(pages)
    if site:
        return site, "site"
    dom = domain_label(company_url)
    if dom:
        return dom, "domain"
    return "", "none"
