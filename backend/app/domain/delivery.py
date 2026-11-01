"""Máquina de estados de los pedidos de entrega y reglas de capacidad.

Diagrama (también en docs/arquitectura.md)::

    pendiente --(se crea ruta)--> asignado --(inicia ruta)--> en_ruta
        |                            |                          |-> entregado (con prueba)
        |                            |-> pendiente (ruta cancelada)
        |-> cancelado <--------------|                          |-> fallido (con motivo)
    fallido --(reprogramar)--> pendiente

Centralizar las transiciones aquí evita que un endpoint marque como
"entregado" un pedido que nunca salió a ruta, y deja un único lugar que
probar.
"""

from app.domain.enums import OrderStatus
from app.domain.errors import ConflictError, DomainError

S = OrderStatus

ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    S.PENDIENTE: {S.ASIGNADO, S.CANCELADO},
    S.ASIGNADO: {S.EN_RUTA, S.PENDIENTE, S.CANCELADO},
    S.EN_RUTA: {S.ENTREGADO, S.FALLIDO},
    S.FALLIDO: {S.PENDIENTE},
    S.ENTREGADO: set(),
    S.CANCELADO: set(),
}

FINAL_STATES = {S.ENTREGADO, S.FALLIDO, S.CANCELADO}


def ensure_transition(current: OrderStatus | str, new: OrderStatus | str) -> None:
    cur, nxt = OrderStatus(current), OrderStatus(new)
    if nxt not in ALLOWED_TRANSITIONS[cur]:
        raise ConflictError(f"No se puede pasar un pedido de '{cur}' a '{nxt}'", code="invalid_transition")


def validate_delivery_proof(note: str | None, has_photo: bool) -> None:
    """Una entrega sin evidencia no es auditable ante un reclamo del cliente."""
    if not has_photo and not (note and note.strip()):
        raise DomainError(
            "La entrega requiere prueba: una foto o una nota (p. ej. quién recibió)",
            code="proof_required",
        )


def ensure_capacity(capacity_kg: float, weights_kg: list[float]) -> float:
    """Valida que la carga total no exceda la capacidad del vehículo.

    Sobrecargar un vehículo es una infracción de tránsito y acelera el
    desgaste de frenos y suspensión, así que es una regla dura (no alerta).
    """
    total = round(sum(weights_kg), 2)
    if total > capacity_kg:
        raise DomainError(
            f"La carga total ({total} kg) excede la capacidad del vehículo ({capacity_kg} kg)",
            code="capacity_exceeded",
        )
    return total
