"""Robots semantics + crawler budget tests."""
import asyncio

from app.retrieval.crawler import crawl
from app.retrieval.robots import allowed

from .fixture_sites import ACME_HIRING, ACME_INDEX, serve


def test_disallowed_recorded_not_fetched():
    ok, reason = allowed("http://example.com/private/x", "trao-interview-prep/1.0 (+research)",
                         lambda u: "User-agent: *\nDisallow: /private\n")
    assert ok is False and reason == "robots"
    ok2, _ = allowed("http://example.com/public/x", "trao-interview-prep/1.0 (+research)",
                     lambda u: "User-agent: *\nDisallow: /private\n")
    assert ok2 is True


def test_crawler_respects_page_budget_and_depth():
    routes = {"/": (200, "text/html", ACME_INDEX),
              "/about": (200, "text/html", "<html><body>about</body></html>"),
              "/h": (200, "text/html", ACME_HIRING)}
    srv = serve(routes)
    port = srv.server_address[1]
    log: dict = {}
    pages, _used = asyncio.run(crawl(f"http://127.0.0.1:{port}/", budget=2, depth=1,
                                     allow_private=True, research_log=log))
    srv.shutdown()
    assert len(pages) <= 2
    assert "fetches" in log
