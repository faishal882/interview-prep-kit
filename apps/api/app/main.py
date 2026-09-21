"""FastAPI app factory."""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.deps import check_origin
from app.api.errors import kit_error_handler, unhandled_handler, validation_handler
from app.api.routers import auth, health, items, kits, practice, sections
from app.domain.errors import KitError
from app.observability import (
    configure_logging,
    get_logger,
    set_request_id,
    setup as setup_otel,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    from app.config import get_settings, validate_production
    from app.jobs.worker import Worker
    from app.llm.router import configure_shared_limiter
    from app.persistence.store import get_store

    configure_logging()
    settings = get_settings()
    setup_otel(settings)
    if settings.ENV == "production":
        problems = validate_production(settings)
        if problems:
            raise RuntimeError("invalid production configuration:\n- " + "\n- ".join(problems))
    configure_shared_limiter(settings.LLM_REQUESTS_PER_MINUTE, settings.LLM_TOKENS_PER_MINUTE)
    store = get_store()
    await store.startup()
    if store.durable:
        from app.retrieval import safe_fetch
        safe_fetch.set_default_cache(store.page_cache)
    worker = Worker(store, concurrency=settings.MAX_CONCURRENT_RUNS,
                    per_user=settings.MAX_CONCURRENT_PER_USER)
    worker_task = asyncio.create_task(worker.run_forever())
    try:
        yield
    finally:
        worker.stop()
        worker_task.cancel()
        try:
            await worker_task
        except (asyncio.CancelledError, Exception):
            pass
        await store.shutdown()


def create_app() -> FastAPI:
    from fastapi.exceptions import RequestValidationError
    from pydantic import ValidationError
    app = FastAPI(title="trao interview prep kit", lifespan=lifespan)
    app.add_exception_handler(KitError, kit_error_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(ValidationError, validation_handler)
    app.add_exception_handler(Exception, unhandled_handler)

    @app.middleware("http")
    async def origin_middleware(request, call_next):
        from app.domain.errors import KitError as KE
        try:
            check_origin(request)
        except KE as ke:
            from app.api.errors import envelope as env
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=403, content=env(ke.code, ke.message, ke.details))
        return await call_next(request)

    @app.middleware("http")
    async def body_limit_middleware(request, call_next):
        from fastapi.responses import JSONResponse
        from app.api.errors import envelope as env
        from app.config import get_settings as _settings
        try:
            limit = _settings().MAX_BODY_BYTES
        except Exception:
            limit = 1048576
        clen = request.headers.get("content-length", "")
        if clen.isdigit() and int(clen) > limit:
            return JSONResponse(status_code=413,
                                content=env("PAYLOAD_TOO_LARGE", "request body too large"))
        return await call_next(request)

    # Outermost: assign request id before any other middleware so errors correlate.
    @app.middleware("http")
    async def request_id_middleware(request, call_next):
        from app.observability import context as obs_ctx
        obs_ctx.clear()
        incoming = request.headers.get("x-request-id") or request.headers.get("x-correlation-id")
        rid = set_request_id(incoming.strip() if incoming else None)
        request.state.request_id = rid
        log = get_logger("trao.http")
        t0 = time.monotonic()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            status = getattr(response, "status_code", 500) if response is not None else 500
            duration_ms = round((time.monotonic() - t0) * 1000, 2)
            record = log.makeRecord(
                log.name, 20, "(middleware)", 0,
                "%s %s -> %s",
                (request.method, request.url.path, status),
                None,
            )
            record.method = request.method
            record.path = request.url.path
            record.status = status
            record.duration_ms = duration_ms
            record.event = "http_request"
            log.handle(record)
            if response is not None:
                response.headers["X-Request-Id"] = rid

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(kits.router)
    app.include_router(items.router)
    app.include_router(sections.router)
    app.include_router(practice.router)
    return app


app = create_app()
