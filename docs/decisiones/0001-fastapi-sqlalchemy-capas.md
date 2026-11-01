# ADR 0001 — FastAPI + SQLAlchemy 2 organizados en capas

- **Estado:** aceptada
- **Fecha:** 2026-11-01

## Contexto

El sistema tiene muchas reglas de negocio (documentos, licencias, capacidad, estados) que deben probarse a fondo y de forma rápida. Además, debe correr en PostgreSQL en producción y las pruebas deben ejecutarse sin Docker.

## Decisión

- **FastAPI** como framework HTTP por su validación con Pydantic, OpenAPI automático e inyección de dependencias.
- **SQLAlchemy 2.0** (estilo tipado `Mapped[]`) + **Alembic**, usando solo tipos portables (`VARCHAR` para estados, `NUMERIC`, `DATE`, `TIMESTAMPTZ`) para que el mismo esquema funcione en PostgreSQL y SQLite.
- Cuatro capas: `domain` (funciones puras), `application` (servicios/casos de uso y DTOs), `infrastructure` (ORM, repositorios, archivos) y `api` (routers).
- Los modelos ORM actúan como entidades de persistencia; las reglas viven en funciones puras del dominio que reciben valores simples (fechas, km, categorías). Es un punto medio pragmático: evita duplicar cada entidad en una clase de dominio separada, pero mantiene las reglas independientes del ORM.
- La app se construye con `create_app(settings, today=...)`, lo que permite inyectar SQLite en memoria y un reloj fijo en las pruebas.

## Consecuencias

- ✅ 100+ pruebas corren en ~15 s sin servicios externos.
- ✅ Las reglas de dominio se prueban con tablas de casos (`pytest.mark.parametrize`) sin base de datos.
- ⚠️ SQLite no valida todo igual que PostgreSQL (p. ej. longitud de `VARCHAR`); por eso las validaciones de longitud también están en los DTOs y la CI puede ampliarse con un job contra PostgreSQL.
- ⚠️ Los servicios conocen los modelos ORM; si el proyecto creciera mucho, convendría introducir entidades de dominio propias.
