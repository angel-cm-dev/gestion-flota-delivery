"""Almacenamiento de fotos de prueba de entrega.

Interfaz mínima (``FileStorage``) con una implementación en disco local. En
producción se puede cambiar por S3/MinIO implementando el mismo protocolo, sin
tocar los servicios.
"""

import uuid
from pathlib import Path
from typing import Protocol

from app.domain.errors import DomainError

# Validamos por firma binaria ("magic bytes") y no solo por la extensión o el
# Content-Type, que el cliente puede falsificar.
_SIGNATURES = {
    b"\xff\xd8\xff": ".jpg",
    b"\x89PNG\r\n\x1a\n": ".png",
    b"RIFF": ".webp",
}


def detect_image_extension(data: bytes) -> str | None:
    for magic, ext in _SIGNATURES.items():
        if data.startswith(magic):
            if ext == ".webp" and data[8:12] != b"WEBP":
                continue
            return ext
    return None


class FileStorage(Protocol):
    def save_image(self, data: bytes, *, prefix: str) -> str: ...
    def resolve(self, relative_path: str) -> Path: ...


class LocalFileStorage:
    def __init__(self, base_dir: str, max_bytes: int) -> None:
        self.base = Path(base_dir).resolve()
        self.max_bytes = max_bytes

    def save_image(self, data: bytes, *, prefix: str) -> str:
        if len(data) > self.max_bytes:
            raise DomainError(f"La foto supera el máximo de {self.max_bytes // (1024 * 1024)} MB", code="file_too_large")
        ext = detect_image_extension(data)
        if not ext:
            raise DomainError("Formato de imagen no soportado (use JPG, PNG o WEBP)", code="invalid_image")
        self.base.mkdir(parents=True, exist_ok=True)
        # Nombre aleatorio: nunca usamos el nombre enviado por el cliente (path traversal).
        name = f"{prefix}-{uuid.uuid4().hex}{ext}"
        (self.base / name).write_bytes(data)
        return name

    def resolve(self, relative_path: str) -> Path:
        path = (self.base / relative_path).resolve()
        if self.base not in path.parents:
            raise DomainError("Ruta de archivo inválida", code="invalid_path")
        return path
