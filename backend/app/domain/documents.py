"""Vigencia de documentos (SOAT, revisión técnica, licencia de conducir).

Un vehículo con SOAT o revisión técnica vencida no puede circular legalmente
(multas MTC y, en caso de accidente, la aseguradora no cubre). Por eso el
sistema bloquea la asignación de rutas con documentos vencidos y alerta con
anticipación (``warning_days``) para que el área de flota los renueve a tiempo.
"""

from dataclasses import dataclass
from datetime import date

from app.domain.enums import DocumentStatus


@dataclass(frozen=True)
class DocumentCheck:
    status: DocumentStatus
    days_left: int


def document_status(expiry: date, today: date, warning_days: int = 30) -> DocumentCheck:
    """Evalúa la vigencia de un documento a una fecha dada.

    El documento es válido *hasta el día de vencimiento inclusive*, por eso
    ``days_left == 0`` todavía cuenta como "por vencer" y no como "vencido".
    """
    days_left = (expiry - today).days
    if days_left < 0:
        status = DocumentStatus.VENCIDO
    elif days_left <= warning_days:
        status = DocumentStatus.POR_VENCER
    else:
        status = DocumentStatus.VIGENTE
    return DocumentCheck(status=status, days_left=days_left)


def is_valid_on(expiry: date, on: date) -> bool:
    return expiry >= on
