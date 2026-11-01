# Guía de la API con ejemplos `curl`

Base URL: `http://localhost:8000` (Docker o `uvicorn`). Documentación interactiva: `/docs` (Swagger) y `/redoc`.

> En Windows PowerShell usa `curl.exe` y comillas dobles escapadas, o ejecuta los ejemplos desde Git Bash.

## 1. Autenticación

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"despacho@demo.pe","password":"Demo123!"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s http://localhost:8000/api/auth/me -H "Authorization: Bearer $TOKEN"
```

Respuesta de login:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 7200,
  "user": { "id": 2, "email": "despacho@demo.pe", "full_name": "Patricia Despacho", "role": "despachador", "is_active": true, "driver_id": null }
}
```

## 2. Vehículos

```bash
# Listado con búsqueda, filtro, orden y paginación
curl -s "http://localhost:8000/api/vehicles?q=toyota&status=activo&sort=-capacity_kg&page=1&size=10" \
  -H "Authorization: Bearer $TOKEN"

# Alta (la placa se normaliza: "xyz 789" -> "XYZ-789")
curl -s -X POST http://localhost:8000/api/vehicles \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"plate":"xyz 789","brand":"Kia","model":"K2700","year":2024,"vehicle_type":"camion","fuel_type":"diesel",
       "capacity_kg":2500,"odometer_km":1000,"soat_expiry":"2027-06-30","tech_review_expiry":"2027-06-30"}'
```

Cada vehículo incluye su estado calculado:

```json
"soat": { "expiry": "2026-11-13", "status": "por_vencer", "days_left": 12 },
"tech_review": { "expiry": "2027-02-04", "status": "vigente", "days_left": 95 },
"maintenance": { "status": "proximo", "next_due_km": 62000, "km_remaining": 250 }
```

Placa inválida → `422`:

```json
{ "status": 422, "code": "validation_error", "detail": "Placa peruana inválida. Formatos válidos: ABC-123 (autos) o 1234-AB (motos)",
  "errors": [{ "field": "plate", "message": "Placa peruana inválida. ..." }] }
```

## 3. Conductores

```bash
curl -s -X POST http://localhost:8000/api/drivers \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"full_name":"Pedro Ramos Díaz","dni":"40123456","phone":"912345678","license_number":"Q40123456",
       "license_category":"A-IIb","license_expiry":"2028-01-01"}'
```

## 4. Pedidos

```bash
curl -s -X POST http://localhost:8000/api/orders \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"customer_name":"Lucía Flores","customer_phone":"987000111","address":"Av. Arequipa 2450","district":"Lince",
       "latitude":-12.085,"longitude":-77.035,"weight_kg":12.5,"scheduled_date":"2026-11-01"}'

# Pendientes de una fecha (varios estados separados por coma)
curl -s "http://localhost:8000/api/orders?status=pendiente&date_from=2026-11-01&date_to=2026-11-01&size=100" \
  -H "Authorization: Bearer $TOKEN"
```

## 5. Rutas

```bash
# Previsualizar el orden optimizado (no guarda nada)
curl -s -X POST http://localhost:8000/api/routes/preview \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"order_ids":[30,31,32,33]}'
# -> { "stops":[{"sequence":1,"order_id":32,"leg_km":3.21},...], "total_km":18.4, "unoptimized_km":27.9, "savings_pct":34.1 }

# Crear la ruta (valida capacidad, documentos, licencia, mantenimiento y disponibilidad)
curl -s -X POST http://localhost:8000/api/routes \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"route_date":"2026-11-01","vehicle_id":2,"driver_id":3,"order_ids":[30,31,32,33]}'

# Iniciar
curl -s -X POST http://localhost:8000/api/routes/15/start -H "Authorization: Bearer $TOKEN"
```

Errores típicos al crear una ruta:

| HTTP | `code` | Causa |
|---|---|---|
| 422 | `capacity_exceeded` | La suma de pesos supera `capacity_kg` |
| 422 | `soat_expired` / `tech_review_expired` | Documento vencido el día de la ruta |
| 422 | `maintenance_overdue` | Mantenimiento preventivo vencido |
| 422 | `license_expired` / `license_category` | Licencia vencida o que no habilita ese tipo de vehículo |
| 409 | `vehicle_busy` / `driver_busy` | Ya tiene una ruta planificada o en curso ese día |
| 409 | `order_not_pending` | Algún pedido ya fue asignado, entregado o cancelado |

## 6. Entregas (conductor)

```bash
CTOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" \
  -d '{"email":"conductor@demo.pe","password":"Demo123!"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Mis rutas de hoy
curl -s http://localhost:8000/api/routes/mine -H "Authorization: Bearer $CTOKEN"

# Entregar con foto y nota (multipart)
curl -s -X POST http://localhost:8000/api/orders/45/deliver \
  -H "Authorization: Bearer $CTOKEN" \
  -F "note=Recibió el portero" -F "photo=@entrega.jpg;type=image/jpeg"

# Entrega fallida
curl -s -X POST http://localhost:8000/api/orders/46/fail \
  -H "Authorization: Bearer $CTOKEN" -H "Content-Type: application/json" -d '{"reason":"Cliente ausente"}'
```

## 7. Mantenimiento, combustible, alertas y dashboard

```bash
curl -s -X POST http://localhost:8000/api/maintenance \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"vehicle_id":5,"kind":"preventivo","description":"Cambio de aceite","odometer_km":16000,"cost":150,"service_date":"2026-11-01"}'

curl -s -X POST http://localhost:8000/api/fuel \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"vehicle_id":1,"fill_date":"2026-11-01","liters":40,"total_cost":672,"odometer_km":48700}'

curl -s http://localhost:8000/api/fuel/efficiency/1 -H "Authorization: Bearer $TOKEN"
curl -s http://localhost:8000/api/alerts -H "Authorization: Bearer $TOKEN"
curl -s http://localhost:8000/api/dashboard -H "Authorization: Bearer $TOKEN"
```

## 8. Códigos de estado

| Código | Significado |
|---|---|
| 200 / 201 / 204 | Éxito |
| 401 | Sin token, token inválido/expirado o usuario desactivado (`WWW-Authenticate: Bearer`) |
| 403 | Rol sin permiso o recurso de otro conductor |
| 404 | Recurso inexistente |
| 409 | Conflicto con el estado actual (duplicados, transición inválida, recurso ocupado) |
| 422 | Datos inválidos o regla de negocio incumplida |
| 500 | Error inesperado (registrado en logs con `request_id`) |
