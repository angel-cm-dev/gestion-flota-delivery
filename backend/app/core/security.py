"""Hash de contraseñas y tokens JWT.

* Argon2id (ganador de la Password Hashing Competition) con los parámetros
  recomendados por ``argon2-cffi``. Es resistente a ataques con GPU por ser
  costoso en memoria, a diferencia de SHA-256 o MD5.
* JWT firmado con HS256. El token lleva solo el id y el rol: nada sensible,
  porque el payload de un JWT es legible por cualquiera (solo está firmado).
"""

from datetime import timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.clock import utcnow

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(*, subject: str, role: str, secret: str, algorithm: str, expires_minutes: int) -> str:
    now = utcnow()
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str, *, secret: str, algorithm: str) -> dict:
    """Lanza ``jwt.PyJWTError`` si el token es inválido o expiró."""
    return jwt.decode(token, secret, algorithms=[algorithm], options={"require": ["sub", "exp"]})
