"""Endpoints de generación de documentos: PDF de solicitud y Excel de estado."""
import re
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from datetime import date

from app import db
from app.schemas import DocumentoPagoIn, NumeroLetraIn
from app.services import exportar
from app.services.numero_letra import numero_a_letra

router = APIRouter(prefix="/api/documentos", tags=["documentos"])

_MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
          "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

_MESES_ABREV = {
    "enero": "ENE", "febrero": "FEB", "marzo": "MAR", "abril": "ABR",
    "mayo": "MAY", "junio": "JUN", "julio": "JUL", "agosto": "AGO",
    "septiembre": "SEP", "octubre": "OCT", "noviembre": "NOV", "diciembre": "DIC",
}

# nom_corto por empresa (Master Excel)
_NOM_CORTO = {
    "BH. BE HEALTHY COMERCIALIZADORA": "BH",
    "BH SOLAR": "BH SOL",
    "BLOOM & BLUSH": "B&B",
    "COMERCIALIZADORA DE MARCAS JSB": "JSB",
    "COMERCIALIZADORA ONLINE NH": "NH",
    "ENFERMERAS UNIDAS PLUS": "EUP",
    "GOLDEN YEARS MANAGEMENT": "GYM",
    "MB COMERCIALIZADORA EN LINEA": "MB",
    "MOSAIC CARE & HEALTH": "MH&C",
    "SELECT SHOP MB": "SSMB",
    "SM DISTRIBUIDORA DIGITAL": "SMD",
    "INMOBILIARIA EISHEL": "EISH",
    "ALEGARAT": "ALGT",
    "ZONA ZELU": "ZZ",
    "DONKERTECH": "DNKT",
    "MW MED SUPPLY MEDICAL": "MW MED",
}

_SUFIJOS_LEGALES = re.compile(
    r"\s+(SAB\s+DE\s+CV|SAPI\s+DE\s+CV|SA\s+DE\s+CV|S\.A\.\s+DE\s+C\.V\.|"
    r"SA\s+DE\s+C\.V\.|S\.A\.P\.I\.\s+DE\s+C\.V\.|SC\s+DE\s+CV|"
    r"S\s+DE\s+RL|SRL\s+DE\s+CV)$",
    re.IGNORECASE,
)


def _nom_corto_empresa(empresa: str) -> str:
    eu = empresa.upper().strip()
    for k, v in _NOM_CORTO.items():
        if k.upper() in eu or eu in k.upper():
            return v
    # Fallback: primera palabra
    return eu.split()[0] if eu else ""


def _nombre_pdf(datos: dict) -> str:
    emp = _nom_corto_empresa(datos.get("empresa") or "")

    prov_raw = (datos.get("proveedor_nombre") or "PAGO").strip().upper()
    prov = _SUFIJOS_LEGALES.sub("", prov_raw).strip()

    fecha_raw = datos.get("fecha_proceso") or date.today().strftime("%d/%m/%Y")
    try:
        d, m, y = fecha_raw.split("/")
        fecha_str = f"{d.zfill(2)}{m.zfill(2)}{y[2:]}"   # "22/6/2026" → "220626"
    except Exception:
        fecha_str = fecha_raw.replace("/", "")

    mes_raw = (datos.get("mes_pago") or datos.get("mes_presupuesto") or "").lower()
    mes_abrev = _MESES_ABREV.get(mes_raw, mes_raw[:3].upper() if mes_raw else "")

    partes = [p for p in ["Solicitud", emp, prov, fecha_str, mes_abrev] if p]
    return "_".join(partes) + ".pdf"


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
    nombre = _nombre_pdf(datos)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
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
