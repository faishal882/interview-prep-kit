"""Phase 7: restart durability, production validation, operator command."""
import os
import time
import uuid

import pytest

from app.config import validate_production

pytestmark = pytest.mark.asyncio


def _mongo_uri() -> str | None:
    uri = os.environ.get("MONGODB_TEST_URI", "mongodb://127.0.0.1:27017")
    try:
        import socket
        from urllib.parse import urlparse
        host = urlparse(uri).hostname or "127.0.0.1"
        port = urlparse(uri).port or 27017
        socket.create_connection((host, port), timeout=2).close()
        return uri
    except OSError:
        return None


async def test_restart_preserves_accounts_kits_edits_and_practice():
    uri = _mongo_uri()
    if uri is None:
        pytest.skip("mongodb not reachable")
    from app.persistence.repos_mongo import MongoStore

    db_name = f"trao_restart_{uuid.uuid4().hex[:8]}"
    first = MongoStore(uri, db_name)
    await first.startup()
    user = await first.users.create("keep@x.co", "hash")
    await first.sessions.create("tok", user["id"], time.time() + 3600)
    await first.kits.create({"id": "k1", "user_id": user["id"], "dedupe_key": "d",
                             "status": "ready", "input": {}, "kit": {"edited": True},
                             "created_at": time.time()})
    await first.practice.append_review("k1:f1", {"confidence": 1, "at": 1.0})
    await first.shutdown()

    # a fresh process view: new client, same database
    second = MongoStore(uri, db_name)
    await second.startup()
    try:
        assert (await second.users.by_email("keep@x.co"))["id"] == user["id"]
        assert (await second.sessions.get("tok"))["user_id"] == user["id"]
        assert (await second.kits.get("k1"))["kit"] == {"edited": True}
        assert await second.practice.reviews("k1:f1") == [{"confidence": 1, "at": 1.0}]
    finally:
        for col in ("users", "sessions", "kits", "jobs", "practice", "page_cache", "throttles"):
            await second._db[col].delete_many({})
        await second.shutdown()


def test_production_validation_names_every_problem(monkeypatch):
    import app.config as config_mod
    monkeypatch.delenv("FAKE_LLM", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    base = {"MONGODB_URI": "", "GEMINI_API_KEY": "", "ALLOWED_ORIGINS": "", "FAKE_LLM": "",
            "MAX_CONCURRENT_RUNS": 2}
    problems = validate_production(config_mod.Settings(**base))
    assert any("MONGODB_URI" in p for p in problems)
    assert any("GEMINI_API_KEY" in p for p in problems)
    assert any("ALLOWED_ORIGINS" in p for p in problems)
    assert len(problems) == 3

    fake = validate_production(config_mod.Settings(**{**base, "FAKE_LLM": "1",
        "MONGODB_URI": "mongodb://x:27017", "GEMINI_API_KEY": "k", "ALLOWED_ORIGINS": "https://a.test"}))
    assert fake == ["FAKE_LLM must not be set in production"]

    good = validate_production(config_mod.Settings(**{**base, "MONGODB_URI": "mongodb://x:27017",
        "GEMINI_API_KEY": "k", "ALLOWED_ORIGINS": "https://a.test"}))
    assert good == []


async def test_unreachable_database_fails_startup():
    from app.persistence.repos_mongo import MongoStore
    store = MongoStore("mongodb://127.0.0.1:9", "trao_unreachable")
    with pytest.raises(Exception):
        await store.startup()
    await store.shutdown()


async def test_operator_command_creates_working_user(monkeypatch):
    uri = _mongo_uri()
    if uri is None:
        pytest.skip("mongodb not reachable")
    from app.cli import create_user as cu_mod
    from app.persistence import store as store_mod
    db_name = f"trao_opuser_{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("MONGODB_URI", uri)
    monkeypatch.setenv("MONGODB_DB", db_name)
    monkeypatch.delenv("FAKE_LLM", raising=False)
    store_mod.reset_stores()
    import app.config as config_mod
    monkeypatch.setattr(config_mod, "_settings", None)
    email = f"op-{uuid.uuid4().hex[:6]}@x.co"
    user = await cu_mod._create(email, "password123")
    assert user["email"] == email
    store_mod.reset_stores()  # _create shuts its store down; open a fresh view
    store = store_mod.get_store()
    try:
        assert await store.users.by_email(email) is not None
        # the created user can actually log in through the API layer
        from app.security.passwords import verify_password
        stored = await store.users.by_email(email)
        assert verify_password(stored["pw_hash"], "password123")
    finally:
        for col in ("users", "sessions", "kits", "jobs", "practice", "page_cache", "throttles"):
            await store._db[col].delete_many({})
        await store.shutdown()
        store_mod.reset_stores()
