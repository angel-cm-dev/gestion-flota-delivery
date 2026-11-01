"""Reloj de la aplicación.

Perú no usa horario de verano, así que basta un desplazamiento fijo UTC-5.
Esto evita depender de la base de datos ``tzdata`` (que no viene en Windows).
"Hoy" se evalúa en hora de Lima: un SOAT que vence hoy sigue vigente hasta
la medianoche peruana, no hasta las 7 p. m. (medianoche UTC).
"""

from datetime import UTC, date, datetime, timedelta, timezone

LIMA_TZ = timezone(timedelta(hours=-5), name="America/Lima")


def utcnow() -> datetime:
    return datetime.now(UTC)


def today_lima() -> date:
    return datetime.now(LIMA_TZ).date()
