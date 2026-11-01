"""Autenticación, autorización por rol y formato de errores."""

from tests.conftest import login


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["database"] == "up"
    assert "X-Request-ID" in res.headers


def test_openapi_is_published(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/routes" in paths and "/api/orders/{order_id}/deliver" in paths


def test_login_ok_returns_token_and_user(client):
    res = client.post("/api/auth/login", json={"email": "ADMIN@demo.pe", "password": "Demo123!"})
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer" and body["user"]["role"] == "admin"


def test_login_wrong_password_returns_problem_details(client):
    res = client.post("/api/auth/login", json={"email": "admin@demo.pe", "password": "incorrecta"})
    assert res.status_code == 401
    assert res.headers["content-type"].startswith("application/problem+json")
    body = res.json()
    assert body["code"] == "invalid_credentials" and body["status"] == 401 and body["instance"] == "/api/auth/login"


def test_unknown_email_gives_same_error(client):
    res = client.post("/api/auth/login", json={"email": "nadie@demo.pe", "password": "Demo123!"})
    assert res.status_code == 401 and res.json()["code"] == "invalid_credentials"


def test_validation_error_lists_fields(client):
    res = client.post("/api/auth/login", json={"email": "no-es-email", "password": ""})
    assert res.status_code == 422
    fields = {e["field"] for e in res.json()["errors"]}
    assert {"email", "password"} <= fields


def test_missing_and_invalid_token(client):
    assert client.get("/api/auth/me").json()["code"] == "missing_token"
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert res.status_code == 401 and res.json()["code"] == "invalid_token"


def test_me_includes_driver_link(client, driver1):
    me = client.get("/api/auth/me", headers=driver1).json()
    assert me["role"] == "conductor" and me["driver_id"] == 1


def test_role_authorization(client, dispatcher, driver1):
    # El conductor no gestiona conductores ni pedidos; el despachador no administra usuarios ni elimina vehículos.
    assert client.get("/api/drivers", headers=driver1).status_code == 403
    assert client.post("/api/orders", headers=driver1, json={}).status_code in (403, 422)
    assert client.get("/api/users", headers=dispatcher).status_code == 403
    assert client.delete("/api/vehicles/6", headers=dispatcher).status_code == 403
    res = client.get("/api/dashboard", headers=driver1)
    assert res.status_code == 403 and res.json()["code"] == "forbidden"


def test_admin_manages_users_and_deactivation_revokes_access(client, admin):
    res = client.post(
        "/api/users",
        headers=admin,
        json={"email": "nuevo@demo.pe", "full_name": "Nuevo Despachador", "password": "Clave123", "role": "despachador"},
    )
    assert res.status_code == 201
    uid = res.json()["id"]
    assert (
        client.post(
            "/api/users", headers=admin, json={"email": "nuevo@demo.pe", "full_name": "Otro", "password": "Clave123", "role": "despachador"}
        ).status_code
        == 409
    )
    token = login(client, "nuevo@demo.pe", "Clave123")
    assert client.get("/api/auth/me", headers=token).status_code == 200
    upd = client.put(f"/api/users/{uid}", headers=admin, json={"full_name": "Nuevo Despachador", "role": "despachador", "is_active": False})
    assert upd.status_code == 200
    # El token sigue firmado y sin expirar, pero el usuario ya no está activo.
    assert client.get("/api/auth/me", headers=token).status_code == 401


def test_admin_cannot_lock_himself_out(client, admin):
    res = client.put("/api/users/1", headers=admin, json={"full_name": "Admin", "role": "despachador", "is_active": True})
    assert res.status_code == 422 and res.json()["code"] == "self_lockout"


def test_users_list_is_paginated_and_filtered(client, admin):
    body = client.get("/api/users?role=conductor&size=1", headers=admin).json()
    assert body["total"] == 2 and body["pages"] == 2 and len(body["items"]) == 1
