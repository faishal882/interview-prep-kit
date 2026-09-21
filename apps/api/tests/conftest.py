import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ.setdefault("FAKE_LLM", "1")


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
