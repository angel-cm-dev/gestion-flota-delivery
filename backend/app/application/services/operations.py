"""Casos de uso de operación: mantenimiento, combustible, alertas y dashboard."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select

from app.application import schemas as s
from app.application.mappers import fuel_out, maintenance_info, maintenance_out
from app.application.services.base import Service
from app.domain.documents import document_status
from app.domain.enums import DocumentStatus, DriverStatus, MaintenanceKind, MaintenanceStatus, Role, RouteStatus, VehicleStatus
from app.domain.errors import DomainError, ForbiddenError, NotFoundError
from app.domain.fuel import cost_per_km, ensure_odometer_increases, km_per_liter
from app.domain.maintenance import maintenance_status
from app.infrastructure.models import Driver, FuelLog, MaintenanceRecord, Route, User, Vehicle
from app.infrastructure.repositories import (
    DriverRepository,
    FuelRepository,
    MaintenanceRepository,
    OrderRepository,
    RouteRepository,
    VehicleRepository,
)


def _vehicle(session, vehicle_id: int) -> Vehicle:
    v = VehicleRepository(session).get(vehicle_id)
    if not v:
        raise NotFoundError("Vehículo no encontrado")
    return v


class MaintenanceService(Service):
    @property
    def repo(self) -> MaintenanceRepository:
        return MaintenanceRepository(self.session)

    def list(self, *, vehicle_id, kind, page, size, sort) -> s.Page[s.MaintenanceOut]:
        rows, total = self.repo.paginate(self.repo.search(vehicle_id=vehicle_id, kind=kind), page=page, size=size, sort=sort)
        return s.Page.build([maintenance_out(m) for m in rows], total, page, size)

    def create(self, data: s.MaintenanceCreate) -> s.MaintenanceOut:
        v = _vehicle(self.session, data.vehicle_id)
        if data.service_date > self.today():
            raise DomainError("La fecha del servicio no puede ser futura")
        if data.kind == MaintenanceKind.PREVENTIVO and data.odometer_km < v.last_maintenance_km:
            raise DomainError("El kilometraje es menor al del último mantenimiento preventivo registrado")
        m = self.repo.add(MaintenanceRecord(**data.model_dump()))
        # Registrar un servicio con un kilometraje mayor actualiza el odómetro.
        v.odometer_km = max(v.odometer_km, data.odometer_km)
        # Solo el preventivo reinicia el contador: un correctivo (p. ej. cambiar
        # una llanta) no reemplaza el cambio de aceite programado.
        if data.kind == MaintenanceKind.PREVENTIVO:
            v.last_maintenance_km = data.odometer_km
            if v.status == VehicleStatus.MANTENIMIENTO:
                v.status = VehicleStatus.ACTIVO
        self.commit()
        self.session.refresh(m)
        return maintenance_out(m)

    def overview(self) -> list[s.MaintenanceOverview]:
        """Estado de mantenimiento de toda la flota, de lo más urgente a lo menos."""
        items = [
            s.MaintenanceOverview(
                vehicle_id=v.id,
                plate=v.plate,
                odometer_km=v.odometer_km,
                maintenance=maintenance_info(v, self.settings.maintenance_warning_km),
            )
            for v in VehicleRepository(self.session).all()
            if v.status != VehicleStatus.INACTIVO
        ]
        return sorted(items, key=lambda x: x.maintenance.km_remaining)


class FuelService(Service):
    @property
    def repo(self) -> FuelRepository:
        return FuelRepository(self.session)

    def list(self, *, vehicle_id, date_from, date_to, page, size, sort) -> s.Page[s.FuelOut]:
        stmt = self.repo.search(vehicle_id=vehicle_id, date_from=date_from, date_to=date_to)
        rows, total = self.repo.paginate(stmt, page=page, size=size, sort=sort)
        return s.Page.build([fuel_out(f) for f in rows], total, page, size)

    def create(self, data: s.FuelCreate, *, user: User) -> s.FuelOut:
        v = _vehicle(self.session, data.vehicle_id)
        if data.fill_date > self.today():
            raise DomainError("La fecha de carga no puede ser futura")
        driver_id: int | None = None
        if user.role == Role.CONDUCTOR:
            # El conductor solo registra cargas del vehículo que tiene asignado ese día.
            driver = DriverRepository(self.session).by_user(user.id)
            route = None
            if driver:
                route = self.session.scalars(
                    select(Route).where(
                        Route.driver_id == driver.id,
                        Route.vehicle_id == v.id,
                        Route.route_date == data.fill_date,
                        Route.status != RouteStatus.CANCELADA,
                    )
                ).first()
            if not driver or not route:
                raise ForbiddenError("Solo puedes registrar combustible del vehículo de tu ruta del día")
            driver_id = driver.id
        last = self.repo.last_for_vehicle(v.id)
        ensure_odometer_increases(last.odometer_km if last else None, data.odometer_km)
        f = self.repo.add(FuelLog(**data.model_dump(), driver_id=driver_id))
        v.odometer_km = max(v.odometer_km, data.odometer_km)
        self.commit()
        self.session.refresh(f)
        return fuel_out(f)

    def efficiency(self, vehicle_id: int) -> s.FuelEfficiency:
        v = _vehicle(self.session, vehicle_id)
        logs = self.repo.history(v.id)
        points: list[s.FuelEfficiencyPoint] = []
        # La primera carga solo sirve de referencia: no se sabe cuántos km rindió.
        for prev, cur in zip(logs, logs[1:], strict=False):
            km = cur.odometer_km - prev.odometer_km
            points.append(
                s.FuelEfficiencyPoint(
                    fill_date=cur.fill_date,
                    odometer_km=cur.odometer_km,
                    liters=cur.liters,
                    km=km,
                    km_per_liter=km_per_liter(prev.odometer_km, cur.odometer_km, cur.liters),
                    cost_per_km=cost_per_km(cur.total_cost, km),
                )
            )
        measured_km = sum(p.km for p in points)
        measured_liters = sum(p.liters for p in points)
        return s.FuelEfficiency(
            vehicle_id=v.id,
            plate=v.plate,
            points=points,
            avg_km_per_liter=round(measured_km / measured_liters, 2) if measured_liters else None,
            total_liters=round(sum(f.liters for f in logs), 2),
            total_cost=round(sum(f.total_cost for f in logs), 2),
        )


class AlertService(Service):
    """Alertas calculadas al vuelo (no se guardan): siempre reflejan el estado actual."""

    def list(self) -> list[s.AlertOut]:
        today, warn_days = self.today(), self.settings.document_warning_days
        alerts: list[s.AlertOut] = []

        def doc_alert(kind: str, label: str, entity_type: str, entity_id: int, name: str, expiry: date) -> None:
            check = document_status(expiry, today, warn_days)
            if check.status == DocumentStatus.VIGENTE:
                return
            expired = check.status == DocumentStatus.VENCIDO
            msg = f"{label} de {name} " + (f"vencido hace {-check.days_left} día(s)" if expired else f"vence en {check.days_left} día(s)")
            alerts.append(
                s.AlertOut(
                    kind=kind,
                    severity="critica" if expired else "advertencia",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_label=name,
                    message=msg,
                    due_date=expiry,
                    days_left=check.days_left,
                )
            )

        for v in VehicleRepository(self.session).all():
            if v.status == VehicleStatus.INACTIVO:
                continue
            doc_alert("soat", "SOAT", "vehicle", v.id, v.plate, v.soat_expiry)
            doc_alert("revision_tecnica", "Revisión técnica", "vehicle", v.id, v.plate, v.tech_review_expiry)
            m = maintenance_status(v.odometer_km, v.last_maintenance_km, v.maintenance_interval_km, self.settings.maintenance_warning_km)
            if m.status != MaintenanceStatus.AL_DIA:
                overdue = m.status == MaintenanceStatus.VENCIDO
                alerts.append(
                    s.AlertOut(
                        kind="mantenimiento",
                        severity="critica" if overdue else "advertencia",
                        entity_type="vehicle",
                        entity_id=v.id,
                        entity_label=v.plate,
                        message=(
                            f"Mantenimiento de {v.plate} vencido por {-m.km_remaining} km"
                            if overdue
                            else f"Mantenimiento de {v.plate} en {m.km_remaining} km"
                        ),
                        km_remaining=m.km_remaining,
                    )
                )
        for d in DriverRepository(self.session).all():
            if d.status != DriverStatus.INACTIVO:
                doc_alert("licencia", "Licencia", "driver", d.id, d.full_name, d.license_expiry)

        # Primero las críticas; dentro de cada grupo, lo más urgente arriba.
        return sorted(
            alerts, key=lambda a: (a.severity != "critica", a.days_left if a.days_left is not None else (a.km_remaining or 0) / 100)
        )


class DashboardService(Service):
    def build(self, day: date | None = None) -> s.Dashboard:
        day = day or self.today()
        orders = OrderRepository(self.session)
        today_counts = orders.count_by_status_on(day)

        last30 = orders.count_by_status_between(day - timedelta(days=29), day)
        closed = last30.get("entregado", 0) + last30.get("fallido", 0)
        success = round(100 * last30.get("entregado", 0) / closed, 1) if closed else None

        week_start = day - timedelta(days=6)
        per_day = orders.delivered_per_day(week_start, day)
        delivered_7 = [
            {"date": (week_start + timedelta(days=i)).isoformat(), "delivered": per_day.get(week_start + timedelta(days=i), 0)}
            for i in range(7)
        ]

        alerts = AlertService(self.session, self.settings, self.today).list()
        drivers_available = self.session.scalar(select(func.count()).select_from(Driver).where(Driver.status == DriverStatus.DISPONIBLE))
        month_start = day.replace(day=1)
        return s.Dashboard(
            date=day,
            orders_today=today_counts,
            orders_today_total=sum(today_counts.values()),
            success_rate_30d=success,
            delivered_last_7_days=delivered_7,
            vehicles_by_status=VehicleRepository(self.session).count_by_status(),
            drivers_available=drivers_available or 0,
            routes_in_progress=RouteRepository(self.session).count_active(),
            alerts_critical=sum(1 for a in alerts if a.severity == "critica"),
            alerts_warning=sum(1 for a in alerts if a.severity == "advertencia"),
            fuel_cost_month=FuelRepository(self.session).total_cost_between(month_start, day),
            map_orders=[
                s.MapOrder(id=o.id, code=o.code, customer_name=o.customer_name, latitude=o.latitude, longitude=o.longitude, status=o.status)
                for o in orders.for_map(day)
            ],
            depot_lat=self.settings.depot_lat,
            depot_lng=self.settings.depot_lng,
        )
