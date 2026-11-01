"""Casos de uso de despacho: pedidos, rutas y entregas."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app.application import schemas as s
from app.application.mappers import order_out, route_out
from app.application.services.base import Service
from app.core.clock import utcnow
from app.domain.delivery import FINAL_STATES, ensure_capacity, ensure_transition, validate_delivery_proof
from app.domain.documents import is_valid_on
from app.domain.enums import DriverStatus, MaintenanceStatus, OrderStatus, Role, RouteStatus, VehicleStatus
from app.domain.errors import ConflictError, DomainError, ForbiddenError, NotFoundError
from app.domain.geo import Point, Stop, nearest_neighbor, route_length_km
from app.domain.licenses import can_drive
from app.domain.maintenance import maintenance_status
from app.infrastructure.models import Order, Route, User
from app.infrastructure.repositories import DriverRepository, OrderRepository, RouteRepository, VehicleRepository
from app.infrastructure.storage import FileStorage


def _sequence_orders(route: Route, orders: list[Order]) -> None:
    """Ordena las paradas con vecino más cercano y actualiza distancia y carga."""
    depot = Point(route.depot_lat, route.depot_lng)
    result = nearest_neighbor(depot, [Stop(o.id, Point(o.latitude, o.longitude)) for o in orders])
    by_id = {o.id: o for o in orders}
    for seq, order_id in enumerate(result.order, start=1):
        by_id[order_id].stop_sequence = seq
    route.total_distance_km = result.total_km
    route.total_weight_kg = round(sum(o.weight_kg for o in orders), 2)


class OrderService(Service):
    needs_storage = True

    def __init__(self, *args, storage: FileStorage | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.storage = storage

    @property
    def repo(self) -> OrderRepository:
        return OrderRepository(self.session)

    def _get(self, order_id: int) -> Order:
        o = self.repo.get(order_id)
        if not o:
            raise NotFoundError("Pedido no encontrado")
        return o

    def list(self, *, q, status, district, date_from, date_to, route_id, page, size, sort) -> s.Page[s.OrderOut]:
        stmt = self.repo.search(q=q, status=status, district=district, date_from=date_from, date_to=date_to, route_id=route_id)
        rows, total = self.repo.paginate(stmt, page=page, size=size, sort=sort)
        return s.Page.build([order_out(o) for o in rows], total, page, size)

    def get(self, order_id: int, *, user: User) -> s.OrderOut:
        o = self._get(order_id)
        if user.role == Role.CONDUCTOR:
            self._ensure_driver_owns(o, user)
        return order_out(o)

    def create(self, data: s.OrderCreate) -> s.OrderOut:
        if data.scheduled_date < self.today():
            raise DomainError("No se puede programar un pedido en una fecha pasada")
        code = self.repo.next_code(f"PED-{data.scheduled_date:%y%m%d}-")
        o = self.repo.add(Order(**data.model_dump(), code=code, status=OrderStatus.PENDIENTE))
        self.commit()
        return order_out(o)

    def update(self, order_id: int, data: s.OrderUpdate) -> s.OrderOut:
        o = self._get(order_id)
        # Un pedido ya asignado a una ruta cambiaría peso/ubicación de una ruta optimizada.
        if o.status != OrderStatus.PENDIENTE:
            raise ConflictError("Solo se pueden editar pedidos en estado 'pendiente'")
        if data.scheduled_date < self.today():
            raise DomainError("No se puede programar un pedido en una fecha pasada")
        for field, value in data.model_dump().items():
            setattr(o, field, value)
        self.commit()
        return order_out(o)

    def cancel(self, order_id: int) -> s.OrderOut:
        o = self._get(order_id)
        ensure_transition(o.status, OrderStatus.CANCELADO)
        route = o.route
        o.status, o.route_id, o.stop_sequence = OrderStatus.CANCELADO, None, None
        self.session.flush()
        if route is not None:
            # Si estaba en una ruta planificada, se reordenan las paradas restantes.
            self.session.refresh(route)
            remaining = [x for x in route.orders if x.id != o.id]
            if remaining:
                _sequence_orders(route, remaining)
            else:
                route.status, route.total_distance_km, route.total_weight_kg = RouteStatus.CANCELADA, 0, 0
        self.commit()
        return order_out(o)

    def reschedule(self, order_id: int, new_date: date) -> s.OrderOut:
        o = self._get(order_id)
        ensure_transition(o.status, OrderStatus.PENDIENTE)
        if o.status != OrderStatus.FALLIDO:
            raise ConflictError("Solo se reprograman pedidos con entrega fallida")
        if new_date < self.today():
            raise DomainError("La nueva fecha no puede ser pasada")
        o.status, o.scheduled_date, o.route_id, o.stop_sequence = OrderStatus.PENDIENTE, new_date, None, None
        self.commit()
        return order_out(o)

    # ------------------------------------------------------------ entregas

    def _ensure_driver_owns(self, o: Order, user: User) -> None:
        """Un conductor solo puede ver/actualizar pedidos de sus propias rutas."""
        driver = DriverRepository(self.session).by_user(user.id)
        if driver is None or o.route is None or o.route.driver_id != driver.id:
            raise ForbiddenError("Este pedido no pertenece a una de tus rutas")

    def _close_route_if_done(self, route: Route | None) -> None:
        """Al cerrar la última parada la ruta se completa y el conductor queda libre."""
        if route is None:
            return
        self.session.flush()
        self.session.refresh(route)
        if route.orders and all(o.status in FINAL_STATES for o in route.orders):
            route.status = RouteStatus.COMPLETADA
            route.completed_at = utcnow()
            route.driver.status = DriverStatus.DISPONIBLE

    def deliver(self, order_id: int, *, user: User, note: str | None, photo: bytes | None) -> s.OrderOut:
        o = self._get(order_id)
        if user.role == Role.CONDUCTOR:
            self._ensure_driver_owns(o, user)
        ensure_transition(o.status, OrderStatus.ENTREGADO)
        validate_delivery_proof(note, bool(photo))
        if photo:
            if self.storage is None:
                raise DomainError("Almacenamiento de archivos no configurado")
            o.proof_photo_path = self.storage.save_image(photo, prefix=o.code)
        o.proof_note = note.strip() if note else None
        o.status = OrderStatus.ENTREGADO
        o.delivered_at = utcnow()
        self._close_route_if_done(o.route)
        self.commit()
        return order_out(o)

    def fail(self, order_id: int, *, user: User, reason: str) -> s.OrderOut:
        o = self._get(order_id)
        if user.role == Role.CONDUCTOR:
            self._ensure_driver_owns(o, user)
        ensure_transition(o.status, OrderStatus.FALLIDO)
        o.status, o.failure_reason = OrderStatus.FALLIDO, reason.strip()
        self._close_route_if_done(o.route)
        self.commit()
        return order_out(o)

    def photo_path(self, order_id: int, *, user: User) -> Path:
        o = self._get(order_id)
        if user.role == Role.CONDUCTOR:
            self._ensure_driver_owns(o, user)
        if not o.proof_photo_path or self.storage is None:
            raise NotFoundError("El pedido no tiene foto de prueba")
        path = self.storage.resolve(o.proof_photo_path)
        if not path.exists():
            raise NotFoundError("La foto ya no está disponible")
        return path


class RouteService(Service):
    @property
    def repo(self) -> RouteRepository:
        return RouteRepository(self.session)

    def _get(self, route_id: int) -> Route:
        r = self.repo.get_full(route_id)
        if not r:
            raise NotFoundError("Ruta no encontrada")
        return r

    def list(self, *, status, route_date, driver_id, vehicle_id, page, size, sort) -> s.Page[s.RouteOut]:
        stmt = self.repo.search(status=status, route_date=route_date, driver_id=driver_id, vehicle_id=vehicle_id)
        rows, total = self.repo.paginate(stmt, page=page, size=size, sort=sort)
        return s.Page.build([route_out(r) for r in rows], total, page, size)

    def get(self, route_id: int, *, user: User) -> s.RouteDetail:
        r = self._get(route_id)
        if user.role == Role.CONDUCTOR:
            driver = DriverRepository(self.session).by_user(user.id)
            if not driver or r.driver_id != driver.id:
                raise ForbiddenError("Esta ruta no está asignada a ti")
        return route_out(r, detail=True)  # type: ignore[return-value]

    def mine(self, user: User, route_date: date | None) -> list[s.RouteDetail]:
        driver = DriverRepository(self.session).by_user(user.id)
        if not driver:
            raise NotFoundError("Tu usuario no está vinculado a un conductor")
        stmt = self.repo.search(status=None, route_date=route_date or self.today(), driver_id=driver.id, vehicle_id=None)
        rows = self.session.scalars(stmt.order_by(Route.id)).all()
        return [route_out(r, detail=True) for r in rows]  # type: ignore[misc]

    def preview(self, data: s.RoutePreviewRequest) -> s.RoutePreview:
        orders = OrderRepository(self.session).by_ids(data.order_ids)
        if len(orders) != len(set(data.order_ids)):
            raise NotFoundError("Uno o más pedidos no existen")
        depot = Point(data.depot_lat or self.settings.depot_lat, data.depot_lng or self.settings.depot_lng)
        by_id = {o.id: o for o in orders}
        result = nearest_neighbor(depot, [Stop(o.id, Point(o.latitude, o.longitude)) for o in orders])
        # Distancia visitando en el orden en que se seleccionaron: sirve para mostrar el ahorro.
        naive = route_length_km(depot, [Point(by_id[i].latitude, by_id[i].longitude) for i in data.order_ids])
        stops = [
            s.RoutePreviewStop(
                sequence=i + 1,
                order_id=oid,
                code=by_id[oid].code,
                latitude=by_id[oid].latitude,
                longitude=by_id[oid].longitude,
                leg_km=result.legs_km[i],
            )
            for i, oid in enumerate(result.order)
        ]
        savings = round(100 * (naive - result.total_km) / naive, 1) if naive > 0 else 0.0
        return s.RoutePreview(
            depot_lat=depot.lat,
            depot_lng=depot.lng,
            stops=stops,
            total_km=result.total_km,
            unoptimized_km=naive,
            savings_pct=max(savings, 0.0),
            total_weight_kg=round(sum(o.weight_kg for o in orders), 2),
        )

    def create(self, data: s.RouteCreate) -> s.RouteDetail:
        day = data.route_date
        if day < self.today():
            raise DomainError("No se pueden planificar rutas en fechas pasadas")

        vehicle = VehicleRepository(self.session).get(data.vehicle_id)
        if not vehicle:
            raise NotFoundError("Vehículo no encontrado")
        driver = DriverRepository(self.session).get(data.driver_id)
        if not driver:
            raise NotFoundError("Conductor no encontrado")

        # --- Reglas del vehículo: operativo, documentos vigentes el día de la ruta y mantenimiento al día.
        if vehicle.status != VehicleStatus.ACTIVO:
            raise DomainError(f"El vehículo {vehicle.plate} no está activo ({vehicle.status})", code="vehicle_unavailable")
        if not is_valid_on(vehicle.soat_expiry, day):
            raise DomainError(f"El SOAT del vehículo {vehicle.plate} estará vencido el {day}", code="soat_expired")
        if not is_valid_on(vehicle.tech_review_expiry, day):
            raise DomainError(f"La revisión técnica de {vehicle.plate} estará vencida el {day}", code="tech_review_expired")
        mcheck = maintenance_status(vehicle.odometer_km, vehicle.last_maintenance_km, vehicle.maintenance_interval_km)
        if mcheck.status == MaintenanceStatus.VENCIDO:
            raise DomainError(f"El vehículo {vehicle.plate} tiene el mantenimiento preventivo vencido", code="maintenance_overdue")

        # --- Reglas del conductor: activo, licencia vigente y de categoría adecuada.
        if driver.status == DriverStatus.INACTIVO:
            raise DomainError(f"El conductor {driver.full_name} está inactivo", code="driver_unavailable")
        if not is_valid_on(driver.license_expiry, day):
            raise DomainError(f"La licencia de {driver.full_name} estará vencida el {day}", code="license_expired")
        if not can_drive(driver.license_category, vehicle.vehicle_type):
            raise DomainError(
                f"La licencia {driver.license_category} no habilita a conducir un vehículo tipo {vehicle.vehicle_type}",
                code="license_category",
            )

        # --- Un vehículo y un conductor no pueden estar en dos rutas activas el mismo día.
        if self.repo.active_for(route_date=day, vehicle_id=vehicle.id):
            raise ConflictError(f"El vehículo {vehicle.plate} ya tiene una ruta activa el {day}", code="vehicle_busy")
        if self.repo.active_for(route_date=day, driver_id=driver.id):
            raise ConflictError(f"{driver.full_name} ya tiene una ruta activa el {day}", code="driver_busy")

        # --- Pedidos: existen, están pendientes y son de la misma fecha.
        orders = list(OrderRepository(self.session).by_ids(data.order_ids))
        if len(orders) != len(data.order_ids):
            raise NotFoundError("Uno o más pedidos no existen")
        for o in orders:
            if o.status != OrderStatus.PENDIENTE:
                raise ConflictError(f"El pedido {o.code} no está pendiente ({o.status})", code="order_not_pending")
            if o.scheduled_date != day:
                raise DomainError(f"El pedido {o.code} está programado para el {o.scheduled_date}, no para el {day}")
        ensure_capacity(vehicle.capacity_kg, [o.weight_kg for o in orders])

        route = self.repo.add(
            Route(
                code=self.repo.next_code(day),
                route_date=day,
                vehicle_id=vehicle.id,
                driver_id=driver.id,
                status=RouteStatus.PLANIFICADA,
                depot_lat=self.settings.depot_lat,
                depot_lng=self.settings.depot_lng,
            )
        )
        for o in orders:
            ensure_transition(o.status, OrderStatus.ASIGNADO)
            o.status, o.route_id = OrderStatus.ASIGNADO, route.id
        _sequence_orders(route, orders)
        self.commit()
        return route_out(self._get(route.id), detail=True)  # type: ignore[return-value]

    def start(self, route_id: int) -> s.RouteDetail:
        r = self._get(route_id)
        if r.status != RouteStatus.PLANIFICADA:
            raise ConflictError("Solo se pueden iniciar rutas planificadas")
        if r.route_date > self.today():
            raise DomainError(f"La ruta está programada para el {r.route_date}; no puede iniciarse antes")
        if r.driver.status == DriverStatus.EN_RUTA:
            raise ConflictError("El conductor ya está en otra ruta en curso")
        r.status, r.started_at = RouteStatus.EN_CURSO, utcnow()
        r.driver.status = DriverStatus.EN_RUTA
        for o in r.orders:
            ensure_transition(o.status, OrderStatus.EN_RUTA)
            o.status = OrderStatus.EN_RUTA
        self.commit()
        return route_out(r, detail=True)  # type: ignore[return-value]

    def cancel(self, route_id: int) -> s.RouteDetail:
        r = self._get(route_id)
        if r.status != RouteStatus.PLANIFICADA:
            raise ConflictError("Solo se pueden cancelar rutas que aún no han iniciado")
        # Los pedidos vuelven a la bolsa de pendientes para planificarse en otra ruta.
        for o in list(r.orders):
            ensure_transition(o.status, OrderStatus.PENDIENTE)
            o.status, o.route_id, o.stop_sequence = OrderStatus.PENDIENTE, None, None
        r.status = RouteStatus.CANCELADA
        self.commit()
        self.session.refresh(r)
        return route_out(r, detail=True)  # type: ignore[return-value]
