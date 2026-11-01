"""Pedidos, rutas optimizadas y entregas con prueba (flujo completo)."""

from tests.conftest import PNG_1PX, TODAY

ORDER = {
    "customer_name": "Cliente de Prueba",
    "customer_phone": "987000111",
    "address": "Av. Arequipa 2450",
    "district": "Lince",
    "latitude": -12.085,
    "longitude": -77.035,
    "weight_kg": 12.5,
    "scheduled_date": TODAY.isoformat(),
}


def pending_today(client, headers) -> list[dict]:
    return client.get(f"/api/orders?status=pendiente&date_from={TODAY}&date_to={TODAY}&size=100", headers=headers).json()["items"]


def test_create_and_filter_orders(client, dispatcher):
    res = client.post("/api/orders", headers=dispatcher, json=ORDER)
    assert res.status_code == 201
    body = res.json()
    assert body["code"].startswith("PED-260615-") and body["status"] == "pendiente"
    found = client.get("/api/orders?q=cliente de prueba", headers=dispatcher).json()
    assert found["total"] == 1
    assert len(pending_today(client, dispatcher)) == 10
    multi = client.get("/api/orders?status=entregado,fallido&size=1", headers=dispatcher).json()
    assert multi["total"] > 0 and multi["pages"] == multi["total"]


def test_order_validation(client, dispatcher):
    past = client.post("/api/orders", headers=dispatcher, json={**ORDER, "scheduled_date": "2026-06-01"})
    assert past.status_code == 422
    outside = client.post("/api/orders", headers=dispatcher, json={**ORDER, "latitude": 40.4, "longitude": -3.7})
    assert outside.status_code == 422


def test_route_preview_optimizes_order(client, dispatcher):
    ids = [o["id"] for o in pending_today(client, dispatcher)]
    res = client.post("/api/routes/preview", headers=dispatcher, json={"order_ids": ids})
    assert res.status_code == 200
    body = res.json()
    assert sorted(s["order_id"] for s in body["stops"]) == sorted(ids)
    assert body["total_km"] <= body["unoptimized_km"]
    assert [s["sequence"] for s in body["stops"]] == list(range(1, len(ids) + 1))


def test_create_route_assigns_and_sequences_orders(client, dispatcher):
    ids = [o["id"] for o in pending_today(client, dispatcher)]
    res = client.post(
        "/api/routes", headers=dispatcher, json={"route_date": TODAY.isoformat(), "vehicle_id": 2, "driver_id": 3, "order_ids": ids}
    )
    assert res.status_code == 201, res.text
    route = res.json()
    assert route["status"] == "planificada" and route["code"].startswith("R20260615-")
    assert [s["stop_sequence"] for s in route["stops"]] == list(range(1, len(ids) + 1))
    assert all(s["status"] == "asignado" for s in route["stops"])
    assert route["total_distance_km"] > 0 and 0 < route["utilization_pct"] <= 100
    assert pending_today(client, dispatcher) == []
    # Ni el vehículo ni el conductor pueden tener otra ruta activa ese día.
    again = client.post(
        "/api/routes", headers=dispatcher, json={"route_date": TODAY.isoformat(), "vehicle_id": 2, "driver_id": 3, "order_ids": [ids[0]]}
    )
    assert again.status_code == 409 and again.json()["code"] == "vehicle_busy"


def _route_error(client, headers, vehicle_id, driver_id, ids=None):
    ids = ids or [o["id"] for o in pending_today(client, headers)][:2]
    res = client.post(
        "/api/routes",
        headers=headers,
        json={"route_date": TODAY.isoformat(), "vehicle_id": vehicle_id, "driver_id": driver_id, "order_ids": ids},
    )
    return res.status_code, res.json().get("code")


def test_route_business_rules(client, dispatcher):
    assert _route_error(client, dispatcher, 3, 3) == (422, "tech_review_expired")
    assert _route_error(client, dispatcher, 5, 4) == (422, "maintenance_overdue")
    assert _route_error(client, dispatcher, 6, 3) == (422, "vehicle_unavailable")
    assert _route_error(client, dispatcher, 2, 4) == (422, "license_category")  # B-IIc no maneja furgonetas
    assert _route_error(client, dispatcher, 2, 5) == (422, "driver_unavailable")
    assert _route_error(client, dispatcher, 1, 3) == (409, "vehicle_busy")
    assert _route_error(client, dispatcher, 2, 1) == (409, "driver_busy")


def test_route_capacity_is_enforced(client, dispatcher):
    moto = {
        "plate": "7788-KT",
        "brand": "Yamaha",
        "model": "FZ",
        "year": 2024,
        "vehicle_type": "moto",
        "fuel_type": "gasolina",
        "capacity_kg": 40,
        "odometer_km": 100,
        "soat_expiry": "2027-01-01",
        "tech_review_expiry": "2027-01-01",
    }
    vid = client.post("/api/vehicles", headers=dispatcher, json=moto).json()["id"]
    ids = [o["id"] for o in pending_today(client, dispatcher)]
    assert _route_error(client, dispatcher, vid, 4, ids) == (422, "capacity_exceeded")


def test_orders_must_be_pending_and_same_date(client, dispatcher):
    tomorrow = client.get("/api/orders?status=pendiente&date_from=2026-06-16", headers=dispatcher).json()["items"][0]["id"]
    assert _route_error(client, dispatcher, 2, 3, [tomorrow])[0] == 422
    delivered = client.get("/api/orders?status=entregado", headers=dispatcher).json()["items"][0]["id"]
    assert _route_error(client, dispatcher, 2, 3, [delivered]) == (409, "order_not_pending")


def test_full_delivery_flow(client, dispatcher, driver1, driver2):
    routes = client.get("/api/routes/mine", headers=driver1).json()
    assert len(routes) == 1
    route = routes[0]
    assert route["status"] == "en_curso" and route["stops_done"] == 2
    pending = [s for s in route["stops"] if s["status"] == "en_ruta"]
    assert len(pending) == 4

    # Otro conductor no puede tocar paradas ajenas.
    assert client.post(f"/api/orders/{pending[0]['id']}/deliver", headers=driver2, data={"note": "x"}).status_code == 403
    # Sin foto ni nota no hay entrega.
    no_proof = client.post(f"/api/orders/{pending[0]['id']}/deliver", headers=driver1, data={})
    assert no_proof.status_code == 422 and no_proof.json()["code"] == "proof_required"
    # Archivo que no es imagen.
    fake = client.post(f"/api/orders/{pending[0]['id']}/deliver", headers=driver1, files={"photo": ("a.png", b"not-an-image", "image/png")})
    assert fake.status_code == 422 and fake.json()["code"] == "invalid_image"

    with_photo = client.post(
        f"/api/orders/{pending[0]['id']}/deliver", headers=driver1, files={"photo": ("foto.png", PNG_1PX, "image/png")}
    )
    assert with_photo.status_code == 200 and with_photo.json()["has_photo"] is True
    photo = client.get(f"/api/orders/{pending[0]['id']}/photo", headers=dispatcher)
    assert photo.status_code == 200 and photo.content == PNG_1PX

    note = client.post(f"/api/orders/{pending[1]['id']}/deliver", headers=driver1, data={"note": "Recibió el portero"})
    assert note.json()["status"] == "entregado" and note.json()["proof_note"] == "Recibió el portero"
    # Una entrega no se puede repetir.
    assert client.post(f"/api/orders/{pending[1]['id']}/deliver", headers=driver1, data={"note": "otra"}).status_code == 409

    failed = client.post(f"/api/orders/{pending[2]['id']}/fail", headers=driver1, json={"reason": "Cliente ausente"})
    assert failed.json()["status"] == "fallido"
    client.post(f"/api/orders/{pending[3]['id']}/deliver", headers=driver1, data={"note": "OK"})

    # Al cerrar la última parada la ruta se completa y el conductor queda disponible.
    done = client.get(f"/api/routes/{route['id']}", headers=dispatcher).json()
    assert done["status"] == "completada" and done["stops_done"] == 6
    assert client.get("/api/drivers/1", headers=dispatcher).json()["status"] == "disponible"

    # El pedido fallido se reprograma y vuelve a la bolsa de pendientes.
    res = client.post(f"/api/orders/{pending[2]['id']}/reschedule", headers=dispatcher, json={"scheduled_date": "2026-06-16"})
    assert res.status_code == 200 and res.json()["status"] == "pendiente" and res.json()["route_id"] is None


def test_driver_cannot_see_other_routes(client, driver2):
    assert client.get("/api/routes/13", headers=driver2).status_code == 403
    assert client.get("/api/routes/14", headers=driver2).status_code == 200


def test_start_and_cancel_planned_route(client, dispatcher):
    planned = client.get("/api/routes?status=planificada", headers=dispatcher).json()["items"][0]
    started = client.post(f"/api/routes/{planned['id']}/start", headers=dispatcher)
    assert started.status_code == 200
    assert all(s["status"] == "en_ruta" for s in started.json()["stops"])
    assert client.post(f"/api/routes/{planned['id']}/cancel", headers=dispatcher).status_code == 409


def test_cancel_route_returns_orders_to_pending(client, dispatcher):
    planned = client.get("/api/routes?status=planificada", headers=dispatcher).json()["items"][0]
    before = len(pending_today(client, dispatcher))
    res = client.post(f"/api/routes/{planned['id']}/cancel", headers=dispatcher)
    assert res.status_code == 200 and res.json()["status"] == "cancelada"
    assert len(pending_today(client, dispatcher)) == before + planned["stops_total"]


def test_cancel_assigned_order_resequences_route(client, dispatcher):
    planned = client.get("/api/routes?status=planificada", headers=dispatcher).json()["items"][0]
    detail = client.get(f"/api/routes/{planned['id']}", headers=dispatcher).json()
    first = detail["stops"][0]
    assert client.post(f"/api/orders/{first['id']}/cancel", headers=dispatcher).json()["status"] == "cancelado"
    after = client.get(f"/api/routes/{planned['id']}", headers=dispatcher).json()
    assert [s["stop_sequence"] for s in after["stops"]] == list(range(1, detail["stops_total"]))
    assert after["total_weight_kg"] < detail["total_weight_kg"]


def test_dashboard(client, dispatcher):
    body = client.get("/api/dashboard", headers=dispatcher).json()
    assert body["date"] == TODAY.isoformat()
    assert body["orders_today_total"] == 19
    assert body["orders_today"]["pendiente"] == 9
    assert body["routes_in_progress"] == 1
    assert len(body["delivered_last_7_days"]) == 7 and body["success_rate_30d"] > 50
    assert body["alerts_critical"] >= 2 and body["fuel_cost_month"] > 0
    assert len(body["map_orders"]) == 19
