"""Consumo de combustible.

El rendimiento (km/litro) se calcula con el método de *tanque lleno a tanque
lleno*: los km recorridos desde la carga anterior divididos entre los litros
de la carga actual. Por eso el odómetro debe ser estrictamente creciente entre
cargas; un odómetro menor indica un error de digitación (o manipulación) y se
rechaza.
"""

from app.domain.errors import DomainError


def ensure_odometer_increases(previous_km: int | None, new_km: int) -> None:
    if previous_km is not None and new_km <= previous_km:
        raise DomainError(
            f"El odómetro ({new_km} km) debe ser mayor al último registrado ({previous_km} km)",
            code="odometer_not_increasing",
        )


def km_per_liter(previous_km: int, current_km: int, liters: float) -> float:
    if liters <= 0:
        raise ValueError("Los litros deben ser positivos")
    return round((current_km - previous_km) / liters, 2)


def cost_per_km(total_cost: float, km: int) -> float | None:
    return round(total_cost / km, 3) if km > 0 else None
