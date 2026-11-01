"""Cálculos geográficos y optimización de rutas.

Usamos la fórmula de *haversine* (distancia sobre la esfera terrestre) porque
no requiere servicios externos y es suficientemente precisa para ordenar
paradas dentro de una ciudad. La distancia real por calles será mayor; si en el
futuro se integra OSRM o Google Directions, solo cambia la función de costo.

El orden de paradas se obtiene con la heurística del *vecino más cercano*:
desde el depósito, siempre ir a la parada no visitada más próxima. Es O(n²),
determinista y explicable al despachador. No garantiza el óptimo (el TSP es
NP-difícil), pero suele quedar dentro de un 20-25 % del mejor recorrido, lo
que es aceptable para rutas urbanas de 5 a 40 paradas.
"""

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True)
class Point:
    lat: float
    lng: float


@dataclass(frozen=True)
class Stop:
    id: int
    point: Point


@dataclass(frozen=True)
class OptimizedRoute:
    order: list[int]
    legs_km: list[float]
    total_km: float


def haversine_km(a: Point, b: Point) -> float:
    lat1, lng1, lat2, lng2 = map(radians, (a.lat, a.lng, b.lat, b.lng))
    dlat, dlng = lat2 - lat1, lng2 - lng1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(h))


def nearest_neighbor(depot: Point, stops: list[Stop], *, return_to_depot: bool = True) -> OptimizedRoute:
    """Ordena las paradas con la heurística del vecino más cercano.

    En caso de empate de distancias se elige el ``id`` menor, para que el
    resultado sea reproducible (importante para pruebas y para que el
    despachador vea siempre el mismo orden con los mismos datos).
    """
    pending = list(stops)
    current = depot
    order: list[int] = []
    legs: list[float] = []
    while pending:
        nxt = min(pending, key=lambda s: (haversine_km(current, s.point), s.id))
        legs.append(haversine_km(current, nxt.point))
        order.append(nxt.id)
        current = nxt.point
        pending.remove(nxt)
    if return_to_depot and order:
        legs.append(haversine_km(current, depot))
    return OptimizedRoute(order=order, legs_km=[round(x, 3) for x in legs], total_km=round(sum(legs), 2))


def route_length_km(depot: Point, points: list[Point], *, return_to_depot: bool = True) -> float:
    """Longitud de un recorrido en el orden dado (útil para comparar contra el optimizado)."""
    total, current = 0.0, depot
    for p in points:
        total += haversine_km(current, p)
        current = p
    if return_to_depot and points:
        total += haversine_km(current, depot)
    return round(total, 2)
