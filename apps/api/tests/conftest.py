import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ.setdefault("FAKE_LLM", "1")
# Tests exercise the development server surface; production-only fail-closed
# behaviour is covered by dedicated tests with patched settings.
os.environ.setdefault("ENV", "development")
# Registration is closed by default; tests provision users through the API.
os.environ.setdefault("REGISTRATION_OPEN", "true")


@pytest.fixture(autouse=True)
def _isolate_process_global_state():
    """Reset process-wide limiter/throttle state between tests.

    Production shares one limiter and per-host throttle state across runs;
    tests must not observe each other's budget consumption.
    """
    from app.llm import router as router_mod
    from app.retrieval import safe_fetch as fetch_mod
    router_mod.reset_shared_limiter()
    fetch_mod._host_last.clear()
    yield
    router_mod.reset_shared_limiter()
    fetch_mod._host_last.clear()
