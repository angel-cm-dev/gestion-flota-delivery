"""Repositorios: único lugar donde se escriben consultas SQL (SQLAlchemy).

Los servicios de aplicación dependen de estos repositorios, no de la sesión
directamente para consultar. Así las reglas de negocio no se mezclan con
detalles de SQL y las consultas reutilizables (p. ej. "rutas activas de un
conductor en una fecha") tienen un nombre propio.
"""

from collections.abc import Sequence
from datetime import date
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import RouteStatus
from app.infrastructure.models import Driver, FuelLog, MaintenanceRecord, Order, Route, User, Vehicle

T = TypeVar("T")

ACTIVE_ROUTE_STATES = (RouteStatus.PLANIFICADA.value, RouteStatus.EN_CURSO.value)


class BaseRepository(Generic[T]):
    model: type[T]
    # Lista blanca de columnas ordenables: nunca se interpola texto del usuario en SQL.
    sortable: dict[str, Any] = {}
    default_sort: str = "-id"

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int) -> T | None:
        return self.session.get(self.model, entity_id)

    def add(self, entity: T) -> T:
        self.session.add(entity)
        self.session.flush()
        return entity

    def delete(self, entity: T) -> None:
        self.session.delete(entity)
        self.session.flush()

    def _apply_sort(self, stmt: Select, sort: str | None) -> Select:
        key = sort or self.default_sort
        desc = key.startswith("-")
        column = self.sortable.get(key.lstrip("-")) or self.model.id  # type: ignore[attr-defined]
        return stmt.order_by(column.desc() if desc else column.asc(), self.model.id.desc() if desc else self.model.id.asc())  # type: ignore[attr-defined]

    def paginate(self, stmt: Select, *, page: int, size: int, sort: str | None) -> tuple[Sequence[T], int]:
        total = self.session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
        rows = self.session.scalars(self._apply_sort(stmt, sort).offset((page - 1) * size).limit(size)).all()
        return rows, total


class UserRepository(BaseRepository[User]):
    model = User
    sortable = {"email": User.email, "full_name": User.full_name, "role": User.role, "created_at": User.created_at}

    def by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(func.lower(User.email) == email.lower()))

    def search(self, *, q: str | None, role: str | None) -> Select:
        stmt = select(User)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(or_(func.lower(User.email).like(like), func.lower(User.full_name).like(like)))
        if role:
            stmt = stmt.where(User.role == role)
        return stmt


class VehicleRepository(BaseRepository[Vehicle]):
    model = Vehicle
    sortable = {
        "plate": Vehicle.plate,
        "brand": Vehicle.brand,
        "capacity_kg": Vehicle.capacity_kg,
        "odometer_km": Vehicle.odometer_km,
        "soat_expiry": Vehicle.soat_expiry,
        "tech_review_expiry": Vehicle.tech_review_expiry,
        "created_at": Vehicle.created_at,
    }
    default_sort = "plate"

    def by_plate(self, plate: str) -> Vehicle | None:
        return self.session.scalar(select(Vehicle).where(Vehicle.plate == plate))

    def search(self, *, q: str | None, status: str | None, vehicle_type: str | None) -> Select:
        stmt = select(Vehicle)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(
                or_(func.lower(Vehicle.plate).like(like), func.lower(Vehicle.brand).like(like), func.lower(Vehicle.model).like(like))
            )
        if status:
            stmt = stmt.where(Vehicle.status == status)
        if vehicle_type:
            stmt = stmt.where(Vehicle.vehicle_type == vehicle_type)
        return stmt

    def all(self) -> Sequence[Vehicle]:
        return self.session.scalars(select(Vehicle).order_by(Vehicle.plate)).all()

    def count_by_status(self) -> dict[str, int]:
        rows = self.session.execute(select(Vehicle.status, func.count()).group_by(Vehicle.status)).all()
        return {status: count for status, count in rows}


class DriverRepository(BaseRepository[Driver]):
    model = Driver
    sortable = {
        "full_name": Driver.full_name,
        "license_expiry": Driver.license_expiry,
        "status": Driver.status,
        "created_at": Driver.created_at,
    }
    default_sort = "full_name"

    def by_user(self, user_id: int) -> Driver | None:
        return self.session.scalar(select(Driver).where(Driver.user_id == user_id))

    def by_field(self, field: str, value: str) -> Driver | None:
        return self.session.scalar(select(Driver).where(getattr(Driver, field) == value))

    def search(self, *, q: str | None, status: str | None) -> Select:
        stmt = select(Driver)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(
                or_(func.lower(Driver.full_name).like(like), Driver.dni.like(like), func.lower(Driver.license_number).like(like))
            )
        if status:
            stmt = stmt.where(Driver.status == status)
        return stmt

    def all(self) -> Sequence[Driver]:
        return self.session.scalars(select(Driver).order_by(Driver.full_name)).all()


class OrderRepository(BaseRepository[Order]):
    model = Order
    sortable = {
        "code": Order.code,
        "scheduled_date": Order.scheduled_date,
        "weight_kg": Order.weight_kg,
        "district": Order.district,
        "status": Order.status,
        "created_at": Order.created_at,
    }

    def by_ids(self, ids: list[int]) -> Sequence[Order]:
        return self.session.scalars(select(Order).where(Order.id.in_(ids))).all()

    def search(
        self,
        *,
        q: str | None,
        status: str | None,
        district: str | None,
        date_from: date | None,
        date_to: date | None,
        route_id: int | None,
    ) -> Select:
        stmt = select(Order)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Order.code).like(like),
                    func.lower(Order.customer_name).like(like),
                    func.lower(Order.address).like(like),
                )
            )
        if status:
            stmt = stmt.where(Order.status.in_(status.split(",")))
        if district:
            stmt = stmt.where(Order.district == district)
        if date_from:
            stmt = stmt.where(Order.scheduled_date >= date_from)
        if date_to:
            stmt = stmt.where(Order.scheduled_date <= date_to)
        if route_id:
            stmt = stmt.where(Order.route_id == route_id)
        return stmt

    def next_code(self, prefix: str) -> str:
        count = self.session.scalar(select(func.count()).select_from(Order).where(Order.code.like(f"{prefix}%"))) or 0
        return f"{prefix}{count + 1:04d}"

    def count_by_status_on(self, day: date) -> dict[str, int]:
        rows = self.session.execute(select(Order.status, func.count()).where(Order.scheduled_date == day).group_by(Order.status)).all()
        return {status: count for status, count in rows}

    def count_by_status_between(self, start: date, end: date) -> dict[str, int]:
        rows = self.session.execute(
            select(Order.status, func.count()).where(Order.scheduled_date.between(start, end)).group_by(Order.status)
        ).all()
        return {status: count for status, count in rows}

    def delivered_per_day(self, start: date, end: date) -> dict[date, int]:
        rows = self.session.execute(
            select(Order.scheduled_date, func.count())
            .where(Order.scheduled_date.between(start, end), Order.status == "entregado")
            .group_by(Order.scheduled_date)
        ).all()
        return {d: c for d, c in rows}

    def for_map(self, day: date) -> Sequence[Order]:
        return self.session.scalars(select(Order).where(Order.scheduled_date == day).order_by(Order.id)).all()


class RouteRepository(BaseRepository[Route]):
    model = Route
    sortable = {
        "code": Route.code,
        "route_date": Route.route_date,
        "status": Route.status,
        "total_distance_km": Route.total_distance_km,
        "created_at": Route.created_at,
    }
    default_sort = "-route_date"

    def get_full(self, route_id: int) -> Route | None:
        return self.session.scalar(
            select(Route)
            .where(Route.id == route_id)
            .options(selectinload(Route.orders), selectinload(Route.vehicle), selectinload(Route.driver))
        )

    def search(self, *, status: str | None, route_date: date | None, driver_id: int | None, vehicle_id: int | None) -> Select:
        stmt = select(Route).options(selectinload(Route.vehicle), selectinload(Route.driver), selectinload(Route.orders))
        if status:
            stmt = stmt.where(Route.status.in_(status.split(",")))
        if route_date:
            stmt = stmt.where(Route.route_date == route_date)
        if driver_id:
            stmt = stmt.where(Route.driver_id == driver_id)
        if vehicle_id:
            stmt = stmt.where(Route.vehicle_id == vehicle_id)
        return stmt

    def active_for(self, *, route_date: date, vehicle_id: int | None = None, driver_id: int | None = None) -> Route | None:
        stmt = select(Route).where(Route.route_date == route_date, Route.status.in_(ACTIVE_ROUTE_STATES))
        if vehicle_id is not None:
            stmt = stmt.where(Route.vehicle_id == vehicle_id)
        if driver_id is not None:
            stmt = stmt.where(Route.driver_id == driver_id)
        return self.session.scalars(stmt.limit(1)).first()

    def next_code(self, day: date) -> str:
        prefix = f"R{day:%Y%m%d}-"
        count = self.session.scalar(select(func.count()).select_from(Route).where(Route.code.like(f"{prefix}%"))) or 0
        return f"{prefix}{count + 1:02d}"

    def count_active(self) -> int:
        return self.session.scalar(select(func.count()).select_from(Route).where(Route.status == RouteStatus.EN_CURSO.value)) or 0


class MaintenanceRepository(BaseRepository[MaintenanceRecord]):
    model = MaintenanceRecord
    sortable = {
        "service_date": MaintenanceRecord.service_date,
        "cost": MaintenanceRecord.cost,
        "odometer_km": MaintenanceRecord.odometer_km,
    }
    default_sort = "-service_date"

    def search(self, *, vehicle_id: int | None, kind: str | None) -> Select:
        stmt = select(MaintenanceRecord).options(selectinload(MaintenanceRecord.vehicle))
        if vehicle_id:
            stmt = stmt.where(MaintenanceRecord.vehicle_id == vehicle_id)
        if kind:
            stmt = stmt.where(MaintenanceRecord.kind == kind)
        return stmt


class FuelRepository(BaseRepository[FuelLog]):
    model = FuelLog
    sortable = {"fill_date": FuelLog.fill_date, "total_cost": FuelLog.total_cost, "odometer_km": FuelLog.odometer_km}
    default_sort = "-fill_date"

    def search(self, *, vehicle_id: int | None, date_from: date | None, date_to: date | None) -> Select:
        stmt = select(FuelLog).options(selectinload(FuelLog.vehicle))
        if vehicle_id:
            stmt = stmt.where(FuelLog.vehicle_id == vehicle_id)
        if date_from:
            stmt = stmt.where(FuelLog.fill_date >= date_from)
        if date_to:
            stmt = stmt.where(FuelLog.fill_date <= date_to)
        return stmt

    def last_for_vehicle(self, vehicle_id: int) -> FuelLog | None:
        return self.session.scalars(
            select(FuelLog).where(FuelLog.vehicle_id == vehicle_id).order_by(FuelLog.odometer_km.desc()).limit(1)
        ).first()

    def history(self, vehicle_id: int) -> Sequence[FuelLog]:
        return self.session.scalars(select(FuelLog).where(FuelLog.vehicle_id == vehicle_id).order_by(FuelLog.odometer_km.asc())).all()

    def total_cost_between(self, start: date, end: date) -> float:
        return float(
            self.session.scalar(select(func.coalesce(func.sum(FuelLog.total_cost), 0)).where(FuelLog.fill_date.between(start, end))) or 0
        )
