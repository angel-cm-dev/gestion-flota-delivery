"""Manejo global de errores con respuestas ProblemDetails (RFC 9457).

Todas las respuestas de error tienen la misma forma, así el frontend puede
mostrar ``detail`` sin adivinar el formato::

    {"type": "...", "title": "...", "status": 422, "detail": "...",
     "instance": "/api/routes", "code": "capacity_exceeded", "errors": [...]}
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_ctx
from app.domain.errors import DomainError

log = logging.getLogger("app.errors")


def problem(request: Request, *, status: int, title: str, detail: str, code: str, errors: list | None = None) -> JSONResponse:
    body = {
        "type": f"https://httpstatuses.io/{status}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "code": code,
    }
    if errors:
        body["errors"] = errors
    if rid := request_id_ctx.get():
        body["request_id"] = rid
    headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
    return JSONResponse(body, status_code=status, media_type="application/problem+json", headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
        if exc.status_code >= 500:
            log.error("domain_error", extra={"code": exc.code})
        return problem(request, status=exc.status_code, title=exc.title, detail=exc.detail, code=exc.code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"].removeprefix("Value error, ")}
            for e in exc.errors()
        ]
        detail = errors[0]["message"] if len(errors) == 1 else "Hay datos inválidos en la solicitud"
        return problem(request, status=422, title="Datos de entrada inválidos", detail=detail, code="validation_error", errors=errors)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return problem(request, status=exc.status_code, title="Error HTTP", detail=str(exc.detail), code=f"http_{exc.status_code}")

    @app.exception_handler(IntegrityError)
    async def integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        # Red de seguridad: las reglas de unicidad se validan antes, pero dos
        # peticiones simultáneas pueden pasar la validación y chocar en la BD.
        log.warning("integrity_error", extra={"error": str(exc.orig)[:200]})
        return problem(
            request,
            status=409,
            title="Conflicto de datos",
            detail="El registro viola una restricción de integridad",
            code="integrity_error",
        )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_error")
        return problem(
            request, status=500, title="Error interno", detail="Ocurrió un error inesperado. Intenta nuevamente.", code="internal_error"
        )
