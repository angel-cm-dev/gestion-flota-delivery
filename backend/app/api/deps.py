"""Inyección de dependencias de FastAPI.

Cada endpoint declara lo que necesita (sesión, usuario, servicio) y FastAPI lo
construye por petición. En las pruebas basta con crear la app con otra
configuración (SQLite en memoria) para que toda la cadena use esa base.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Annotated, TypeVar

import jwt
from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.application.services.base import Service
from app.core.config import Settings
from app.core.security import decode_access_token
from app.domain.enums import Role
from app.domain.errors import AuthenticationError, ForbiddenError
from app.infrastructure.models import User

S = TypeVar("S", bound=Service)

bearer = HTTPBearer(auto_error=False, description="Token JWT obtenido en POST /api/auth/login")


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    session: Session = request.app.state.session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DbDep = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_current_user(
    db: DbDep,
    settings: SettingsDep,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if creds is None:
        raise AuthenticationError("Falta el token de acceso (cabecera Authorization: Bearer <token>)", code="missing_token")
    try:
        payload = decode_access_token(creds.credentials, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm)
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("El token expiró; inicia sesión nuevamente", code="token_expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Token inválido", code="invalid_token") from exc
    user = db.get(User, int(payload["sub"]))
    # Se consulta la BD en cada petición: si un admin desactiva a alguien,
    # su token deja de servir de inmediato aunque aún no haya expirado.
    if user is None or not user.is_active:
        raise AuthenticationError("Usuario inexistente o desactivado", code="invalid_user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role) -> Callable[[User], User]:
    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError(f"Se requiere uno de estos roles: {', '.join(roles)}")
        return user

    return checker


ALL_ROLES = (Role.ADMIN, Role.DESPACHADOR, Role.CONDUCTOR)
Staff = Annotated[User, Depends(require_roles(Role.ADMIN, Role.DESPACHADOR))]
AdminOnly = Annotated[User, Depends(require_roles(Role.ADMIN))]
AnyRole = Annotated[User, Depends(require_roles(*ALL_ROLES))]


@dataclass
class PageParams:
    page: int = Query(1, ge=1, description="Número de página (desde 1)")
    size: int = Query(20, ge=1, le=100, description="Elementos por página (máx. 100)")
    sort: str | None = Query(None, pattern=r"^-?[a-z_]+$", description="Campo de orden; prefijo '-' para descendente")


Paging = Annotated[PageParams, Depends()]


def service(cls: type[S]) -> Callable[..., S]:
    """Fábrica de dependencias: ``Depends(service(VehicleService))``."""

    def factory(request: Request, db: DbDep, settings: SettingsDep) -> S:
        kwargs = {"today": request.app.state.today}
        if getattr(cls, "needs_storage", False):
            kwargs["storage"] = request.app.state.storage
        return cls(db, settings, **kwargs)

    return factory
