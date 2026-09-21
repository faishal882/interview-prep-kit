"""Optional OpenTelemetry — off by default, content-free by default.

Exporters are asynchronous and never fail or slow a run. When the OTLP
endpoint is unset (or the SDK is not installed), every helper is a no-op so
the batch command and the server behave identically to before.
"""
from __future__ import annotations

import hashlib
import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

from app.config import get_settings

from . import context as ctx

_log = logging.getLogger("trao.otel")
_tracer = None
_meter = None
_enabled = False
_metrics: dict[str, Any] = {}


def _content_free(attrs: dict[str, Any] | None) -> dict[str, Any]:
    """Strip description / page text; keep sizes and hashes unless opted in."""
    out: dict[str, Any] = {}
    if not attrs:
        return out
    capture = False
    try:
        capture = bool(get_settings().DEBUG_CAPTURE_CONTENT)
    except Exception:
        capture = False
    for k, v in attrs.items():
        if k in ("jd", "text", "prompt", "page_text", "description", "content", "body"):
            if capture:
                out[k] = v
            else:
                raw = v if isinstance(v, (bytes, str)) else str(v)
                data = raw.encode() if isinstance(raw, str) else raw
                out[f"{k}_bytes"] = len(data)
                out[f"{k}_hash"] = hashlib.sha256(data).hexdigest()[:16]
        else:
            out[k] = v
    return out


def setup(settings=None) -> None:
    """Initialise providers only when an OTLP endpoint is configured."""
    global _tracer, _meter, _enabled, _metrics
    s = settings or get_settings()
    endpoint = (getattr(s, "OTEL_EXPORTER_OTLP_ENDPOINT", "") or "").strip()
    if not endpoint:
        _enabled = False
        _tracer = None
        _meter = None
        return
    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        _log.warning("otel_packages_missing", extra={"event": "otel_packages_missing"})
        _enabled = False
        return

    try:
        resource = Resource.create({"service.name": s.OTEL_SERVICE_NAME or "trao-api"})
        provider = TracerProvider(resource=resource)
        # Never let export failures propagate into the run.
        exporter = OTLPSpanExporter(endpoint=endpoint.rstrip("/") + "/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("trao")

        reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=endpoint.rstrip("/") + "/v1/metrics"),
            export_interval_millis=15000,
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(meter_provider)
        _meter = metrics.get_meter("trao")
        _metrics = {
            "jobs": _meter.create_counter("trao.jobs", description="job outcomes"),
            "tokens": _meter.create_counter("trao.tokens", description="model tokens"),
            "rate_limits": _meter.create_counter("trao.rate_limits", description="rate-limit hits"),
            "crawls": _meter.create_counter("trao.crawls", description="crawl outcomes"),
        }
        _enabled = True
    except Exception as exc:  # never fail startup for telemetry
        _log.warning("otel_setup_failed: %s", exc)
        _enabled = False
        _tracer = None
        _meter = None


def shutdown() -> None:
    """Best-effort flush/shutdown of providers (tests and process exit)."""
    global _tracer, _meter, _enabled, _metrics
    try:
        from opentelemetry import metrics, trace
        tp = trace.get_tracer_provider()
        if hasattr(tp, "shutdown"):
            tp.shutdown()
        mp = metrics.get_meter_provider()
        if hasattr(mp, "shutdown"):
            mp.shutdown()
    except Exception:
        pass
    _tracer = None
    _meter = None
    _enabled = False
    _metrics = {}


def enabled() -> bool:
    return _enabled


@contextmanager
def span(name: str, attributes: dict | None = None) -> Iterator[dict]:
    """Root-safe span; no-op when telemetry is off. Never raises."""
    attrs = _content_free(attributes)
    if not _enabled or _tracer is None:
        yield {"name": name, "attributes": attrs}
        return
    try:
        from opentelemetry import trace
        with _tracer.start_as_current_span(name) as sp:
            for k, v in attrs.items():
                try:
                    sp.set_attribute(k, v)
                except Exception:
                    pass
            # Prefer the real OTel trace id in the context when available.
            try:
                sc = sp.get_span_context()
                if sc and sc.trace_id:
                    ctx.set_trace_id(f"{sc.trace_id:032x}"[:16])
            except Exception:
                pass
            yield {"name": name, "attributes": attrs, "span": sp}
    except Exception:
        yield {"name": name, "attributes": attrs}


def record_metric(name: str, value: int = 1, **labels: str) -> None:
    if not _enabled:
        return
    counter = _metrics.get(name)
    if counter is None:
        return
    try:
        counter.add(value, labels)
    except Exception:
        pass


def timed_ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 2)
