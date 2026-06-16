"""Endpoints de generación de documentos: PDF de solicitud y Excel de estado."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app import db
from app.schemas import DocumentoPagoIn, NumeroLetraIn
from app.services import exportar
from app.services.numero_letra import numero_a_letra

router = APIRouter(prefix="/api/documentos", tags=["documentos"])

_MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
          "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _nombre_pdf(datos: dict) -> str:
    prov = (datos.get("proveedor_nombre") or "PAGO").split()[0].upper()
    emp = (datos.get("empresa") or "").split()[0].upper()
    fecha = (datos.get("fecha_proceso") or "").replace("/", "")
    base = "_".join(p for p in ["Solicitud", emp, prov, fecha] if p)
    return f"{base or 'Solicitud'}.pdf"


@router.post("/pdf")
async def generar_pdf(body: DocumentoPagoIn):
    """Genera el PDF de Solicitud de Pago a partir de los datos del formulario."""
    datos = dict(body.datos)
    if not datos.get("importe_letra") and datos.get("monto_total"):
        try:
            datos["importe_letra"] = numero_a_letra(float(datos["monto_total"]))
        except Exception:
            pass
    pdf_bytes = exportar.exportar_solicitud_pdf(datos)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{_nombre_pdf(datos)}"'},
    )


@router.get("/excel")
async def generar_excel(mes: int, anio: int):
    """Genera el Excel de Estado de Cuenta de un mes/año."""
    if not db.db_disponible():
        raise HTTPException(status_code=503, detail="Base de datos no configurada")
    estado = db.estado_cuenta_mes(mes, anio)
    estado["mes_nombre"] = _MESES[mes] if 1 <= mes <= 12 else str(mes)
    xlsx = exportar.exportar_estado_cuenta_xlsx(estado)
    fname = f"EstadoCuenta_{estado['mes_nombre']}_{anio}.xlsx"
    return Response(
        content=xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post("/numero-letra")
async def a_letra(body: NumeroLetraIn):
    return {"letra": numero_a_letra(body.monto)}
