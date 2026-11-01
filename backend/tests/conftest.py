"""Fixtures compartidas.

Las pruebas de integración levantan la app real contra SQLite en memoria
(sin Docker) con un "hoy" fijo, para que las alertas de vencimiento sean
deterministas sin importar el día en que se ejecuten.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.infrastructure.database import Base
from app.main import create_app
from app.seed import DEMO_PASSWORD, seed

TODAY = date(2026, 6, 15)

# PNG mínimo válido (1x1) para probar la subida de fotos de prueba de entrega.
PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


@pytest.fixture
def app(tmp_path):
    settings = Settings(database_url="sqlite://", upload_dir=str(tmp_path / "uploads"), log_json=False, log_level="WARNING")
    application = create_app(settings, today=lambda: TODAY)
    Base.metadata.create_all(application.state.engine)
    with application.state.session_factory() as session:
        seed(session, today=TODAY)
    yield application
    application.state.engine.dispose()


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


def login(client: TestClient, email: str, password: str = DEMO_PASSWORD) -> dict[str, str]:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def admin(client):
    return login(client, "admin@demo.pe")


@pytest.fixture
def dispatcher(client):
    return login(client, "despacho@demo.pe")


@pytest.fixture
def driver1(client):
    return login(client, "conductor@demo.pe")


@pytest.fixture
def driver2(client):
    return login(client, "conductor2@demo.pe")
