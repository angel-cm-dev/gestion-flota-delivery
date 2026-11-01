"""Pruebas unitarias de reglas de dominio puras (sin base de datos ni HTTP)."""

from datetime import date, timedelta

import pytest

from app.domain.delivery import ensure_capacity, ensure_transition, validate_delivery_proof
from app.domain.documents import document_status, is_valid_on
from app.domain.enums import DocumentStatus, MaintenanceStatus, OrderStatus, VehicleType
from app.domain.errors import ConflictError, DomainError
from app.domain.fuel import cost_per_km, ensure_odometer_increases, km_per_liter
from app.domain.licenses import can_drive, normalize_license_number, validate_category
from app.domain.maintenance import maintenance_status
from app.domain.plates import is_motorcycle_plate, normalize_plate

# ------------------------------------------------------------------ placas


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ABC-123", "ABC-123"),
        ("abc123", "ABC-123"),
        (" a1b 234 ", "A1B-234"),
        ("C4F-512", "C4F-512"),
        ("4521lm", "4521-LM"),
        ("4521-LM", "4521-LM"),
    ],
)
def test_normalize_valid_plates(raw, expected):
    assert normalize_plate(raw) == expected


@pytest.mark.parametrize("raw", ["", "AB-123", "ABCD-123", "1BC-123", "ABC-12", "ABC-1234", "123-ABC", "45-LM", "ÑBC-123"])
def test_reject_invalid_plates(raw):
    with pytest.raises(ValueError):
        normalize_plate(raw)


def test_detects_motorcycle_plate():
    assert is_motorcycle_plate("4521-LM")
    assert not is_motorcycle_plate("ABC-123")


# ------------------------------------------------------------------ licencias


@pytest.mark.parametrize(
    ("category", "vtype", "allowed"),
    [
        ("A-I", VehicleType.AUTO, True),
        ("A-I", VehicleType.FURGONETA, False),
        ("A-IIa", VehicleType.FURGONETA, True),
        ("A-IIa", VehicleType.CAMION, False),
        ("A-IIb", VehicleType.CAMION, True),
        ("A-IIIc", VehicleType.CAMION, True),
        ("B-IIc", VehicleType.MOTO, True),
        ("B-I", VehicleType.MOTO, False),
        ("A-IIIc", VehicleType.MOTO, False),
        ("B-IIc", VehicleType.AUTO, False),
    ],
)
def test_license_category_matrix(category, vtype, allowed):
    assert can_drive(category, vtype) is allowed


def test_license_number_format():
    assert normalize_license_number(" q45781236 ") == "Q45781236"
    with pytest.raises(ValueError):
        normalize_license_number("45781236")
    with pytest.raises(ValueError):
        validate_category("C-I")


# ------------------------------------------------------------------ documentos

TODAY = date(2026, 6, 15)


@pytest.mark.parametrize(
    ("offset", "status"),
    [(-1, DocumentStatus.VENCIDO), (0, DocumentStatus.POR_VENCER), (30, DocumentStatus.POR_VENCER), (31, DocumentStatus.VIGENTE)],
)
def test_document_status_boundaries(offset, status):
    check = document_status(TODAY + timedelta(days=offset), TODAY, warning_days=30)
    assert check.status == status
    assert check.days_left == offset


def test_document_valid_until_expiry_day_inclusive():
    assert is_valid_on(TODAY, TODAY)
    assert not is_valid_on(TODAY, TODAY + timedelta(days=1))


# ------------------------------------------------------------------ pedidos y capacidad


def test_allowed_order_transitions():
    ensure_transition(OrderStatus.PENDIENTE, OrderStatus.ASIGNADO)
    ensure_transition(OrderStatus.EN_RUTA, OrderStatus.ENTREGADO)
    ensure_transition(OrderStatus.FALLIDO, OrderStatus.PENDIENTE)


@pytest.mark.parametrize(
    ("current", "new"),
    [
        (OrderStatus.PENDIENTE, OrderStatus.ENTREGADO),
        (OrderStatus.ENTREGADO, OrderStatus.CANCELADO),
        (OrderStatus.EN_RUTA, OrderStatus.CANCELADO),
        (OrderStatus.CANCELADO, OrderStatus.PENDIENTE),
    ],
)
def test_forbidden_order_transitions(current, new):
    with pytest.raises(ConflictError):
        ensure_transition(current, new)


def test_delivery_requires_photo_or_note():
    validate_delivery_proof("Recibió el portero", has_photo=False)
    validate_delivery_proof(None, has_photo=True)
    with pytest.raises(DomainError) as exc:
        validate_delivery_proof("   ", has_photo=False)
    assert exc.value.code == "proof_required"


def test_capacity_rule():
    assert ensure_capacity(100, [40, 60]) == 100
    with pytest.raises(DomainError) as exc:
        ensure_capacity(100, [40, 60.5])
    assert exc.value.code == "capacity_exceeded"


# ------------------------------------------------------------------ mantenimiento y combustible


@pytest.mark.parametrize(
    ("odometer", "status", "remaining"),
    [
        (9_000, MaintenanceStatus.AL_DIA, 1000),
        (9_500, MaintenanceStatus.PROXIMO, 500),
        (10_000, MaintenanceStatus.VENCIDO, 0),
        (10_300, MaintenanceStatus.VENCIDO, -300),
    ],
)
def test_maintenance_status(odometer, status, remaining):
    check = maintenance_status(odometer, last_maintenance_km=5_000, interval_km=5_000, warning_km=500)
    assert check.status == status
    assert check.next_due_km == 10_000
    assert check.km_remaining == remaining


def test_maintenance_interval_must_be_positive():
    with pytest.raises(ValueError):
        maintenance_status(100, 0, 0)


def test_fuel_rules():
    assert km_per_liter(10_000, 10_450, 45) == 10.0
    assert cost_per_km(90, 450) == 0.2
    assert cost_per_km(90, 0) is None
    ensure_odometer_increases(None, 100)
    with pytest.raises(DomainError):
        ensure_odometer_increases(1000, 1000)
