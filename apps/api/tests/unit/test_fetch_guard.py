"""Phase 1: guard, robots semantics, normalisation, scope, cache, limiter, streaming."""
import asyncio
import time

import httpx
import respx

from app.retrieval import robots as robots_mod
from app.retrieval.crawler import dedupe_key, is_hiring_platform, normalize_url, registrable_domain
from app.retrieval.safe_fetch import PageCache, fetch, resolve_redirect
from app.retrieval import safe_fetch as safe_fetch_mod
from app.retrieval.url_guard import is_globally_routable, validate_url


def test_guard_refuses_non_routable():
    for url in [
        "http://10.0.0.1/", "http://172.16.0.1/", "http://192.168.1.1/",
        "http://127.0.0.1/", "http://localhost/", "http://169.254.169.254/",
        "http://[::1]/", "http://[fe80::1]/", "http://100.64.0.1/",
        "http://224.0.0.1/", "http://0.0.0.0/",
    ]:
        ok, reason = validate_url(url, allow_private=False)
        assert not ok, url
        assert reason in ("private", "dns"), (url, reason)


def test_guard_unwraps_ipv4_mapped():
    assert not is_globally_routable("::ffff:10.0.0.1")
    assert is_globally_routable("::ffff:8.8.8.8")
    assert is_globally_routable("8.8.8.8")


def test_guard_scheme_host_and_bypass():
    assert validate_url("ftp://example.com/") == (False, "scheme")
    assert validate_url("http:///") == (False, "no-host")
    assert validate_url("http://127.0.0.1/x", allow_private=True) == (True, "")


def test_guard_production_ports():
    ok, reason = validate_url("http://example.com:8080/", allow_private=False, production=True)
    assert (ok, reason) == (False, "port")
    ok2, _ = validate_url("https://example.com:443/", allow_private=False, production=True)
    assert ok2
    ok3, _ = validate_url("http://example.com/", allow_private=False, production=True)
    assert ok3


def test_robots_decide_semantics():
    ua = "trao-interview-prep/1.0 (+research)"
    assert robots_mod.decide(404, None, "http://h/x", ua) == (True, "")
    assert robots_mod.decide(None, None, "http://h/x", ua)[0] is False
    assert robots_mod.decide(500, "oops", "http://h/x", ua)[0] is False
    ok, _ = robots_mod.decide(200, "User-agent: *\nDisallow: /private\n", "http://h/private/x", ua)
    assert ok is False
    ok2, _ = robots_mod.decide(200, "User-agent: *\nDisallow: /private\n", "http://h/public/x", ua)
    assert ok2 is True


def test_robots_async_check_and_delay():
    async def go():
        async def fetch_status(url):
            return 200, "User-agent: *\nCrawl-delay: 3\nDisallow: /private\n"
        robots_mod.clear_cache()
        ok, reason, delay = await robots_mod.check("http://h.test/public", "ua", fetch_status)
        assert (ok, reason, delay) == (True, "", 3.0)
        ok2, _, _ = await robots_mod.check("http://h.test/private", "ua", fetch_status)
        assert ok2 is False
    asyncio.run(go())


def test_registrable_domain_suffix_aware():
    assert registrable_domain("example.com") == "example.com"
    assert registrable_domain("careers.example.com") == "example.com"
    assert registrable_domain("acme.co.uk") == "acme.co.uk"
    assert registrable_domain("jobs.acme.co.uk") == "acme.co.uk"
    assert registrable_domain("other.co.uk") == "other.co.uk"
    assert registrable_domain("Example.COM.") == "example.com"
    assert registrable_domain("127.0.0.1") == "127.0.0.1"


def test_ats_exact_domain_only():
    assert is_hiring_platform("boards.greenhouse.io")
    assert is_hiring_platform("greenhouse.io")
    assert not is_hiring_platform("greenhouse.io.evil.example")
    assert not is_hiring_platform("notgreenhouse.io")
    assert not is_hiring_platform("greenhouse.iox")


def test_normalize_url_dedupes_trivial_variants():
    a = normalize_url("HTTP://Example.COM:80/about")
    b = normalize_url("http://example.com/about")
    c = normalize_url("http://example.com/about#team")
    d = normalize_url("http://example.com/?b=2&a=1")
    e = normalize_url("http://example.com/?a=1&b=2")
    assert a == b == c
    assert d == e
    assert normalize_url("http://example.com") == "http://example.com/"
    # trailing slash changes the resource, so it is kept — but deduped for crawl scope
    assert normalize_url("http://example.com/about/") != normalize_url("http://example.com/about")
    assert dedupe_key("http://example.com/about/") == dedupe_key("http://example.com/about")


def test_resolve_redirect_rejects_bad_targets():
    ok, _ = resolve_redirect("http://a.test/x", "/y")
    assert ok
    ok2, reason = resolve_redirect("http://a.test/x", "javascript:alert(1)")
    assert not ok2 and reason == "redirect-scheme"
    ok3, reason3 = resolve_redirect("http://a.test/x", None)
    assert not ok3 and reason3 == "redirect-no-location"


def test_cache_bounded_and_expiring():
    c = PageCache(maxsize=2, ttl_s=0.05)
    c.put("a", {"t": 1})
    c.put("b", {"t": 2})
    c.put("c", {"t": 3})
    assert len(c) == 2
    assert c.get("a") is None
    assert c.get("b") == {"t": 2}
    time.sleep(0.06)
    assert c.get("b") is None


def test_redirect_chain_followed_to_final_content():
    async def go():
        async with respx.mock(assert_all_called=False) as router:
            router.get("http://chain.test/robots.txt").mock(return_value=httpx.Response(404))
            router.get("http://chain.test/old").mock(return_value=httpx.Response(302, headers={"location": "/new"}))
            router.get("http://chain.test/new").mock(return_value=httpx.Response(200, headers={"content-type": "text/html"}, text="<html><body>final page</body></html>"))
            return await fetch("http://chain.test/old", allow_private=True)
    page = asyncio.run(go())
    assert page is not None and "final page" in page["text"]
    assert page["final_url"] == "http://chain.test/new"


def test_redirect_to_private_refused_before_request():
    import socket
    real = socket.getaddrinfo

    def fake(host, *a, **k):
        if host == "start.test":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
        return real(host, *a, **k)

    async def go():
        async with respx.mock(assert_all_called=False) as router:
            router.get("http://start.test/robots.txt").mock(return_value=httpx.Response(404))
            route = router.get("http://start.test/go").mock(
                return_value=httpx.Response(302, headers={"location": "http://169.254.169.254/"}))
            import app.retrieval.url_guard as guard_mod
            orig = guard_mod.socket.getaddrinfo
            guard_mod.socket.getaddrinfo = fake
            try:
                record: list[dict] = []
                page = await fetch("http://start.test/go", allow_private=False, record=record)
            finally:
                guard_mod.socket.getaddrinfo = orig
            return page, record, route.called
    page, record, called = asyncio.run(go())
    assert page is None
    assert called
    assert any(r["reason"] == "redirect-private" for r in record)


def test_crawl_delay_honoured():
    async def go():
        async with respx.mock(assert_all_called=False) as router:
            router.get("http://slow.test/robots.txt").mock(
                return_value=httpx.Response(200, headers={"content-type": "text/plain"},
                                            text="User-agent: *\nCrawl-delay: 1\n"))
            router.get("http://slow.test/").mock(
                return_value=httpx.Response(200, headers={"content-type": "text/html"},
                                            text="<html><body>slow</body></html>"))
            robots_mod.clear_cache()
            t0 = time.monotonic()
            page = await fetch("http://slow.test/", allow_private=True, cache=PageCache())
            return page, time.monotonic() - t0
    page, elapsed = asyncio.run(go())
    assert page is not None
    assert elapsed >= 0.9


def test_oversize_aborted_and_content_type_rejected():
    async def go():
        async with respx.mock(assert_all_called=False) as router:
            router.get("http://big.test/robots.txt").mock(return_value=httpx.Response(404))
            router.get("http://big.test/huge").mock(
                return_value=httpx.Response(200, headers={"content-type": "text/html"}, content=b"x" * (2 * 1024 * 1024 + 100)))
            record: list[dict] = []
            r1 = await fetch("http://big.test/huge", allow_private=True, record=record)
            router.get("http://big.test/doc.pdf").mock(
                return_value=httpx.Response(200, headers={"content-type": "application/pdf"}, text="pdf"))
            record2: list[dict] = []
            r2 = await fetch("http://big.test/doc.pdf", allow_private=True, record=record2)
            return r1, record, r2, record2
    r1, record, r2, record2 = asyncio.run(go())
    assert r1 is None
    assert any(r["reason"] == "oversize" for r in record)
    assert r2 is None
    assert any(r["reason"] == "content-type" for r in record2)


def test_per_host_limit_holds_under_concurrency():
    starts: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        starts.append(time.monotonic())
        time.sleep(0.05)
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html><body>ok</body></html>")

    async def go():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport, follow_redirects=False) as client:
            await asyncio.gather(
                fetch("http://conc.test/a", allow_private=True, client=client, cache=PageCache()),
                fetch("http://conc.test/b", allow_private=True, client=client, cache=PageCache()),
            )
    old = safe_fetch_mod._rate_interval_s
    safe_fetch_mod._rate_interval_s = 0.3
    try:
        asyncio.run(go())
    finally:
        safe_fetch_mod._rate_interval_s = old
    assert len(starts) == 2
    assert starts[1] - starts[0] >= 0.2
