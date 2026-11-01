"""La migración de Alembic crea exactamente el esquema de los modelos ORM.

Evita el error clásico de cambiar un modelo y olvidar generar la migración:
``alembic check`` falla si el modelo y la última migración no coinciden.
"""

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_migrations_upgrade_and_match_models(tmp_path):
    url = f"sqlite:///{(tmp_path / 'mig.db').as_posix()}"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    tables = set(inspect(create_engine(url)).get_table_names())
    assert {"users", "vehicles", "drivers", "routes", "orders", "maintenance_records", "fuel_logs"} <= tables
    command.check(cfg)  # lanza excepción si hay diferencias con los modelos
    command.downgrade(cfg, "base")
