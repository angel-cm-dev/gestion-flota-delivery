"""Datos de ejemplo FICTICIOS para la demo.

Uso:  python -m app.seed            (idempotente: si ya existe admin@demo.pe no hace nada)
      python -m app.seed --reset    (borra todo y vuelve a sembrar; solo desarrollo)

Las fechas se calculan relativas a "hoy" para que la demo siempre muestre
alertas por vencer, rutas del día e historial de la última semana. Nombres,
DNI, teléfonos y placas son inventados.
"""

import argparse
import random
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import LIMA_TZ, today_lima
from app.core.config import get_settings
from app.core.security import hash_password
from app.domain.geo import Point, Stop, nearest_neighbor
from app.infrastructure.database import Base, build_engine, build_session_factory
from app.infrastructure.models import Driver, FuelLog, MaintenanceRecord, Order, Route, User, Vehicle

DEMO_PASSWORD = "Demo123!"

# (distrito, lat, lng) aproximados de Lima Metropolitana.
DISTRICTS = [
    ("Miraflores", -12.1211, -77.0297),
    ("San Isidro", -12.0977, -77.0365),
    ("Santiago de Surco", -12.1450, -76.9920),
    ("San Borja", -12.1009, -76.9990),
    ("La Molina", -12.0790, -76.9420),
    ("Jesús María", -12.0750, -77.0490),
    ("Lince", -12.0840, -77.0360),
    ("Pueblo Libre", -12.0740, -77.0630),
    ("Magdalena del Mar", -12.0900, -77.0710),
    ("San Miguel", -12.0770, -77.0910),
    ("Barranco", -12.1490, -77.0210),
    ("Chorrillos", -12.1700, -77.0150),
    ("Los Olivos", -11.9690, -77.0710),
    ("San Martín de Porres", -12.0090, -77.0600),
    ("Breña", -12.0590, -77.0500),
    ("Surquillo", -12.1130, -77.0200),
]
STREETS = [
    "Av. Arequipa",
    "Av. Javier Prado",
    "Jr. Huiracocha",
    "Calle Los Pinos",
    "Av. Brasil",
    "Av. La Marina",
    "Calle Las Begonias",
    "Av. Benavides",
    "Jr. Cuzco",
    "Av. Primavera",
    "Calle Schell",
    "Av. Salaverry",
]
FIRST = ["Lucía", "Carlos", "María", "Jorge", "Rosa", "Diego", "Ana", "Luis", "Sofía", "Miguel", "Valeria", "Raúl", "Elena", "Pedro"]
LAST = ["Quispe", "Huamán", "Flores", "Rojas", "Mendoza", "Torres", "Vargas", "Castillo", "Ramos", "Chávez", "Salazar", "Paredes"]


def _dt(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour, 0), tzinfo=LIMA_TZ)


def seed(session: Session, today: date | None = None, rng_seed: int = 7) -> bool:
    if session.scalar(select(User).where(User.email == "admin@demo.pe")):
        return False
    today = today or today_lima()
    rng = random.Random(rng_seed)
    settings = get_settings()
    pwd = hash_password(DEMO_PASSWORD)

    users = {
        key: User(email=email, full_name=name, password_hash=pwd, role=role)
        for key, email, name, role in [
            ("admin", "admin@demo.pe", "Administrador Demo", "admin"),
            ("despacho", "despacho@demo.pe", "Patricia Despacho", "despachador"),
            ("conductor", "conductor@demo.pe", "Juan Pérez Quispe", "conductor"),
            ("conductor2", "conductor2@demo.pe", "Rosa Huamán Torres", "conductor"),
        ]
    }
    session.add_all(users.values())
    session.flush()

    d = lambda days: today + timedelta(days=days)  # noqa: E731
    vehicles = [
        Vehicle(
            plate="BXK-482",
            brand="Toyota",
            model="Hiace",
            year=2021,
            vehicle_type="furgoneta",
            fuel_type="diesel",
            capacity_kg=1200,
            odometer_km=48_200,
            soat_expiry=d(160),
            tech_review_expiry=d(210),
            maintenance_interval_km=5000,
            last_maintenance_km=45_000,
        ),
        Vehicle(
            plate="C4F-512",
            brand="Hyundai",
            model="H-1",
            year=2020,
            vehicle_type="furgoneta",
            fuel_type="gasolina",
            capacity_kg=900,
            odometer_km=61_750,
            soat_expiry=d(12),
            tech_review_expiry=d(95),  # SOAT por vencer
            maintenance_interval_km=5000,
            last_maintenance_km=57_000,
        ),  # mantenimiento próximo (250 km)
        Vehicle(
            plate="D7M-903",
            brand="Isuzu",
            model="NPR 816",
            year=2019,
            vehicle_type="camion",
            fuel_type="diesel",
            capacity_kg=4500,
            odometer_km=132_400,
            soat_expiry=d(70),
            tech_review_expiry=d(-4),  # RT vencida
            maintenance_interval_km=10000,
            last_maintenance_km=125_000,
        ),
        Vehicle(
            plate="ARQ-275",
            brand="Suzuki",
            model="Carry",
            year=2022,
            vehicle_type="furgoneta",
            fuel_type="gnv",
            capacity_kg=650,
            odometer_km=22_100,
            soat_expiry=d(240),
            tech_review_expiry=d(300),
            maintenance_interval_km=5000,
            last_maintenance_km=20_000,
        ),
        Vehicle(
            plate="4521-LM",
            brand="Honda",
            model="CB190R",
            year=2023,
            vehicle_type="moto",
            fuel_type="gasolina",
            capacity_kg=40,
            odometer_km=15_900,
            soat_expiry=d(25),
            tech_review_expiry=d(400),
            maintenance_interval_km=3000,
            last_maintenance_km=12_000,
        ),  # mantenimiento vencido
        Vehicle(
            plate="F2A-118",
            brand="Nissan",
            model="NV350",
            year=2018,
            vehicle_type="furgoneta",
            fuel_type="diesel",
            capacity_kg=1100,
            odometer_km=210_000,
            soat_expiry=d(-30),
            tech_review_expiry=d(-10),
            maintenance_interval_km=5000,
            last_maintenance_km=205_000,
            status="inactivo",
        ),
    ]
    session.add_all(vehicles)

    drivers = [
        Driver(
            user_id=users["conductor"].id,
            full_name="Juan Pérez Quispe",
            dni="45781236",
            phone="987654321",
            license_number="Q45781236",
            license_category="A-IIb",
            license_expiry=d(400),
        ),
        Driver(
            user_id=users["conductor2"].id,
            full_name="Rosa Huamán Torres",
            dni="41236578",
            phone="976543210",
            license_number="H41236578",
            license_category="A-IIa",
            license_expiry=d(20),
        ),  # licencia por vencer
        Driver(
            full_name="Carlos Mendoza Ríos",
            dni="46325874",
            phone="965432109",
            license_number="M46325874",
            license_category="A-IIIc",
            license_expiry=d(800),
        ),
        Driver(
            full_name="Luis Vargas Salazar",
            dni="47896541",
            phone="954321098",
            license_number="V47896541",
            license_category="B-IIc",
            license_expiry=d(500),
        ),
        Driver(
            full_name="Elena Castillo Paredes",
            dni="42587413",
            phone="943210987",
            license_number="C42587413",
            license_category="A-I",
            license_expiry=d(-15),
            status="inactivo",
        ),
    ]
    session.add_all(drivers)
    session.flush()

    counter: dict[date, int] = {}

    def make_order(day: date, status: str = "pendiente") -> Order:
        district, lat, lng = rng.choice(DISTRICTS)
        counter[day] = counter.get(day, 0) + 1
        return Order(
            code=f"PED-{day:%y%m%d}-{counter[day]:04d}",
            customer_name=f"{rng.choice(FIRST)} {rng.choice(LAST)} {rng.choice(LAST)}",
            customer_phone=f"9{rng.randint(10_000_000, 99_999_999)}",
            address=f"{rng.choice(STREETS)} {rng.randint(100, 3999)}",
            district=district,
            latitude=round(lat + rng.uniform(-0.008, 0.008), 6),
            longitude=round(lng + rng.uniform(-0.008, 0.008), 6),
            weight_kg=round(rng.uniform(2, 60), 1),
            scheduled_date=day,
            status=status,
            created_at=_dt(day - timedelta(days=1), 15),
        )

    def make_route(day: date, vehicle: Vehicle, driver: Driver, orders: list[Order], status: str, seq: int) -> Route:
        route = Route(
            code=f"R{day:%Y%m%d}-{seq:02d}",
            route_date=day,
            vehicle_id=vehicle.id,
            driver_id=driver.id,
            status=status,
            depot_lat=settings.depot_lat,
            depot_lng=settings.depot_lng,
            created_at=_dt(day, 7),
        )
        session.add(route)
        session.flush()
        session.add_all(orders)
        session.flush()
        result = nearest_neighbor(Point(route.depot_lat, route.depot_lng), [Stop(o.id, Point(o.latitude, o.longitude)) for o in orders])
        by_id = {o.id: o for o in orders}
        for i, oid in enumerate(result.order, 1):
            by_id[oid].stop_sequence = i
            by_id[oid].route_id = route.id
        route.total_distance_km = result.total_km
        route.total_weight_kg = round(sum(o.weight_kg for o in orders), 2)
        if status in ("en_curso", "completada"):
            route.started_at = _dt(day, 8)
        if status == "completada":
            route.completed_at = _dt(day, 17)
        return route

    # Historial: los últimos 6 días, rutas completadas con algunas entregas fallidas.
    for back in range(6, 0, -1):
        day = d(-back)
        for idx, (veh, drv) in enumerate([(vehicles[0], drivers[0]), (vehicles[3], drivers[1])], 1):
            orders = [make_order(day) for _ in range(rng.randint(4, 7))]
            for o in orders:
                if rng.random() < 0.12:
                    o.status, o.failure_reason = (
                        "fallido",
                        rng.choice(["Cliente ausente", "Dirección incorrecta", "Rechazado por el cliente"]),
                    )
                else:
                    o.status, o.delivered_at = "entregado", _dt(day, rng.randint(9, 16))
                    o.proof_note = f"Recibido por {rng.choice(FIRST)} (DNI verificado)"
            make_route(day, veh, drv, orders, "completada", idx)

    # Hoy: una ruta en curso (conductor@demo.pe) con 2 entregas hechas, una planificada y pedidos pendientes.
    today_orders = [make_order(today, "en_ruta") for _ in range(6)]
    route_today = make_route(today, vehicles[0], drivers[0], today_orders, "en_curso", 1)
    session.flush()
    for o in sorted(today_orders, key=lambda x: x.stop_sequence or 0)[:2]:
        o.status, o.delivered_at, o.proof_note = "entregado", _dt(today, 9), "Entregado en recepción del edificio"
    drivers[0].status = "en_ruta"
    _ = route_today

    planned = [make_order(today, "asignado") for _ in range(4)]
    make_route(today, vehicles[3], drivers[1], planned, "planificada", 2)

    session.add_all([make_order(today) for _ in range(9)])  # pendientes de hoy para planificar
    session.add_all([make_order(d(1)) for _ in range(6)])  # pendientes de mañana

    # Mantenimientos y combustible (historial para gráficos de rendimiento).
    session.add_all(
        [
            MaintenanceRecord(
                vehicle_id=vehicles[0].id,
                kind="preventivo",
                description="Cambio de aceite y filtros",
                odometer_km=45_000,
                cost=380.0,
                service_date=d(-40),
                workshop="Taller Automotriz Los Andes",
            ),
            MaintenanceRecord(
                vehicle_id=vehicles[1].id,
                kind="preventivo",
                description="Cambio de aceite, filtros y bujías",
                odometer_km=57_000,
                cost=420.5,
                service_date=d(-75),
                workshop="Servicentro Lima Sur",
            ),
            MaintenanceRecord(
                vehicle_id=vehicles[2].id,
                kind="correctivo",
                description="Cambio de pastillas de freno",
                odometer_km=131_000,
                cost=650.0,
                service_date=d(-20),
                workshop="Frenos y Embragues SAC",
            ),
            MaintenanceRecord(
                vehicle_id=vehicles[4].id,
                kind="preventivo",
                description="Mantenimiento general de moto",
                odometer_km=12_000,
                cost=180.0,
                service_date=d(-90),
                workshop="MotoService Perú",
            ),
        ]
    )
    for veh, liters, price, step in [(vehicles[0], 55, 16.8, 520), (vehicles[1], 45, 17.9, 410), (vehicles[3], 30, 2.1, 300)]:
        odo = veh.odometer_km - step * 6
        for i in range(6, 0, -1):
            odo += step + rng.randint(-40, 40)
            lt = round(liters + rng.uniform(-5, 5), 2)
            session.add(
                FuelLog(
                    vehicle_id=veh.id,
                    fill_date=d(-i * 4),
                    liters=lt,
                    total_cost=round(lt * price, 2),
                    odometer_km=min(odo, veh.odometer_km - (i - 1)),
                    station=rng.choice(["Primax Javier Prado", "Repsol Arequipa", "Pecsa Benavides"]),
                )
            )
    session.commit()
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Siembra datos de demostración")
    parser.add_argument("--reset", action="store_true", help="Elimina y recrea todas las tablas (solo desarrollo)")
    args = parser.parse_args()
    settings = get_settings()
    engine = build_engine(settings.database_url)
    if args.reset:
        if settings.environment == "production":
            raise SystemExit("--reset no está permitido en producción")
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
    with build_session_factory(engine)() as session:
        created = seed(session)
    print("Datos de demostración creados." if created else "Ya existían datos de demostración; no se hizo nada.")


if __name__ == "__main__":
    main()
