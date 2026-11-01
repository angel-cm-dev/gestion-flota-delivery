"""Pruebas de haversine y de la heurística del vecino más cercano."""

import pytest

from app.domain.geo import Point, Stop, haversine_km, nearest_neighbor, route_length_km


def test_haversine_one_degree_on_equator():
    assert haversine_km(Point(0, 0), Point(0, 1)) == pytest.approx(111.19, abs=0.01)


def test_haversine_is_symmetric_and_zero_for_same_point():
    a, b = Point(-12.1211, -77.0297), Point(-12.0977, -77.0365)  # Miraflores -> San Isidro
    assert haversine_km(a, a) == 0
    assert haversine_km(a, b) == pytest.approx(haversine_km(b, a))
    assert 2.4 < haversine_km(a, b) < 2.9


def test_nearest_neighbor_visits_closest_first():
    depot = Point(0, 0)
    stops = [Stop(1, Point(0, 3)), Stop(2, Point(0, 1)), Stop(3, Point(0, 2))]
    result = nearest_neighbor(depot, stops)
    assert result.order == [2, 3, 1]
    # 1 + 1 + 1 grados de ida y 3 de regreso al depósito.
    assert result.total_km == pytest.approx(6 * 111.19, rel=1e-3)
    assert len(result.legs_km) == 4


def test_nearest_neighbor_without_return():
    result = nearest_neighbor(Point(0, 0), [Stop(1, Point(0, 1))], return_to_depot=False)
    assert result.legs_km == [pytest.approx(111.195, abs=0.01)]


def test_tie_break_is_deterministic_by_id():
    stops = [Stop(9, Point(0, 1)), Stop(4, Point(0, -1))]
    assert nearest_neighbor(Point(0, 0), stops).order == [4, 9]


def test_empty_route():
    result = nearest_neighbor(Point(0, 0), [])
    assert result.order == [] and result.total_km == 0


def test_optimized_is_not_worse_than_zigzag():
    depot = Point(-12.0464, -77.0428)
    pts = [Point(-12.15, -77.02), Point(-12.05, -77.05), Point(-12.14, -77.01), Point(-12.06, -77.06)]
    stops = [Stop(i, p) for i, p in enumerate(pts)]
    optimized = nearest_neighbor(depot, stops)
    assert optimized.total_km <= route_length_km(depot, pts)
