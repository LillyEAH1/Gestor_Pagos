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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
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
    return {
        "ok": True,
        "groq_configurada": bool(settings.groq_api_key),
        "db_configurada": bool(settings.database_url),
    }
