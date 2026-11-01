"""Validación de DTOs y del almacenamiento de fotos."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.application.schemas import DriverCreate, OrderCreate, RouteCreate, UserCreate, VehicleCreate
from app.domain.errors import DomainError
from app.infrastructure.storage import LocalFileStorage, detect_image_extension
from tests.conftest import PNG_1PX

ORDER = dict(
    customer_name="Cliente Demo",
    customer_phone="987654321",
    address="Av. Arequipa 123",
    district="Lince",
    latitude=-12.08,
    longitude=-77.03,
    weight_kg=5,
    scheduled_date=date(2026, 6, 15),
)


def test_order_rejects_coordinates_outside_peru():
    OrderCreate(**ORDER)
    with pytest.raises(ValidationError):
        OrderCreate(**{**ORDER, "latitude": -77.03, "longitude": -12.08})  # lat/lng invertidas


def test_vehicle_dto_normalizes_plate():
    v = VehicleCreate(
        plate="bxk 482",
        brand="Toyota",
        model="Hiace",
        year=2021,
        vehicle_type="furgoneta",
        fuel_type="diesel",
        capacity_kg=1000,
        odometer_km=10,
        soat_expiry=date(2027, 1, 1),
        tech_review_expiry=date(2027, 1, 1),
    )
    assert v.plate == "BXK-482"


@pytest.mark.parametrize("pwd", ["corta1A", "sinnumeros", "SINMINUSCULA1", "sinmayuscula1"])
def test_password_policy(pwd):
    with pytest.raises(ValidationError):
        UserCreate(email="x@demo.pe", full_name="Usuario X", password=pwd, role="despachador")


def test_driver_dto_validates_formats():
    with pytest.raises(ValidationError):
        DriverCreate(
            full_name="Ana Ríos",
            dni="1234567",
            phone="987654321",
            license_number="Q12345678",
            license_category="A-I",
            license_expiry=date(2027, 1, 1),
        )


def test_route_rejects_duplicate_orders():
    with pytest.raises(ValidationError):
        RouteCreate(route_date=date(2026, 6, 15), vehicle_id=1, driver_id=1, order_ids=[1, 1])


def test_storage_validates_magic_bytes(tmp_path):
    storage = LocalFileStorage(str(tmp_path), max_bytes=1024)
    name = storage.save_image(PNG_1PX, prefix="PED-1")
    assert name.endswith(".png") and storage.resolve(name).exists()
    assert detect_image_extension(b"GIF89a") is None
    with pytest.raises(DomainError):
        storage.save_image(b"%PDF-1.4 not an image", prefix="x")
    with pytest.raises(DomainError):
        storage.save_image(PNG_1PX + b"0" * 2048, prefix="x")
    with pytest.raises(DomainError):
        storage.resolve("../secreto.txt")
