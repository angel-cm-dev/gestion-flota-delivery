# Modelo de datos

Esquema creado por la migración `backend/alembic/versions/0001_esquema_inicial.py`. Los estados se guardan como `VARCHAR` (no `ENUM` nativo) para poder agregar valores sin migraciones complejas; la aplicación valida los valores permitidos.

```mermaid
erDiagram
    USERS ||--o| DRIVERS : "cuenta del conductor"
    VEHICLES ||--o{ ROUTES : "realiza"
    DRIVERS ||--o{ ROUTES : "conduce"
    ROUTES ||--o{ ORDERS : "contiene (paradas)"
    VEHICLES ||--o{ MAINTENANCE_RECORDS : "recibe"
    VEHICLES ||--o{ FUEL_LOGS : "carga"
    DRIVERS ||--o{ FUEL_LOGS : "registra"

    USERS {
        int id PK
        varchar email UK
        varchar full_name
        varchar password_hash "Argon2id"
        varchar role "admin | despachador | conductor"
        bool is_active
        timestamptz created_at
    }
    VEHICLES {
        int id PK
        varchar plate UK "ABC-123 / 1234-AB"
        varchar brand
        varchar model
        int year
        varchar vehicle_type "moto | auto | furgoneta | camion"
        varchar fuel_type
        float capacity_kg "CHECK > 0"
        int odometer_km "CHECK >= 0"
        date soat_expiry
        date tech_review_expiry
        int maintenance_interval_km
        int last_maintenance_km
        varchar status "activo | mantenimiento | inactivo"
        timestamptz created_at
    }
    DRIVERS {
        int id PK
        int user_id FK,UK "nullable"
        varchar full_name
        varchar dni UK "8 dígitos"
        varchar phone "9XXXXXXXX"
        varchar license_number UK "letra + DNI"
        varchar license_category "A-I … A-IIIc, B-I … B-IIc"
        date license_expiry
        varchar status "disponible | en_ruta | inactivo"
        timestamptz created_at
    }
    ROUTES {
        int id PK
        varchar code UK "R20260615-01"
        date route_date
        int vehicle_id FK
        int driver_id FK
        varchar status "planificada | en_curso | completada | cancelada"
        float depot_lat
        float depot_lng
        float total_distance_km
        float total_weight_kg
        timestamptz started_at
        timestamptz completed_at
        timestamptz created_at
    }
    ORDERS {
        int id PK
        varchar code UK "PED-260615-0001"
        varchar customer_name
        varchar customer_phone
        varchar address
        varchar district
        float latitude "CHECK -90..90"
        float longitude "CHECK -180..180"
        float weight_kg "CHECK > 0"
        text notes
        date scheduled_date
        varchar status
        int route_id FK "nullable"
        int stop_sequence "orden optimizado"
        timestamptz delivered_at
        text proof_note
        varchar proof_photo_path
        varchar failure_reason
        timestamptz created_at
    }
    MAINTENANCE_RECORDS {
        int id PK
        int vehicle_id FK
        varchar kind "preventivo | correctivo"
        varchar description
        int odometer_km
        numeric cost "12,2"
        date service_date
        varchar workshop
        timestamptz created_at
    }
    FUEL_LOGS {
        int id PK
        int vehicle_id FK
        int driver_id FK "nullable"
        date fill_date
        numeric liters "CHECK > 0"
        numeric total_cost "CHECK >= 0"
        int odometer_km
        varchar station
        timestamptz created_at
    }
```

## Tablas

| Tabla | Propósito | Notas de diseño |
|---|---|---|
| `users` | Cuentas de acceso y rol | Email único (comparación en minúsculas). El hash nunca sale en los DTOs. |
| `vehicles` | Unidades de la flota | La placa se guarda **normalizada** para que la restricción `UNIQUE` sea efectiva. El estado de documentos/mantenimiento **no se guarda**: se calcula (ver ADR 0003). |
| `drivers` | Conductores | `user_id` es opcional y único: vincula al conductor con su cuenta para la app móvil. DNI y licencia únicos. |
| `routes` | Recorrido de un vehículo + conductor en una fecha | Guarda el depósito usado (si cambia la configuración, las rutas históricas no se alteran) y la distancia/carga calculadas. Índice `(route_date, status)` para la regla "una ruta activa por día". |
| `orders` | Pedidos de entrega y su prueba | `route_id` + `stop_sequence` definen el orden de visita. `ON DELETE SET NULL` en la ruta conserva el pedido. Índice `(scheduled_date, status)` para el planificador y el dashboard. |
| `maintenance_records` | Historial de servicios | Un preventivo actualiza `vehicles.last_maintenance_km`. |
| `fuel_logs` | Cargas de combustible | El km/l se calcula entre cargas consecutivas (no se guarda, así corregir una carga no deja datos inconsistentes). |

## Montos y decimales

`cost`, `liters` y `total_cost` usan `NUMERIC` en la base (exactitud decimal) y se exponen como `float` en JSON para simplificar el frontend.

## Fechas y zona horaria

- `DATE` para vencimientos y fechas operativas; se comparan contra "hoy" en **hora de Lima (UTC-5)**.
- `TIMESTAMPTZ` para eventos (`created_at`, `delivered_at`), almacenados en UTC.
