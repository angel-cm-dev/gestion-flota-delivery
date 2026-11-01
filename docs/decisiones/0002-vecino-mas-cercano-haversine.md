# ADR 0002 — Orden de paradas con vecino más cercano y distancia haversine

- **Estado:** aceptada
- **Fecha:** 2026-11-01

## Contexto

El despachador necesita un orden de visita razonable para 5 a 40 paradas urbanas. Ordenar paradas es una variante del problema del viajante (TSP), NP-difícil. No queremos depender de APIs pagadas (Google Directions) ni de un servidor de ruteo para la primera versión.

## Opciones consideradas

| Opción | Calidad | Costo / complejidad |
|---|---|---|
| Orden manual | Mala | Nulo |
| **Vecino más cercano + haversine** | Buena (típicamente 15–25 % peor que el óptimo) | O(n²), sin dependencias |
| Vecino más cercano + 2-opt | Muy buena | O(n²) por iteración, más código |
| OR-Tools / VRP solver | Óptima o casi | Dependencia pesada, configuración compleja |
| OSRM / Google Directions | Distancias reales por calles | Servidor propio o API de pago |

## Decisión

Usar **vecino más cercano** desde el depósito con distancia **haversine**, con desempate determinista por `id`, encapsulado en `app/domain/geo.py`. La función de costo está aislada para reemplazarla luego por distancias de OSRM sin tocar los servicios.

## Consecuencias

- ✅ Resultado instantáneo, explicable y reproducible (fácil de probar).
- ✅ El endpoint `/api/routes/preview` muestra el ahorro frente al orden manual (≈40 % en los datos demo).
- ⚠️ La distancia en línea recta subestima la distancia real por calles (≈1.3–1.5× en Lima).
- ⚠️ No considera ventanas horarias ni tráfico. Queda en el roadmap (2-opt, OSRM, VRPTW).
