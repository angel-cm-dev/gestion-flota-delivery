"""Modelos ORM (tablas). Ver docs/modelo-datos.md para el diagrama ER."""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utcnow
from app.infrastructure.database import Base

# Numeric(asdecimal=False): exactitud decimal en la BD, float en Python/JSON.
Money = Numeric(12, 2, asdecimal=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    driver: Mapped["Driver | None"] = relationship(back_populates="user", uselist=False)


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint("capacity_kg > 0", name="ck_vehicles_capacity_positive"),
        CheckConstraint("odometer_km >= 0", name="ck_vehicles_odometer_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    brand: Mapped[str] = mapped_column(String(60))
    model: Mapped[str] = mapped_column(String(60))
    year: Mapped[int] = mapped_column(Integer)
    vehicle_type: Mapped[str] = mapped_column(String(20))
    fuel_type: Mapped[str] = mapped_column(String(20))
    capacity_kg: Mapped[float] = mapped_column(Float)
    odometer_km: Mapped[int] = mapped_column(Integer, default=0)
    soat_expiry: Mapped[date] = mapped_column(Date)
    tech_review_expiry: Mapped[date] = mapped_column(Date)
    maintenance_interval_km: Mapped[int] = mapped_column(Integer, default=5000)
    last_maintenance_km: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="activo", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    dni: Mapped[str] = mapped_column(String(8), unique=True)
    phone: Mapped[str] = mapped_column(String(15))
    license_number: Mapped[str] = mapped_column(String(9), unique=True)
    license_category: Mapped[str] = mapped_column(String(10))
    license_expiry: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="disponible", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User | None] = relationship(back_populates="driver")


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (Index("ix_routes_date_status", "route_date", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    route_date: Mapped[date] = mapped_column(Date)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"))
    status: Mapped[str] = mapped_column(String(20), default="planificada")
    depot_lat: Mapped[float] = mapped_column(Float)
    depot_lng: Mapped[float] = mapped_column(Float)
    total_distance_km: Mapped[float] = mapped_column(Float, default=0)
    total_weight_kg: Mapped[float] = mapped_column(Float, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    vehicle: Mapped[Vehicle] = relationship()
    driver: Mapped[Driver] = relationship()
    orders: Mapped[list["Order"]] = relationship(back_populates="route", order_by="Order.stop_sequence")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("weight_kg > 0", name="ck_orders_weight_positive"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_orders_lat"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_orders_lng"),
        Index("ix_orders_date_status", "scheduled_date", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    customer_phone: Mapped[str] = mapped_column(String(15))
    address: Mapped[str] = mapped_column(String(255))
    district: Mapped[str] = mapped_column(String(80), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    scheduled_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="pendiente")
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id", ondelete="SET NULL"), index=True)
    stop_sequence: Mapped[int | None] = mapped_column(Integer)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proof_note: Mapped[str | None] = mapped_column(Text)
    proof_photo_path: Mapped[str | None] = mapped_column(String(255))
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    route: Mapped[Route | None] = relationship(back_populates="orders")


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(String(255))
    odometer_km: Mapped[int] = mapped_column(Integer)
    cost: Mapped[float] = mapped_column(Money)
    service_date: Mapped[date] = mapped_column(Date)
    workshop: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    vehicle: Mapped[Vehicle] = relationship()


class FuelLog(Base):
    __tablename__ = "fuel_logs"
    __table_args__ = (
        CheckConstraint("liters > 0", name="ck_fuel_liters_positive"),
        CheckConstraint("total_cost >= 0", name="ck_fuel_cost_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), index=True)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("drivers.id", ondelete="SET NULL"))
    fill_date: Mapped[date] = mapped_column(Date)
    liters: Mapped[float] = mapped_column(Numeric(10, 2, asdecimal=False))
    total_cost: Mapped[float] = mapped_column(Money)
    odometer_km: Mapped[int] = mapped_column(Integer)
    station: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    vehicle: Mapped[Vehicle] = relationship()
