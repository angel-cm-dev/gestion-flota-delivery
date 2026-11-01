from app.api.routers.auth_users import auth_router, users_router
from app.api.routers.dispatch import orders_router, routes_router
from app.api.routers.fleet import drivers_router, vehicles_router
from app.api.routers.health import router as health_router
from app.api.routers.operations import alerts_router, dashboard_router, fuel_router, maintenance_router

ALL_ROUTERS = [
    health_router,
    auth_router,
    users_router,
    vehicles_router,
    drivers_router,
    orders_router,
    routes_router,
    maintenance_router,
    fuel_router,
    alerts_router,
    dashboard_router,
]
