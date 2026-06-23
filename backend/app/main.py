"""GestorPagosMarcovich — API FastAPI."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import ocr, documentos, pagos, catalogos

settings = get_settings()

app = FastAPI(
    title="GestorPagosMarcovich API",
    version="0.1.0",
    description="Backend de gestión de pagos IT: OCR, PDF de solicitud, historial.",
)

# CORS: si CORS_ORIGINS contiene "*" (o está vacío) se abre a cualquier origen
# (sin credenciales, ya que aún no hay auth). Cuando se agregue login, fijar
# CORS_ORIGINS a la URL exacta de Vercel y se usarán credenciales.
_origins = settings.cors_origins_list
_allow_all = (not _origins) or ("*" in _origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _origins,
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ocr.router)
app.include_router(documentos.router)
app.include_router(pagos.router)
app.include_router(catalogos.router)


@app.get("/")
async def root():
    return {"service": "GestorPagosMarcovich API", "status": "ok"}


@app.get("/health")
async def health():
    db_ok = bool(settings.database_url)
    if db_ok:
        try:
            from app import db as _db
            with _db.get_conn() as c:
                c.execute("SELECT 1")
        except Exception:
            db_ok = False
    return {
        "ok": True,
        "groq_configurada": bool(settings.groq_api_key),
        "db_configurada": db_ok,
    }
