"""Validación de placas vehiculares peruanas.

Formatos aceptados (sistema de placas vigente desde 2010, SUNARP):

* Vehículos de 4 ruedas: ``ABC-123``. El primer carácter es siempre una letra
  (indica la región/categoría) y los dos siguientes pueden ser letras o dígitos
  (p. ej. ``A1B-234``, ``C4F-512``); terminan en 3 dígitos.
* Motocicletas: ``1234-AB`` (4 dígitos + 2 letras).

Las placas se normalizan a mayúsculas, sin espacios y con guion, para que
"abc123", "ABC 123" y "ABC-123" se reconozcan como la misma unidad y la
restricción UNIQUE de la base de datos funcione de verdad.
"""

import re

_CAR = re.compile(r"^([A-Z][A-Z0-9]{2})-?(\d{3})$")
_MOTO = re.compile(r"^(\d{4})-?([A-Z]{2})$")


def normalize_plate(raw: str) -> str:
    """Devuelve la placa normalizada o lanza ``ValueError`` si no es válida."""
    if raw is None:
        raise ValueError("La placa es obligatoria")
    value = re.sub(r"\s+", "", raw).upper()
    if m := _CAR.match(value):
        return f"{m.group(1)}-{m.group(2)}"
    if m := _MOTO.match(value):
        return f"{m.group(1)}-{m.group(2)}"
    raise ValueError("Placa peruana inválida. Formatos válidos: ABC-123 (autos) o 1234-AB (motos)")


def is_motorcycle_plate(plate: str) -> bool:
    return bool(_MOTO.match(plate.replace(" ", "").upper()))
