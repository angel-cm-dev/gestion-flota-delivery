"""Casos de uso de vehículos y conductores."""

from __future__ import annotations

from sqlalchemy import exists, select

from app.application import schemas as s
from app.application.mappers import driver_out, vehicle_out
from app.application.services.base import Service
from app.domain.enums import DriverStatus, Role, VehicleStatus
from app.domain.errors import ConflictError, DomainError, NotFoundError
from app.infrastructure.models import Driver, Route, Vehicle
from app.infrastructure.repositories import DriverRepository, UserRepository, VehicleRepository


class VehicleService(Service):
    @property
    def repo(self) -> VehicleRepository:
        return VehicleRepository(self.session)

    def _get(self, vehicle_id: int) -> Vehicle:
        v = self.repo.get(vehicle_id)
        if not v:
            raise NotFoundError("Vehículo no encontrado")
        return v

    def _ensure_plate_free(self, plate: str, current_id: int | None = None) -> None:
        other = self.repo.by_plate(plate)
        if other and other.id != current_id:
            raise ConflictError(f"La placa {plate} ya está registrada", code="plate_taken")

    def list(self, *, q, status, vehicle_type, page, size, sort) -> s.Page[s.VehicleOut]:
        rows, total = self.repo.paginate(self.repo.search(q=q, status=status, vehicle_type=vehicle_type), page=page, size=size, sort=sort)
        today = self.today()
        return s.Page.build([vehicle_out(v, today, self.settings) for v in rows], total, page, size)

    def get(self, vehicle_id: int) -> s.VehicleOut:
        return vehicle_out(self._get(vehicle_id), self.today(), self.settings)

    def create(self, data: s.VehicleCreate) -> s.VehicleOut:
        self._ensure_plate_free(data.plate)
        if data.last_maintenance_km > data.odometer_km:
            raise DomainError("El último mantenimiento no puede superar el odómetro actual")
        v = self.repo.add(Vehicle(**data.model_dump(), status=VehicleStatus.ACTIVO))
        self.commit()
        return vehicle_out(v, self.today(), self.settings)

    def update(self, vehicle_id: int, data: s.VehicleUpdate) -> s.VehicleOut:
        v = self._get(vehicle_id)
        self._ensure_plate_free(data.plate, v.id)
        # El odómetro nunca retrocede: protege los cálculos de mantenimiento y rendimiento.
        if data.odometer_km < v.odometer_km:
            raise DomainError(f"El odómetro no puede disminuir (actual: {v.odometer_km} km)", code="odometer_decrease")
        if data.last_maintenance_km > data.odometer_km:
            raise DomainError("El último mantenimiento no puede superar el odómetro actual")
        for field, value in data.model_dump().items():
            setattr(v, field, value)
        self.commit()
        return vehicle_out(v, self.today(), self.settings)

    def delete(self, vehicle_id: int) -> None:
        v = self._get(vehicle_id)
        if self.session.scalar(select(exists().where(Route.vehicle_id == v.id))):
            raise ConflictError("El vehículo tiene rutas registradas; márcalo como 'inactivo' en lugar de eliminarlo")
        self.repo.delete(v)
        self.commit()


class DriverService(Service):
    @property
    def repo(self) -> DriverRepository:
        return DriverRepository(self.session)

    def _get(self, driver_id: int) -> Driver:
        d = self.repo.get(driver_id)
        if not d:
            raise NotFoundError("Conductor no encontrado")
        return d

    def _validate_unique_and_user(self, data: s.DriverBase, current_id: int | None = None) -> None:
        for field, label in (("dni", "DNI"), ("license_number", "número de licencia")):
            other = self.repo.by_field(field, getattr(data, field))
            if other and other.id != current_id:
                raise ConflictError(f"Ya existe un conductor con ese {label}")
        # La licencia peruana es la letra + el DNI del titular: si no coinciden, hay un error de digitación.
        if data.license_number[1:] != data.dni:
            raise DomainError("El número de licencia debe corresponder al DNI del conductor", code="license_dni_mismatch")
        if data.user_id is not None:
            user = UserRepository(self.session).get(data.user_id)
            if not user or user.role != Role.CONDUCTOR:
                raise DomainError("La cuenta vinculada debe existir y tener rol 'conductor'")
            linked = self.repo.by_user(data.user_id)
            if linked and linked.id != current_id:
                raise ConflictError("Esa cuenta ya está vinculada a otro conductor")

    def list(self, *, q, status, page, size, sort) -> s.Page[s.DriverOut]:
        rows, total = self.repo.paginate(self.repo.search(q=q, status=status), page=page, size=size, sort=sort)
        today = self.today()
        return s.Page.build([driver_out(d, today, self.settings) for d in rows], total, page, size)

    def get(self, driver_id: int) -> s.DriverOut:
        return driver_out(self._get(driver_id), self.today(), self.settings)

    def create(self, data: s.DriverCreate) -> s.DriverOut:
        self._validate_unique_and_user(data)
        d = self.repo.add(Driver(**data.model_dump(), status=DriverStatus.DISPONIBLE))
        self.commit()
        return driver_out(d, self.today(), self.settings)

    def update(self, driver_id: int, data: s.DriverUpdate) -> s.DriverOut:
        d = self._get(driver_id)
        self._validate_unique_and_user(data, d.id)
        if d.status == DriverStatus.EN_RUTA and data.status != DriverStatus.EN_RUTA:
            raise DomainError("El conductor tiene una ruta en curso; finalízala antes de cambiar su estado")
        for field, value in data.model_dump().items():
            setattr(d, field, value)
        self.commit()
        return driver_out(d, self.today(), self.settings)

    def delete(self, driver_id: int) -> None:
        d = self._get(driver_id)
        if self.session.scalar(select(exists().where(Route.driver_id == d.id))):
            raise ConflictError("El conductor tiene rutas registradas; márcalo como 'inactivo' en lugar de eliminarlo")
        self.repo.delete(d)
        self.commit()
