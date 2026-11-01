"""Configuración centralizada (12-factor): todo se lee de variables de entorno."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Gestión de Flota y Delivery API"
    environment: str = "development"
    # SQLite es solo para desarrollo rápido sin Docker; producción usa PostgreSQL.
    database_url: str = "sqlite:///./flota-dev.db"

    jwt_secret: str = Field(default="dev-secret-cambiar-en-produccion-minimo-32-caracteres", min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120

    # Lista separada por comas, p. ej. "http://localhost:5173,http://localhost:8080"
    cors_origins: str = "http://localhost:5173"

    # Depósito central desde el que salen las rutas (por defecto: Cercado de Lima).
    depot_lat: float = -12.0464
    depot_lng: float = -77.0428

    upload_dir: str = "./uploads"
    max_upload_mb: int = 5

    document_warning_days: int = 30
    maintenance_warning_km: int = 500

    log_level: str = "INFO"
    log_json: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
