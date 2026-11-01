"""Conversión de entidades ORM a DTOs, enriquecidas con reglas de dominio
(vigencia de documentos, estado de mantenimiento, avance de la ruta)."""

from datetime import date

from app.application import schemas as s
from app.core.config import Settings
from app.domain.delivery import FINAL_STATES
from app.domain.documents import document_status
from app.domain.maintenance import maintenance_status
from app.infrastructure.models import Driver, FuelLog, MaintenanceRecord, Order, Route, User, Vehicle


def doc_info(expiry: date, today: date, warning_days: int) -> s.DocumentInfo:
    check = document_status(expiry, today, warning_days)
    return s.DocumentInfo(expiry=expiry, status=check.status, days_left=check.days_left)


def maintenance_info(v: Vehicle, warning_km: int) -> s.MaintenanceInfo:
    check = maintenance_status(v.odometer_km, v.last_maintenance_km, v.maintenance_interval_km, warning_km)
    return s.MaintenanceInfo(status=check.status, next_due_km=check.next_due_km, km_remaining=check.km_remaining)


def user_out(u: User) -> s.UserOut:
    return s.UserOut(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        role=u.role,
        is_active=u.is_active,
        created_at=u.created_at,
        driver_id=u.driver.id if u.driver else None,
    )


def vehicle_out(v: Vehicle, today: date, settings: Settings) -> s.VehicleOut:
    return s.VehicleOut(
        id=v.id,
        plate=v.plate,
        brand=v.brand,
        model=v.model,
        year=v.year,
        vehicle_type=v.vehicle_type,
        fuel_type=v.fuel_type,
        capacity_kg=v.capacity_kg,
        odometer_km=v.odometer_km,
        maintenance_interval_km=v.maintenance_interval_km,
        last_maintenance_km=v.last_maintenance_km,
        status=v.status,
        soat=doc_info(v.soat_expiry, today, settings.document_warning_days),
        tech_review=doc_info(v.tech_review_expiry, today, settings.document_warning_days),
        maintenance=maintenance_info(v, settings.maintenance_warning_km),
        created_at=v.created_at,
    )


def driver_out(d: Driver, today: date, settings: Settings) -> s.DriverOut:
    return s.DriverOut(
        id=d.id,
        full_name=d.full_name,
        dni=d.dni,
        phone=d.phone,
        license_number=d.license_number,
        license_category=d.license_category,
        status=d.status,
        user_id=d.user_id,
        license=doc_info(d.license_expiry, today, settings.document_warning_days),
        created_at=d.created_at,
    )


def order_out(o: Order) -> s.OrderOut:
    out = s.OrderOut.model_validate(o)
    out.has_photo = bool(o.proof_photo_path)
    return out


def route_out(r: Route, *, detail: bool = False) -> s.RouteOut | s.RouteDetail:
    orders = sorted(r.orders, key=lambda o: (o.stop_sequence or 0, o.id))
    data = dict(
        id=r.id,
        code=r.code,
        route_date=r.route_date,
        status=r.status,
        vehicle=s.VehicleRef.model_validate(r.vehicle),
        driver=s.DriverRef.model_validate(r.driver),
        depot_lat=r.depot_lat,
        depot_lng=r.depot_lng,
        total_distance_km=r.total_distance_km,
        total_weight_kg=r.total_weight_kg,
        utilization_pct=round(100 * r.total_weight_kg / r.vehicle.capacity_kg, 1) if r.vehicle.capacity_kg else 0,
        stops_total=len(orders),
        stops_done=sum(1 for o in orders if o.status in FINAL_STATES),
        started_at=r.started_at,
        completed_at=r.completed_at,
        created_at=r.created_at,
    )
    if detail:
        return s.RouteDetail(**data, stops=[order_out(o) for o in orders])
    return s.RouteOut(**data)


def maintenance_out(m: MaintenanceRecord) -> s.MaintenanceOut:
    return s.MaintenanceOut(
        id=m.id,
        vehicle_id=m.vehicle_id,
        vehicle_plate=m.vehicle.plate,
        kind=m.kind,
        description=m.description,
        odometer_km=m.odometer_km,
        cost=m.cost,
        service_date=m.service_date,
        workshop=m.workshop,
        created_at=m.created_at,
    )


def fuel_out(f: FuelLog) -> s.FuelOut:
    return s.FuelOut(
        id=f.id,
        vehicle_id=f.vehicle_id,
        vehicle_plate=f.vehicle.plate,
        driver_id=f.driver_id,
        fill_date=f.fill_date,
        liters=f.liters,
        total_cost=f.total_cost,
        odometer_km=f.odometer_km,
        station=f.station,
        created_at=f.created_at,
    )
