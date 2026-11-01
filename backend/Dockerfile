# syntax=docker/dockerfile:1
# ---------- Etapa 1: instala dependencias en un entorno virtual aislado ----------
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install -r requirements.txt

# ---------- Etapa 2: imagen final mínima, sin compiladores ni caché de pip ----------
FROM python:3.12-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UPLOAD_DIR=/app/uploads
RUN groupadd --system app && useradd --system --gid app --home-dir /app --no-create-home app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app alembic.ini docker-entrypoint.sh ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app app ./app
RUN chmod +x docker-entrypoint.sh && mkdir -p /app/uploads && chown app:app /app/uploads

# Nunca ejecutar como root: si alguien explota la app, no controla el contenedor.
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status == 200 else 1)"
ENTRYPOINT ["./docker-entrypoint.sh"]
