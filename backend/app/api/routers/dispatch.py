from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import AnyRole, Paging, Staff, require_roles, service
from app.application import schemas as s
from app.application.services import OrderService, RouteService
from app.domain.enums import Role
from app.infrastructure.models import User

orders_router = APIRouter(prefix="/api/orders", tags=["Pedidos"])
routes_router = APIRouter(prefix="/api/routes", tags=["Rutas"])

OrderSvc = Annotated[OrderService, Depends(service(OrderService))]
RouteSvc = Annotated[RouteService, Depends(service(RouteService))]
Conductor = Annotated[User, Depends(require_roles(Role.CONDUCTOR))]


@orders_router.get("", response_model=s.Page[s.OrderOut], summary="Listar pedidos")
def list_orders(
    _: Staff,
    paging: Paging,
    svc: OrderSvc,
    q: str | None = Query(None, max_length=100, description="Busca por código, cliente o dirección"),
    status_: str | None = Query(None, alias="status", description="Uno o varios estados separados por coma"),
    district: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    route_id: int | None = None,
):
    return svc.list(
        q=q,
        status=status_,
        district=district,
        date_from=date_from,
        date_to=date_to,
        route_id=route_id,
        page=paging.page,
        size=paging.size,
        sort=paging.sort,
    )


@orders_router.get("/{order_id}", response_model=s.OrderOut)
def get_order(order_id: int, user: AnyRole, svc: OrderSvc):
    return svc.get(order_id, user=user)


@orders_router.post("", response_model=s.OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(data: s.OrderCreate, _: Staff, svc: OrderSvc):
    return svc.create(data)


@orders_router.put("/{order_id}", response_model=s.OrderOut)
def update_order(order_id: int, data: s.OrderUpdate, _: Staff, svc: OrderSvc):
    return svc.update(order_id, data)


@orders_router.post("/{order_id}/cancel", response_model=s.OrderOut)
def cancel_order(order_id: int, _: Staff, svc: OrderSvc):
    return svc.cancel(order_id)


@orders_router.post("/{order_id}/reschedule", response_model=s.OrderOut, summary="Reprogramar un pedido fallido")
def reschedule_order(order_id: int, data: s.RescheduleRequest, _: Staff, svc: OrderSvc):
    return svc.reschedule(order_id, data.scheduled_date)


@orders_router.post(
    "/{order_id}/deliver",
    response_model=s.OrderOut,
    summary="Marcar como entregado con prueba (foto y/o nota)",
    description="multipart/form-data. Se requiere al menos una foto (JPG/PNG/WEBP) o una nota.",
)
async def deliver_order(
    order_id: int,
    user: AnyRole,
    svc: OrderSvc,
    note: Annotated[str | None, Form(max_length=500)] = None,
    photo: Annotated[UploadFile | None, File()] = None,
):
    data = await photo.read() if photo is not None and photo.filename else None
    return svc.deliver(order_id, user=user, note=note, photo=data)


@orders_router.post("/{order_id}/fail", response_model=s.OrderOut, summary="Marcar entrega fallida con motivo")
def fail_order(order_id: int, data: s.FailRequest, user: AnyRole, svc: OrderSvc):
    return svc.fail(order_id, user=user, reason=data.reason)


@orders_router.get("/{order_id}/photo", response_class=FileResponse, summary="Foto de prueba de entrega")
def order_photo(order_id: int, user: AnyRole, svc: OrderSvc):
    return FileResponse(svc.photo_path(order_id, user=user))


@routes_router.get("", response_model=s.Page[s.RouteOut], summary="Listar rutas")
def list_routes(
    _: Staff,
    paging: Paging,
    svc: RouteSvc,
    status_: str | None = Query(None, alias="status"),
    route_date: date | None = None,
    driver_id: int | None = None,
    vehicle_id: int | None = None,
):
    return svc.list(
        status=status_,
        route_date=route_date,
        driver_id=driver_id,
        vehicle_id=vehicle_id,
        page=paging.page,
        size=paging.size,
        sort=paging.sort,
    )


@routes_router.get("/mine", response_model=list[s.RouteDetail], summary="Rutas del conductor autenticado")
def my_routes(user: Conductor, svc: RouteSvc, route_date: date | None = None):
    return svc.mine(user, route_date)


@routes_router.post("/preview", response_model=s.RoutePreview, summary="Previsualizar el orden optimizado de paradas")
def preview_route(data: s.RoutePreviewRequest, _: Staff, svc: RouteSvc):
    return svc.preview(data)


@routes_router.get("/{route_id}", response_model=s.RouteDetail)
def get_route(route_id: int, user: AnyRole, svc: RouteSvc):
    return svc.get(route_id, user=user)


@routes_router.post(
    "",
    response_model=s.RouteDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Crear ruta: valida capacidad, documentos y licencia, y optimiza el orden",
)
def create_route(data: s.RouteCreate, _: Staff, svc: RouteSvc):
    return svc.create(data)


@routes_router.post("/{route_id}/start", response_model=s.RouteDetail)
def start_route(route_id: int, _: Staff, svc: RouteSvc):
    return svc.start(route_id)


@routes_router.post("/{route_id}/cancel", response_model=s.RouteDetail)
def cancel_route(route_id: int, _: Staff, svc: RouteSvc):
    return svc.cancel(route_id)
