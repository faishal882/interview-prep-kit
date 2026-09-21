"""Structured JSON logging always on — request, job and trace ids on every line."""
from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any

from . import context as ctx

_CONFIGURED = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        rid = ctx.request_id()
        jid = ctx.job_id()
        tid = ctx.trace_id()
        if rid:
            payload["request_id"] = rid
        if jid:
            payload["job_id"] = jid
        if tid:
            payload["trace_id"] = tid
        for key in ("method", "path", "status", "duration_ms", "event", "bytes", "hash"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            payload["stack"] = "".join(traceback.format_exception(*record.exc_info))
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    # Keep noisy libraries quieter.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    _CONFIGURED = True


def get_logger(name: str = "trao") -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)


def log_exception(logger: logging.Logger, msg: str, exc: BaseException) -> None:
    logger.error(msg, exc_info=(type(exc), exc, exc.__traceback__))
