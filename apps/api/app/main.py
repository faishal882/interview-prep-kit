"""FastAPI app factory."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import check_origin
from app.api.errors import envelope, kit_error_handler, unhandled_handler
from app.api.routers import auth, items, kits, practice, sections
from app.domain.errors import KitError


def create_app() -> FastAPI:
    app = FastAPI(title="trao interview prep kit")
    app.add_exception_handler(KitError, kit_error_handler)
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

    app.include_router(auth.router)
    app.include_router(kits.router)
    app.include_router(items.router)
    app.include_router(sections.router)
    app.include_router(practice.router)
    return app


app = create_app()
