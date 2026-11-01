from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import AdminOnly, AnyRole, Paging, Staff, service
from app.application import schemas as s
from app.application.services import DriverService, VehicleService
from app.domain.enums import DriverStatus, VehicleStatus, VehicleType

vehicles_router = APIRouter(prefix="/api/vehicles", tags=["Vehículos"])
drivers_router = APIRouter(prefix="/api/drivers", tags=["Conductores"])

VehicleSvc = Annotated[VehicleService, Depends(service(VehicleService))]
DriverSvc = Annotated[DriverService, Depends(service(DriverService))]


@vehicles_router.get("", response_model=s.Page[s.VehicleOut], summary="Listar vehículos (filtros, orden y paginación)")
def list_vehicles(
    _: AnyRole,
    paging: Paging,
    svc: VehicleSvc,
    q: str | None = Query(None, max_length=60, description="Busca por placa, marca o modelo"),
    status_: VehicleStatus | None = Query(None, alias="status"),
    vehicle_type: VehicleType | None = None,
):
    return svc.list(q=q, status=status_, vehicle_type=vehicle_type, page=paging.page, size=paging.size, sort=paging.sort)


@vehicles_router.get("/{vehicle_id}", response_model=s.VehicleOut)
def get_vehicle(vehicle_id: int, _: AnyRole, svc: VehicleSvc):
    return svc.get(vehicle_id)


@vehicles_router.post("", response_model=s.VehicleOut, status_code=status.HTTP_201_CREATED)
def create_vehicle(data: s.VehicleCreate, _: Staff, svc: VehicleSvc):
    return svc.create(data)


@vehicles_router.put("/{vehicle_id}", response_model=s.VehicleOut)
def update_vehicle(vehicle_id: int, data: s.VehicleUpdate, _: Staff, svc: VehicleSvc):
    return svc.update(vehicle_id, data)


@vehicles_router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar vehículo (solo admin)")
def delete_vehicle(vehicle_id: int, _: AdminOnly, svc: VehicleSvc):
    svc.delete(vehicle_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@drivers_router.get("", response_model=s.Page[s.DriverOut])
def list_drivers(
    _: Staff,
    paging: Paging,
    svc: DriverSvc,
    q: str | None = Query(None, max_length=60, description="Busca por nombre, DNI o licencia"),
    status_: DriverStatus | None = Query(None, alias="status"),
):
    return svc.list(q=q, status=status_, page=paging.page, size=paging.size, sort=paging.sort)


@drivers_router.get("/{driver_id}", response_model=s.DriverOut)
def get_driver(driver_id: int, _: Staff, svc: DriverSvc):
    return svc.get(driver_id)


@drivers_router.post("", response_model=s.DriverOut, status_code=status.HTTP_201_CREATED)
def create_driver(data: s.DriverCreate, _: Staff, svc: DriverSvc):
    return svc.create(data)


@drivers_router.put("/{driver_id}", response_model=s.DriverOut)
def update_driver(driver_id: int, data: s.DriverUpdate, _: Staff, svc: DriverSvc):
    return svc.update(driver_id, data)


@drivers_router.delete("/{driver_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar conductor (solo admin)")
def delete_driver(driver_id: int, _: AdminOnly, svc: DriverSvc):
    svc.delete(driver_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
