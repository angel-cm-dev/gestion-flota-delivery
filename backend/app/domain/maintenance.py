"""Mantenimiento preventivo por kilometraje.

Cada vehículo tiene un intervalo (p. ej. cada 5 000 km cambio de aceite y
filtros). El próximo mantenimiento vence en ``last_maintenance_km + interval``.
Se alerta cuando faltan ``warning_km`` o menos, y un vehículo con el
mantenimiento vencido no puede salir a ruta: es más barato parar un día que
reparar un motor o perder una entrega por avería.
"""

from dataclasses import dataclass

from app.domain.enums import MaintenanceStatus


@dataclass(frozen=True)
class MaintenanceCheck:
    status: MaintenanceStatus
    next_due_km: int
    km_remaining: int


def maintenance_status(odometer_km: int, last_maintenance_km: int, interval_km: int, warning_km: int = 500) -> MaintenanceCheck:
    if interval_km <= 0:
        raise ValueError("El intervalo de mantenimiento debe ser positivo")
    next_due = last_maintenance_km + interval_km
    remaining = next_due - odometer_km
    if remaining <= 0:
        status = MaintenanceStatus.VENCIDO
    elif remaining <= warning_km:
        status = MaintenanceStatus.PROXIMO
    else:
        status = MaintenanceStatus.AL_DIA
    return MaintenanceCheck(status=status, next_due_km=next_due, km_remaining=remaining)
