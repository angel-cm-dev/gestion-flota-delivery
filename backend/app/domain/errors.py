"""Errores del dominio.

Las capas de dominio y aplicación lanzan estas excepciones sin saber nada de
HTTP. La capa API (``app/api/errors.py``) las traduce a respuestas
ProblemDetails (RFC 9457) con el código de estado adecuado.
"""


class DomainError(Exception):
    """Regla de negocio incumplida (HTTP 422 por defecto)."""

    status_code = 422
    title = "Regla de negocio incumplida"
    code = "business_rule"

    def __init__(self, detail: str, *, code: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        if code:
            self.code = code


class NotFoundError(DomainError):
    status_code = 404
    title = "Recurso no encontrado"
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    title = "Conflicto con el estado actual"
    code = "conflict"


class ForbiddenError(DomainError):
    status_code = 403
    title = "Acceso denegado"
    code = "forbidden"


class AuthenticationError(DomainError):
    status_code = 401
    title = "No autenticado"
    code = "unauthenticated"
