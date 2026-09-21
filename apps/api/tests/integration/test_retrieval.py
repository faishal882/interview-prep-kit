"""Robots semantics + crawler budget, redirect, oversize and scope tests."""
import asyncio

from app.retrieval.crawler import crawl
from app.retrieval.robots import allowed

from .fixture_sites import ACME_HIRING, ACME_INDEX, many_links_page, serve


def test_disallowed_recorded_not_fetched():
    ok, reason = allowed("http://example.com/private/x", "trao-interview-prep/1.0 (+research)",
                         lambda u: "User-agent: *\nDisallow: /private\n")
    assert ok is False and reason == "robots"
    ok2, _ = allowed("http://example.com/public/x", "trao-interview-prep/1.0 (+research)",
                     lambda u: "User-agent: *\nDisallow: /private\n")
    assert ok2 is True
    ok3, reason3 = allowed("http://example.com/x", "ua", lambda u: None)
    assert ok3 is True and reason3 == ""


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


def test_redirect_returns_final_page_content():
    routes = {"/old": ("redirect", "/new"),
              "/new": (200, "text/html", "<html><body>final destination</body></html>")}
    srv = serve(routes)
    port = srv.server_address[1]
    pages, _ = asyncio.run(crawl(f"http://127.0.0.1:{port}/old", budget=4, depth=1, allow_private=True))
    srv.shutdown()
    assert len(pages) == 1
    assert "final destination" in pages[0]["text"]
    assert pages[0]["final_url"].endswith("/new")


def test_robots_disallow_blocks_start_page():
    routes = {"/": (200, "text/html", ACME_INDEX)}
    srv = serve(routes, robots="User-agent: *\nDisallow: /\n")
    port = srv.server_address[1]
    log: dict = {}
    pages, _ = asyncio.run(crawl(f"http://127.0.0.1:{port}/", budget=4, depth=1,
                                 allow_private=True, research_log=log))
    srv.shutdown()
    assert pages == []
    assert any(f["reason"] == "robots" for f in log.get("fetches", []))


def test_robots_missing_allows_and_error_disallows():
    routes = {"/": (200, "text/html", ACME_INDEX)}
    srv = serve(routes, robots="missing")
    port = srv.server_address[1]
    pages, _ = asyncio.run(crawl(f"http://127.0.0.1:{port}/", budget=2, depth=0, allow_private=True))
    srv.shutdown()
    assert len(pages) == 1
    srv2 = serve(routes, robots="error")
    port2 = srv2.server_address[1]
    pages2, _ = asyncio.run(crawl(f"http://127.0.0.1:{port2}/", budget=2, depth=0, allow_private=True))
    srv2.shutdown()
    assert pages2 == []


def test_oversize_aborted_mid_stream():
    big = "x" * (2 * 1024 * 1024 + 5000)
    routes = {"/": (200, "text/html", f"<html><body>{big}</body></html>")}
    srv = serve(routes)
    port = srv.server_address[1]
    log: dict = {}
    pages, _ = asyncio.run(crawl(f"http://127.0.0.1:{port}/", budget=2, depth=0,
                                 allow_private=True, research_log=log))
    srv.shutdown()
    assert pages == []
    assert any(f["reason"] == "oversize" for f in log.get("fetches", []))


def test_budget_counts_pages_retrieved_and_links_bounded():
    index = many_links_page(5000)
    routes = {"/": (200, "text/html", index)}
    for i in range(30):
        routes[f"/p{i}"] = (200, "text/html", f"<html><body>leaf {i}</body></html>")
    srv = serve(routes)
    port = srv.server_address[1]
    pages, _ = asyncio.run(crawl(f"http://127.0.0.1:{port}/", budget=4, depth=1, allow_private=True))
    srv.shutdown()
    assert len(pages) == 4  # budget counts retrieved pages, not queued links
    for p in pages:
        assert len(p["links"]) <= 200


def test_trivially_different_urls_fetched_once():
    routes = {"/about": (200, "text/html", "<html><body>about <a href='/about/'>self</a> <a href='/about#x'>frag</a></body></html>")}
    srv = serve(routes)
    port = srv.server_address[1]
    log: dict = {}
    pages, _ = asyncio.run(crawl(f"http://127.0.0.1:{port}/about", budget=6, depth=2,
                                 allow_private=True, research_log=log))
    srv.shutdown()
    urls = [p["final_url"] for p in pages]
    assert len(urls) == len(set(urls)) == 1
