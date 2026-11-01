"""DTOs (Pydantic v2): contratos de entrada y salida de la API.

Separar los DTOs de los modelos ORM evita exponer columnas internas (p. ej.
``password_hash``) y permite validar la entrada antes de llegar al dominio.
"""

import re
from datetime import date, datetime
from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.domain.enums import (
    DocumentStatus,
    DriverStatus,
    FuelType,
    MaintenanceKind,
    MaintenanceStatus,
    OrderStatus,
    Role,
    RouteStatus,
    VehicleStatus,
    VehicleType,
)
from app.domain.licenses import normalize_license_number, validate_category
from app.domain.plates import normalize_plate

T = TypeVar("T")

# Rectángulo aproximado que contiene el territorio peruano. Rechazar
# coordenadas fuera de él detecta el error típico de invertir lat/lng.
PERU_LAT = (-18.4, 0.1)
PERU_LNG = (-81.4, -68.6)


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def build(cls, items: list[T], total: int, page: int, size: int) -> "Page[T]":
        return cls(items=items, total=total, page=page, size=size, pages=ceil(total / size) if size else 0)


# ---------------------------------------------------------------- Auth / usuarios


def validate_password_policy(value: str) -> str:
    """Mínimo 8 caracteres con mayúscula, minúscula y dígito."""
    if len(value) < 8 or not re.search(r"[A-Z]", value) or not re.search(r"[a-z]", value) or not re.search(r"\d", value):
        raise ValueError("La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula y un número")
    return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(ORM):
    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime
    driver_id: int | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=3, max_length=120)
    password: str = Field(max_length=128)
    role: Role

    @field_validator("password")
    @classmethod
    def _pwd(cls, v: str) -> str:
        return validate_password_policy(v)


class UserUpdate(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    role: Role
    is_active: bool
    password: str | None = Field(default=None, max_length=128)

    @field_validator("password")
    @classmethod
    def _pwd(cls, v: str | None) -> str | None:
        return validate_password_policy(v) if v else None


# ---------------------------------------------------------------- Vehículos


class VehicleBase(BaseModel):
    plate: str = Field(examples=["ABC-123"])
    brand: str = Field(min_length=2, max_length=60)
    model: str = Field(min_length=1, max_length=60)
    year: int = Field(ge=1990, le=2100)
    vehicle_type: VehicleType
    fuel_type: FuelType
    capacity_kg: float = Field(gt=0, le=40000)
    odometer_km: int = Field(ge=0, le=2_000_000)
    soat_expiry: date
    tech_review_expiry: date
    maintenance_interval_km: int = Field(default=5000, ge=500, le=100_000)
    last_maintenance_km: int = Field(default=0, ge=0)

    @field_validator("plate")
    @classmethod
    def _plate(cls, v: str) -> str:
        return normalize_plate(v)


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(VehicleBase):
    status: VehicleStatus


class DocumentInfo(BaseModel):
    expiry: date
    status: DocumentStatus
    days_left: int


class MaintenanceInfo(BaseModel):
    status: MaintenanceStatus
    next_due_km: int
    km_remaining: int


class VehicleOut(ORM):
    id: int
    plate: str
    brand: str
    model: str
    year: int
    vehicle_type: VehicleType
    fuel_type: FuelType
    capacity_kg: float
    odometer_km: int
    maintenance_interval_km: int
    last_maintenance_km: int
    status: VehicleStatus
    soat: DocumentInfo
    tech_review: DocumentInfo
    maintenance: MaintenanceInfo
    created_at: datetime


# ---------------------------------------------------------------- Conductores


class DriverBase(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    dni: str = Field(pattern=r"^\d{8}$", examples=["45781236"])
    phone: str = Field(pattern=r"^9\d{8}$", examples=["987654321"], description="Celular peruano de 9 dígitos")
    license_number: str = Field(examples=["Q45781236"])
    license_category: str = Field(examples=["A-IIb"])
    license_expiry: date
    user_id: int | None = None

    @field_validator("license_number")
    @classmethod
    def _license(cls, v: str) -> str:
        return normalize_license_number(v)

    @field_validator("license_category")
    @classmethod
    def _category(cls, v: str) -> str:
        return validate_category(v)


class DriverCreate(DriverBase):
    pass


class DriverUpdate(DriverBase):
    status: DriverStatus


class DriverOut(ORM):
    id: int
    full_name: str
    dni: str
    phone: str
    license_number: str
    license_category: str
    status: DriverStatus
    user_id: int | None
    license: DocumentInfo
    created_at: datetime


# ---------------------------------------------------------------- Pedidos


class OrderBase(BaseModel):
    customer_name: str = Field(min_length=3, max_length=120)
    customer_phone: str = Field(pattern=r"^9\d{8}$")
    address: str = Field(min_length=5, max_length=255)
    district: str = Field(min_length=2, max_length=80)
    latitude: float = Field(ge=PERU_LAT[0], le=PERU_LAT[1])
    longitude: float = Field(ge=PERU_LNG[0], le=PERU_LNG[1])
    weight_kg: float = Field(gt=0, le=5000)
    scheduled_date: date
    notes: str | None = Field(default=None, max_length=500)


class OrderCreate(OrderBase):
    pass


class OrderUpdate(OrderBase):
    pass


class OrderOut(ORM):
    id: int
    code: str
    customer_name: str
    customer_phone: str
    address: str
    district: str
    latitude: float
    longitude: float
    weight_kg: float
    scheduled_date: date
    notes: str | None
    status: OrderStatus
    route_id: int | None
    stop_sequence: int | None
    delivered_at: datetime | None
    proof_note: str | None
    has_photo: bool = False
    failure_reason: str | None
    created_at: datetime


class FailRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=255, examples=["Cliente ausente"])


class RescheduleRequest(BaseModel):
    scheduled_date: date


# ---------------------------------------------------------------- Rutas


class RouteCreate(BaseModel):
    route_date: date
    vehicle_id: int
    driver_id: int
    order_ids: list[int] = Field(min_length=1, max_length=60)

    @field_validator("order_ids")
    @classmethod
    def _unique(cls, v: list[int]) -> list[int]:
        if len(set(v)) != len(v):
            raise ValueError("Hay pedidos repetidos en la ruta")
        return v


class RoutePreviewRequest(BaseModel):
    order_ids: list[int] = Field(min_length=1, max_length=60)
    depot_lat: float | None = None
    depot_lng: float | None = None


class RoutePreviewStop(BaseModel):
    sequence: int
    order_id: int
    code: str
    latitude: float
    longitude: float
    leg_km: float


class RoutePreview(BaseModel):
    depot_lat: float
    depot_lng: float
    stops: list[RoutePreviewStop]
    total_km: float
    unoptimized_km: float
    savings_pct: float
    total_weight_kg: float


class VehicleRef(ORM):
    id: int
    plate: str
    vehicle_type: VehicleType
    capacity_kg: float


class DriverRef(ORM):
    id: int
    full_name: str
    phone: str


class RouteOut(ORM):
    id: int
    code: str
    route_date: date
    status: RouteStatus
    vehicle: VehicleRef
    driver: DriverRef
    depot_lat: float
    depot_lng: float
    total_distance_km: float
    total_weight_kg: float
    utilization_pct: float
    stops_total: int
    stops_done: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class RouteDetail(RouteOut):
    stops: list[OrderOut]


# ---------------------------------------------------------------- Mantenimiento


class MaintenanceCreate(BaseModel):
    vehicle_id: int
    kind: MaintenanceKind
    description: str = Field(min_length=3, max_length=255)
    odometer_km: int = Field(ge=0)
    cost: float = Field(ge=0, le=1_000_000)
    service_date: date
    workshop: str | None = Field(default=None, max_length=120)


class MaintenanceOut(ORM):
    id: int
    vehicle_id: int
    vehicle_plate: str
    kind: MaintenanceKind
    description: str
    odometer_km: int
    cost: float
    service_date: date
    workshop: str | None
    created_at: datetime


class MaintenanceOverview(BaseModel):
    vehicle_id: int
    plate: str
    odometer_km: int
    maintenance: MaintenanceInfo


# ---------------------------------------------------------------- Combustible


class FuelCreate(BaseModel):
    vehicle_id: int
    fill_date: date
    liters: float = Field(gt=0, le=1000)
    total_cost: float = Field(ge=0, le=100_000)
    odometer_km: int = Field(ge=0)
    station: str | None = Field(default=None, max_length=120)


class FuelOut(ORM):
    id: int
    vehicle_id: int
    vehicle_plate: str
    driver_id: int | None
    fill_date: date
    liters: float
    total_cost: float
    odometer_km: int
    station: str | None
    created_at: datetime


class FuelEfficiencyPoint(BaseModel):
    fill_date: date
    odometer_km: int
    liters: float
    km: int
    km_per_liter: float
    cost_per_km: float | None


class FuelEfficiency(BaseModel):
    vehicle_id: int
    plate: str
    points: list[FuelEfficiencyPoint]
    avg_km_per_liter: float | None
    total_liters: float
    total_cost: float


# ---------------------------------------------------------------- Alertas / dashboard


class AlertOut(BaseModel):
    kind: str = Field(description="soat | revision_tecnica | licencia | mantenimiento")
    severity: str = Field(description="critica | advertencia")
    entity_type: str
    entity_id: int
    entity_label: str
    message: str
    due_date: date | None = None
    days_left: int | None = None
    km_remaining: int | None = None


class MapOrder(BaseModel):
    id: int
    code: str
    customer_name: str
    latitude: float
    longitude: float
    status: OrderStatus


class Dashboard(BaseModel):
    date: date
    orders_today: dict[str, int]
    orders_today_total: int
    success_rate_30d: float | None
    delivered_last_7_days: list[dict]
    vehicles_by_status: dict[str, int]
    drivers_available: int
    routes_in_progress: int
    alerts_critical: int
    alerts_warning: int
    fuel_cost_month: float
    map_orders: list[MapOrder]
    depot_lat: float
    depot_lng: float
