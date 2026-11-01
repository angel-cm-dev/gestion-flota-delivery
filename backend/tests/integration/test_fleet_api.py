"""Vehículos, conductores, mantenimiento, combustible y alertas."""

NEW_VEHICLE = {
    "plate": "xyz 789",
    "brand": "Kia",
    "model": "K2700",
    "year": 2024,
    "vehicle_type": "camion",
    "fuel_type": "diesel",
    "capacity_kg": 2500,
    "odometer_km": 1000,
    "soat_expiry": "2027-01-01",
    "tech_review_expiry": "2027-01-01",
    "maintenance_interval_km": 5000,
    "last_maintenance_km": 0,
}


def test_vehicle_list_includes_document_and_maintenance_status(client, dispatcher):
    body = client.get("/api/vehicles?size=50", headers=dispatcher).json()
    by_plate = {v["plate"]: v for v in body["items"]}
    assert body["total"] == 6
    assert by_plate["C4F-512"]["soat"]["status"] == "por_vencer"
    assert by_plate["D7M-903"]["tech_review"]["status"] == "vencido"
    assert by_plate["C4F-512"]["maintenance"]["status"] == "proximo"
    assert by_plate["4521-LM"]["maintenance"]["status"] == "vencido"


def test_vehicle_filters_search_and_sort(client, dispatcher):
    assert client.get("/api/vehicles?vehicle_type=moto", headers=dispatcher).json()["total"] == 1
    assert client.get("/api/vehicles?status=inactivo", headers=dispatcher).json()["items"][0]["plate"] == "F2A-118"
    assert client.get("/api/vehicles?q=hiace", headers=dispatcher).json()["items"][0]["plate"] == "BXK-482"
    caps = [v["capacity_kg"] for v in client.get("/api/vehicles?sort=-capacity_kg", headers=dispatcher).json()["items"]]
    assert caps == sorted(caps, reverse=True)
    assert client.get("/api/vehicles?sort=drop_table", headers=dispatcher).status_code == 200  # columna no permitida: se ignora


def test_create_vehicle_normalizes_plate_and_rejects_duplicates(client, dispatcher):
    res = client.post("/api/vehicles", headers=dispatcher, json=NEW_VEHICLE)
    assert res.status_code == 201
    assert res.json()["plate"] == "XYZ-789" and res.json()["status"] == "activo"
    dup = client.post("/api/vehicles", headers=dispatcher, json={**NEW_VEHICLE, "plate": "XYZ-789"})
    assert dup.status_code == 409 and dup.json()["code"] == "plate_taken"


def test_invalid_plate_is_rejected(client, dispatcher):
    res = client.post("/api/vehicles", headers=dispatcher, json={**NEW_VEHICLE, "plate": "12-ABCD"})
    assert res.status_code == 422
    assert res.json()["errors"][0]["field"] == "plate"


def test_odometer_cannot_go_back(client, dispatcher):
    v = client.get("/api/vehicles/1", headers=dispatcher).json()
    payload = {k: v[k] for k in NEW_VEHICLE if k in v} | {
        "soat_expiry": v["soat"]["expiry"],
        "tech_review_expiry": v["tech_review"]["expiry"],
    }
    res = client.put(
        "/api/vehicles/1", headers=dispatcher, json={**payload, "odometer_km": 100, "last_maintenance_km": 0, "status": "activo"}
    )
    assert res.status_code == 422 and res.json()["code"] == "odometer_decrease"


def test_vehicle_with_routes_cannot_be_deleted(client, admin):
    res = client.delete("/api/vehicles/1", headers=admin)
    assert res.status_code == 409
    created = client.post("/api/vehicles", headers=admin, json=NEW_VEHICLE).json()
    assert client.delete(f"/api/vehicles/{created['id']}", headers=admin).status_code == 204
    assert client.get(f"/api/vehicles/{created['id']}", headers=admin).status_code == 404


def test_driver_license_must_match_dni(client, dispatcher):
    base = {
        "full_name": "Pedro Ramos",
        "dni": "40123456",
        "phone": "912345678",
        "license_category": "A-IIb",
        "license_expiry": "2028-01-01",
    }
    bad = client.post("/api/drivers", headers=dispatcher, json={**base, "license_number": "Q99999999"})
    assert bad.status_code == 422 and bad.json()["code"] == "license_dni_mismatch"
    ok = client.post("/api/drivers", headers=dispatcher, json={**base, "license_number": "q40123456"})
    assert ok.status_code == 201 and ok.json()["license_number"] == "Q40123456"
    assert client.post("/api/drivers", headers=dispatcher, json={**base, "license_number": "Q40123456"}).status_code == 409


def test_driver_user_link_requires_conductor_role(client, dispatcher):
    payload = {
        "full_name": "Pedro Ramos",
        "dni": "40123456",
        "phone": "912345678",
        "license_number": "Q40123456",
        "license_category": "A-IIb",
        "license_expiry": "2028-01-01",
        "user_id": 2,
    }
    assert client.post("/api/drivers", headers=dispatcher, json=payload).status_code == 422


def test_drivers_search(client, dispatcher):
    body = client.get("/api/drivers?q=45781236", headers=dispatcher).json()
    assert body["total"] == 1 and body["items"][0]["full_name"] == "Juan Pérez Quispe"
    rosa = client.get("/api/drivers/2", headers=dispatcher).json()
    assert rosa["license"]["status"] == "por_vencer"


def test_preventive_maintenance_resets_counter(client, dispatcher):
    res = client.post(
        "/api/maintenance",
        headers=dispatcher,
        json={
            "vehicle_id": 5,
            "kind": "preventivo",
            "description": "Cambio de aceite",
            "odometer_km": 16_000,
            "cost": 150,
            "service_date": "2026-06-14",
        },
    )
    assert res.status_code == 201 and res.json()["vehicle_plate"] == "4521-LM"
    moto = client.get("/api/vehicles/5", headers=dispatcher).json()
    assert moto["last_maintenance_km"] == 16_000 and moto["odometer_km"] == 16_000
    assert moto["maintenance"]["status"] == "al_dia"
    overview = client.get("/api/maintenance/overview", headers=dispatcher).json()
    assert overview[0]["maintenance"]["km_remaining"] <= overview[-1]["maintenance"]["km_remaining"]


def test_maintenance_in_future_is_rejected(client, dispatcher):
    res = client.post(
        "/api/maintenance",
        headers=dispatcher,
        json={
            "vehicle_id": 1,
            "kind": "correctivo",
            "description": "Llanta",
            "odometer_km": 48_300,
            "cost": 90,
            "service_date": "2026-07-01",
        },
    )
    assert res.status_code == 422


def test_fuel_log_requires_increasing_odometer_and_reports_efficiency(client, dispatcher):
    eff = client.get("/api/fuel/efficiency/1", headers=dispatcher).json()
    assert len(eff["points"]) == 5 and eff["avg_km_per_liter"] > 0
    bad = client.post(
        "/api/fuel",
        headers=dispatcher,
        json={"vehicle_id": 1, "fill_date": "2026-06-15", "liters": 40, "total_cost": 700, "odometer_km": 1000},
    )
    assert bad.status_code == 422 and bad.json()["code"] == "odometer_not_increasing"
    ok = client.post(
        "/api/fuel",
        headers=dispatcher,
        json={"vehicle_id": 1, "fill_date": "2026-06-15", "liters": 40, "total_cost": 700, "odometer_km": 48_700},
    )
    assert ok.status_code == 201
    assert client.get("/api/vehicles/1", headers=dispatcher).json()["odometer_km"] == 48_700
    assert client.get("/api/fuel?vehicle_id=1", headers=dispatcher).json()["total"] == 7


def test_driver_can_only_log_fuel_for_own_vehicle(client, driver1):
    other = client.post(
        "/api/fuel",
        headers=driver1,
        json={"vehicle_id": 2, "fill_date": "2026-06-15", "liters": 30, "total_cost": 500, "odometer_km": 70_000},
    )
    assert other.status_code == 403
    own = client.post(
        "/api/fuel",
        headers=driver1,
        json={"vehicle_id": 1, "fill_date": "2026-06-15", "liters": 30, "total_cost": 500, "odometer_km": 48_800},
    )
    assert own.status_code == 201 and own.json()["driver_id"] == 1


def test_alerts(client, dispatcher):
    alerts = client.get("/api/alerts", headers=dispatcher).json()
    kinds = {(a["kind"], a["entity_label"], a["severity"]) for a in alerts}
    assert ("revision_tecnica", "D7M-903", "critica") in kinds
    assert ("soat", "C4F-512", "advertencia") in kinds
    assert ("licencia", "Rosa Huamán Torres", "advertencia") in kinds
    assert ("mantenimiento", "4521-LM", "critica") in kinds
    # Vehículos y conductores inactivos no generan alertas.
    assert not any(a["entity_label"] in ("F2A-118", "Elena Castillo Paredes") for a in alerts)
    assert alerts[0]["severity"] == "critica"
