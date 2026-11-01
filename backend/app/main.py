"""Punto de entrada: fábrica de la aplicación FastAPI.

``create_app`` arma la app a partir de una configuración. Producción usa
``app = create_app()``; las pruebas llaman ``create_app(Settings(...))`` con
SQLite en memoria y un reloj fijo.
"""

import logging
import time
import uuid
from collections.abc import Callable
from datetime import date

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.routers import ALL_ROUTERS
from app.core.clock import today_lima
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, request_id_ctx
from app.infrastructure.database import build_engine, build_session_factory
from app.infrastructure.storage import LocalFileStorage

VERSION = "1.0.0"
access_log = logging.getLogger("app.access")

DESCRIPTION = """
API para gestionar una flota de reparto: vehículos, conductores, pedidos,
rutas optimizadas, entregas con prueba, mantenimiento y combustible.

**Autenticación:** obtén un token en `POST /api/auth/login` (demo: `admin@demo.pe` / `Demo123!`)
y pulsa *Authorize* para enviarlo como `Bearer`.

**Errores:** todas las respuestas de error usan ProblemDetails (`application/problem+json`).
"""


def create_app(settings: Settings | None = None, *, today: Callable[[], date] = today_lima) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_json)

    app = FastAPI(
        title=settings.app_name,
        version=VERSION,
        description=DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={"name": "Angel Castañeda Meza", "url": "https://github.com/angel-cm-dev"},
        license_info={"name": "MIT"},
    )
    engine = build_engine(settings.database_url)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)
    app.state.storage = LocalFileStorage(settings.upload_dir, settings.max_upload_mb * 1024 * 1024)
    app.state.today = today

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        # Reutiliza el X-Request-ID del proxy si viene; si no, genera uno.
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        token = request_id_ctx.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        elapsed = round((time.perf_counter() - start) * 1000, 1)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path != "/health":
            access_log.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": elapsed,
                    "request_id": rid,
                },
            )
        return response

    register_error_handlers(app)
    for router in ALL_ROUTERS:
        app.include_router(router)
    return app


app = create_app()
