from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import AdminOnly, CurrentUser, Paging, service
from app.application import schemas as s
from app.application.mappers import user_out
from app.application.services import AuthService, UserService
from app.domain.enums import Role

auth_router = APIRouter(prefix="/api/auth", tags=["Autenticación"])
users_router = APIRouter(prefix="/api/users", tags=["Usuarios"])


@auth_router.post("/login", response_model=s.TokenResponse, summary="Iniciar sesión y obtener un JWT")
def login(data: s.LoginRequest, svc: Annotated[AuthService, Depends(service(AuthService))]):
    return svc.login(data.email, data.password)


@auth_router.get("/me", response_model=s.UserOut, summary="Usuario autenticado")
def me(user: CurrentUser):
    return user_out(user)


@users_router.get("", response_model=s.Page[s.UserOut])
def list_users(
    _: AdminOnly,
    paging: Paging,
    svc: Annotated[UserService, Depends(service(UserService))],
    q: str | None = Query(None, max_length=100),
    role: Role | None = None,
):
    return svc.list(q=q, role=role, page=paging.page, size=paging.size, sort=paging.sort)


@users_router.post("", response_model=s.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(data: s.UserCreate, _: AdminOnly, svc: Annotated[UserService, Depends(service(UserService))]):
    return svc.create(data)


@users_router.put("/{user_id}", response_model=s.UserOut)
def update_user(user_id: int, data: s.UserUpdate, admin: AdminOnly, svc: Annotated[UserService, Depends(service(UserService))]):
    return svc.update(user_id, data, acting_user=admin)
