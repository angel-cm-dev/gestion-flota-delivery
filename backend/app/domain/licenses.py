"""Reglas de licencias de conducir (MTC Perú).

* El número de licencia es una letra seguida de los 8 dígitos del DNI
  (p. ej. ``Q45781236``).
* Clase A (vehículos motorizados de 4 ruedas): A-I, A-IIa, A-IIb, A-IIIa,
  A-IIIb, A-IIIc. Clase B (vehículos menores): B-I, B-IIa, B-IIb, B-IIc.

Simplificación de negocio usada en este sistema (documentada en el README):

* moto      -> requiere B-IIa, B-IIb o B-IIc
* auto      -> cualquier categoría A
* furgoneta -> A-IIa o superior (transporte de carga liviana con fines comerciales)
* camion    -> A-IIb o superior
"""

import re

from app.domain.enums import VehicleType

LICENSE_NUMBER = re.compile(r"^[A-Z]\d{8}$")

CATEGORIES_A = ["A-I", "A-IIa", "A-IIb", "A-IIIa", "A-IIIb", "A-IIIc"]
CATEGORIES_B = ["B-I", "B-IIa", "B-IIb", "B-IIc"]
ALL_CATEGORIES = CATEGORIES_A + CATEGORIES_B

_MIN_CATEGORY_A = {
    VehicleType.AUTO: "A-I",
    VehicleType.FURGONETA: "A-IIa",
    VehicleType.CAMION: "A-IIb",
}


def normalize_license_number(raw: str) -> str:
    value = raw.strip().upper()
    if not LICENSE_NUMBER.match(value):
        raise ValueError("Número de licencia inválido. Formato: letra + 8 dígitos (p. ej. Q45781236)")
    return value


def validate_category(category: str) -> str:
    if category not in ALL_CATEGORIES:
        raise ValueError(f"Categoría de licencia inválida. Valores: {', '.join(ALL_CATEGORIES)}")
    return category


def can_drive(category: str, vehicle_type: VehicleType | str) -> bool:
    """Indica si una categoría de licencia habilita a conducir el tipo de vehículo."""
    vtype = VehicleType(vehicle_type)
    if vtype == VehicleType.MOTO:
        return category in ("B-IIa", "B-IIb", "B-IIc")
    if category not in CATEGORIES_A:
        return False
    # Las categorías A son acumulativas: una superior habilita las inferiores.
    return CATEGORIES_A.index(category) >= CATEGORIES_A.index(_MIN_CATEGORY_A[vtype])
