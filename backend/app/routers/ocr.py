"""Endpoints de OCR (Groq Vision)."""
import asyncio
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.services import ocr_scanner
from app.config import get_settings

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.post("/escanear")
async def escanear(
    archivo: UploadFile = File(...),
    tipo_doc: str = Form("recibo"),
):
    """
    Recibe un PDF o imagen del recibo/factura y devuelve los campos extraídos.
    tipo_doc: "recibo" | "telmex" | "factura".
    """
    data = await archivo.read()
    if not data:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande (máx 15 MB)")
    resultado = await asyncio.to_thread(
        ocr_scanner.escanear_recibo_bytes,
        data, archivo.filename or "archivo", tipo_doc=tipo_doc,
    )
    return resultado


@router.get("/probar")
async def probar():
    """Verifica que la Groq API key configurada funcione."""
    key = get_settings().groq_api_key
    if not key:
        raise HTTPException(status_code=400, detail="GROQ_API_KEY no configurada")
    ok, msg = ocr_scanner.probar_groq_conexion(key)
    return {"ok": ok, "mensaje": msg}
