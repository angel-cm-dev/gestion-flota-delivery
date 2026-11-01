from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import AnyRole, Paging, Staff, service
from app.application import schemas as s
from app.application.services import AlertService, DashboardService, FuelService, MaintenanceService
from app.domain.enums import MaintenanceKind

maintenance_router = APIRouter(prefix="/api/maintenance", tags=["Mantenimiento"])
fuel_router = APIRouter(prefix="/api/fuel", tags=["Combustible"])
alerts_router = APIRouter(prefix="/api/alerts", tags=["Alertas"])
dashboard_router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

MaintSvc = Annotated[MaintenanceService, Depends(service(MaintenanceService))]
FuelSvc = Annotated[FuelService, Depends(service(FuelService))]


@maintenance_router.get("", response_model=s.Page[s.MaintenanceOut])
def list_maintenance(_: Staff, paging: Paging, svc: MaintSvc, vehicle_id: int | None = None, kind: MaintenanceKind | None = None):
    return svc.list(vehicle_id=vehicle_id, kind=kind, page=paging.page, size=paging.size, sort=paging.sort)


@maintenance_router.get("/overview", response_model=list[s.MaintenanceOverview], summary="Estado de mantenimiento de la flota")
def maintenance_overview(_: Staff, svc: MaintSvc):
    return svc.overview()


@maintenance_router.post("", response_model=s.MaintenanceOut, status_code=status.HTTP_201_CREATED)
def create_maintenance(data: s.MaintenanceCreate, _: Staff, svc: MaintSvc):
    return svc.create(data)


@fuel_router.get("", response_model=s.Page[s.FuelOut])
def list_fuel(
    _: Staff,
    paging: Paging,
    svc: FuelSvc,
    vehicle_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    return svc.list(vehicle_id=vehicle_id, date_from=date_from, date_to=date_to, page=paging.page, size=paging.size, sort=paging.sort)


@fuel_router.post("", response_model=s.FuelOut, status_code=status.HTTP_201_CREATED, summary="Registrar carga de combustible")
def create_fuel(data: s.FuelCreate, user: AnyRole, svc: FuelSvc):
    return svc.create(data, user=user)


@fuel_router.get("/efficiency/{vehicle_id}", response_model=s.FuelEfficiency, summary="Rendimiento km/l por vehículo")
def fuel_efficiency(vehicle_id: int, _: Staff, svc: FuelSvc):
    return svc.efficiency(vehicle_id)


@alerts_router.get("", response_model=list[s.AlertOut], summary="Alertas de vencimientos y mantenimiento")
def list_alerts(_: Staff, svc: Annotated[AlertService, Depends(service(AlertService))]):
    return svc.list()


@dashboard_router.get("", response_model=s.Dashboard, summary="KPIs del día")
def dashboard(
    _: Staff,
    svc: Annotated[DashboardService, Depends(service(DashboardService))],
    day: date | None = Query(None, alias="date"),
):
    return svc.build(day)
