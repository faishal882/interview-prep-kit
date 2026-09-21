"""FastAPI app factory."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import check_origin
from app.api.errors import envelope, kit_error_handler, unhandled_handler, validation_handler
from app.api.routers import auth, items, kits, practice, sections
from app.domain.errors import KitError


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    from app.config import get_settings, validate_production
    from app.jobs.worker import Worker
    from app.llm.router import configure_shared_limiter
    from app.persistence.store import get_store

    settings = get_settings()
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
        from app.domain.errors import Codes, KitError as KE
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

    app.include_router(auth.router)
    app.include_router(kits.router)
    app.include_router(items.router)
    app.include_router(sections.router)
    app.include_router(practice.router)
    return app


app = create_app()
