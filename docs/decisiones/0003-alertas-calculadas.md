# ADR 0003 — Alertas y estados de vigencia calculados al vuelo

- **Estado:** aceptada
- **Fecha:** 2026-11-01

## Contexto

Las alertas (SOAT, revisión técnica, licencia, mantenimiento) dependen de la fecha actual y del odómetro. Si se guardaran en una tabla, habría que recalcularlas con un *job* programado y podrían quedar desactualizadas (p. ej. si alguien corrige un vencimiento).

## Decisión

No persistir alertas ni estados de vigencia. Se calculan en cada consulta con funciones puras (`document_status`, `maintenance_status`) a partir de los datos fuente, usando "hoy" en hora de Lima (UTC-5). El umbral de aviso es configurable (`DOCUMENT_WARNING_DAYS`, `MAINTENANCE_WARNING_KM`).

## Consecuencias

- ✅ Siempre consistentes: corregir una fecha actualiza la alerta inmediatamente.
- ✅ Sin *cron jobs* ni tablas extra; fácil de probar con un reloj inyectado.
- ⚠️ El costo es O(vehículos + conductores) por consulta; con miles de unidades convendría filtrar en SQL por rango de fechas o cachear.
- ⚠️ Para notificar por correo/WhatsApp se necesitará igualmente un proceso programado que reutilice estas mismas funciones (en roadmap).
