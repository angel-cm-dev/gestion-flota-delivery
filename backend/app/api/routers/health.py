from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=["Salud"])


@router.get("/health", summary="Estado del servicio y de la base de datos")
def health(request: Request) -> JSONResponse:
    """Usado por Docker/Kubernetes: 200 si la BD responde, 503 si no."""
    try:
        with request.app.state.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    body = {"status": "ok" if db_ok else "degraded", "database": "up" if db_ok else "down", "version": request.app.version}
    return JSONResponse(body, status_code=200 if db_ok else 503)
