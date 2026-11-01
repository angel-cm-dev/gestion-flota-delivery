from __future__ import annotations

from app.application import schemas as s
from app.application.mappers import user_out
from app.application.services.base import Service
from app.core.security import create_access_token, hash_password, verify_password
from app.domain.enums import Role
from app.domain.errors import AuthenticationError, ConflictError, DomainError, NotFoundError
from app.infrastructure.models import User
from app.infrastructure.repositories import UserRepository

# Hash precalculado para comparar cuando el email no existe: así la respuesta
# tarda lo mismo y no se puede averiguar qué emails están registrados midiendo tiempos.
_DUMMY_HASH = hash_password("usuario-inexistente")


class AuthService(Service):
    def login(self, email: str, password: str) -> s.TokenResponse:
        user = UserRepository(self.session).by_email(email)
        if user is None:
            verify_password(password, _DUMMY_HASH)
            raise AuthenticationError("Email o contraseña incorrectos", code="invalid_credentials")
        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Email o contraseña incorrectos", code="invalid_credentials")
        if not user.is_active:
            raise AuthenticationError("El usuario está desactivado", code="user_inactive")
        token = create_access_token(
            subject=str(user.id),
            role=user.role,
            secret=self.settings.jwt_secret,
            algorithm=self.settings.jwt_algorithm,
            expires_minutes=self.settings.jwt_expire_minutes,
        )
        return s.TokenResponse(access_token=token, expires_in=self.settings.jwt_expire_minutes * 60, user=user_out(user))


class UserService(Service):
    @property
    def repo(self) -> UserRepository:
        return UserRepository(self.session)

    def list(self, *, q: str | None, role: str | None, page: int, size: int, sort: str | None) -> s.Page[s.UserOut]:
        rows, total = self.repo.paginate(self.repo.search(q=q, role=role), page=page, size=size, sort=sort)
        return s.Page.build([user_out(u) for u in rows], total, page, size)

    def create(self, data: s.UserCreate) -> s.UserOut:
        if self.repo.by_email(data.email):
            raise ConflictError("Ya existe un usuario con ese email", code="email_taken")
        user = self.repo.add(
            User(email=data.email.lower(), full_name=data.full_name, password_hash=hash_password(data.password), role=data.role)
        )
        self.commit()
        return user_out(user)

    def update(self, user_id: int, data: s.UserUpdate, *, acting_user: User) -> s.UserOut:
        user = self.repo.get(user_id)
        if not user:
            raise NotFoundError("Usuario no encontrado")
        # Un admin no puede quitarse a sí mismo el rol ni desactivarse: dejaría
        # el sistema potencialmente sin nadie capaz de administrarlo.
        if user.id == acting_user.id and (data.role != Role.ADMIN or not data.is_active):
            raise DomainError("No puedes quitarte el rol de admin ni desactivar tu propia cuenta", code="self_lockout")
        if user.driver and data.role != Role.CONDUCTOR:
            raise DomainError("El usuario está vinculado a un conductor; desvincúlalo antes de cambiar su rol")
        user.full_name = data.full_name
        user.role = data.role
        user.is_active = data.is_active
        if data.password:
            user.password_hash = hash_password(data.password)
        self.commit()
        return user_out(user)
