"""Enumeraciones del dominio.

Se usan ``StrEnum`` para que los valores viajen tal cual en JSON y se guarden
como texto en la base de datos (columnas VARCHAR). Así evitamos los tipos ENUM
nativos de PostgreSQL, que complican las migraciones cuando se agrega un valor.
"""

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    DESPACHADOR = "despachador"
    CONDUCTOR = "conductor"


class VehicleType(StrEnum):
    MOTO = "moto"
    AUTO = "auto"
    FURGONETA = "furgoneta"
    CAMION = "camion"


class VehicleStatus(StrEnum):
    ACTIVO = "activo"
    MANTENIMIENTO = "mantenimiento"
    INACTIVO = "inactivo"


class FuelType(StrEnum):
    GASOLINA = "gasolina"
    DIESEL = "diesel"
    GLP = "glp"
    GNV = "gnv"
    ELECTRICO = "electrico"


class DriverStatus(StrEnum):
    DISPONIBLE = "disponible"
    EN_RUTA = "en_ruta"
    INACTIVO = "inactivo"


class OrderStatus(StrEnum):
    PENDIENTE = "pendiente"
    ASIGNADO = "asignado"
    EN_RUTA = "en_ruta"
    ENTREGADO = "entregado"
    FALLIDO = "fallido"
    CANCELADO = "cancelado"


class RouteStatus(StrEnum):
    PLANIFICADA = "planificada"
    EN_CURSO = "en_curso"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"


class MaintenanceKind(StrEnum):
    PREVENTIVO = "preventivo"
    CORRECTIVO = "correctivo"


class DocumentStatus(StrEnum):
    VIGENTE = "vigente"
    POR_VENCER = "por_vencer"
    VENCIDO = "vencido"


class MaintenanceStatus(StrEnum):
    AL_DIA = "al_dia"
    PROXIMO = "proximo"
    VENCIDO = "vencido"
