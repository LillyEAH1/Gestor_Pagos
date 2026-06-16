"""
exportar.py (backend) — portado de v60/exportar.py.

Genera el PDF de Solicitud de Pago (plantilla de fondo + drawString con
coordenadas fijas) y el Excel de Estado de Cuenta. Devuelve BYTES (no escribe
a disco), para que los endpoints los streameen al navegador.

Las coordenadas y la lógica de firmas se conservan 1:1 del original.
"""
from __future__ import annotations
import io
import json
from pathlib import Path
from datetime import date

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

PW, PH = letter          # 612 × 792 pts
NEGRO = colors.black
MUTED = colors.HexColor("#333333")

_ASSETS = Path(__file__).resolve().parents[2] / "assets" / "logos"


def _plantilla() -> str:
    p = _ASSETS / "formato2_page-0001.jpg"
    return str(p) if p.exists() else ""


def _get_logo(empresa: str):
    if not empresa:
        return None
    mf = _ASSETS / "logo_map.json"
    if not mf.exists():
        return None
    try:
        m = json.loads(mf.read_text(encoding="utf-8"))
        eu = empresa.upper()
        for k, v in m.items():
            if k.upper() in eu or eu[:12] in k.upper():
                p = _ASSETS / v
                if p.exists():
                    return str(p)
    except Exception:
        pass
    return None


def exportar_solicitud_pdf(datos: dict) -> bytes:
    """Genera el PDF en memoria y devuelve los bytes. NUNCA pone empresa por default."""

    def g(k: str) -> str:
        return (datos.get(k) or "").strip()

    empresa = g("empresa")
    sucursal = g("sucursal")
    cc = g("centro_costos")
    direccion = g("direccion")
    proveedor = g("proveedor_nombre")
    motivo = g("motivo_pago")
    folio = g("folio_cfdi")
    nota_cred = g("notas_credito")
    try:
        monto = float(str(datos.get("monto_total") or 0).replace(",", ""))
    except Exception:
        monto = 0.0
    monto_str = f"$ {monto:,.2f}" if monto else ""
    letra = g("importe_letra")
    banco = g("banco")
    clabe = g("clabe")
    no_cta = g("no_cuenta")
    obs = g("observaciones")
    mes_pres = g("mes_presupuesto")
    mes_pago_ = g("mes_pago")
    fec_sol = g("fecha_proceso") or date.today().strftime("%d/%m/%Y")
    analista = g("analista_nombre")
    gerente = g("gerente_nombre")
    visto_bno = g("visto_bno")
    depto_fin = g("depto_finanzas")
    dir_fin = g("dir_financiera")
    dir_gral = g("dir_general")

    logo_path = _get_logo(empresa)

    buf = io.BytesIO()
    cv = canvas.Canvas(buf, pagesize=letter)

    plantilla = _plantilla()
    if plantilla:
        cv.drawImage(plantilla, 0, 0, width=PW, height=PH, preserveAspectRatio=False)

    if logo_path:
        try:
            cv.drawImage(logo_path, 22, PH - 88, width=95, height=52,
                         preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    elif empresa:
        cv.setFont("Helvetica", 7.5)
        cv.setFillColor(NEGRO)
        cv.drawString(22, PH - 62, empresa)

    def ds(txt, x, y, sz=8.5, bold=False, color=NEGRO):
        if not txt:
            return
        cv.setFillColor(color)
        cv.setFont("Helvetica-Bold" if bold else "Helvetica", sz)
        cv.drawString(x, y, str(txt))
        cv.setFillColor(NEGRO)

    def dsr(txt, x, y, sz=8.5, bold=False):
        if not txt:
            return
        cv.setFont("Helvetica-Bold" if bold else "Helvetica", sz)
        cv.setFillColor(NEGRO)
        cv.drawRightString(x, y, str(txt))

    def dsc(txt, x, y, sz=7.0, bold=False, color=NEGRO):
        if not txt:
            return
        cv.setFillColor(color)
        cv.setFont("Helvetica-Bold" if bold else "Helvetica", sz)
        cv.drawCentredString(x, y, str(txt))
        cv.setFillColor(NEGRO)

    # ── SUCURSAL | Fecha de solicitud ────────────────────
    ds(sucursal, 180.5, 673.0, sz=8.5, bold=True)
    ds(fec_sol, 494.4, 673.0, sz=8.5)
    # ── CENTRO DE COSTOS | DIRECCIÓN ─────────────────────
    ds(cc, 137.8, 648.0, sz=8.0)
    ds(direccion, 456.0, 648.0, sz=8.0, bold=True)
    # ── BENEFICIARIO ─────────────────────────────────────
    ds(proveedor, 137.8, 613.0, sz=8.5, bold=True)
    # ── MOTIVO DE PAGO ───────────────────────────────────
    ds(motivo, 137.8, 591.4, sz=8.5)
    # ── DATOS DE CFDI — Folio | Nota de crédito ──────────
    dsc(folio, 340.0, 529.0, sz=8.5, bold=True)
    ds(nota_cred, 468.0, 529.0, sz=8.0)
    # ── DATOS DE PAGO — Importe ──────────────────────────
    ds(letra, 137.8, 461.8, sz=7.5)
    dsr(monto_str, 597.6, 461.8, sz=11.0, bold=True)
    # ── Banco | CLABE | No. de Cuenta ────────────────────
    ds(banco, 81.6, 435.8, sz=8.5, bold=True)
    ds(clabe, 235.2, 435.8, sz=8.5, bold=True)
    ds(no_cta, 504.0, 435.8, sz=8.5, bold=True)
    # ── Observaciones ────────────────────────────────────
    ds(obs, 137.8, 409.0, sz=8.0, bold=True)
    # ── EXCLUSIVO FINANZAS ───────────────────────────────
    ds(mes_pres, 218.4, 332.2, sz=8.5, bold=True)
    ds(mes_pago_, 429.6, 332.2, sz=8.5, bold=True)
    ds(cc, 137.8, 297.6, sz=8.0)

    # ── FIRMAS ───────────────────────────────────────────
    XC1, XC2, XC3, XC4 = 76.5, 229.5, 382.5, 535.5
    Y1N, Y1D = 233.8, 226.6
    dsc(analista, XC1, Y1N, sz=6.5, bold=True)
    dsc(gerente, XC2, Y1N, sz=6.5, bold=True)
    dsc("ANALISTA DE SISTEMAS", XC1, Y1D, sz=5.5, color=MUTED)
    dsc("GERENTE DE SISTEMAS", XC2, Y1D, sz=5.5, color=MUTED)

    Y2N, Y2D = 125.8, 118.6
    dsc(visto_bno, XC1, Y2N, sz=6.5, bold=True)
    dsc(depto_fin, XC2, Y2N, sz=6.5, bold=True)
    dsc(dir_fin, XC3, Y2N, sz=6.5, bold=True)
    dsc(dir_gral, XC4, Y2N, sz=6.5, bold=True)
    dsc("DEPARTAMENTO DE FINANZAS", XC1, Y2D, sz=5.5, color=MUTED)
    dsc("DEPARTAMENTO DE FINANZAS", XC2, Y2D, sz=5.5, color=MUTED)
    dsc("DIRECCIÓN FINANCIERA", XC3, Y2D, sz=5.5, color=MUTED)
    dsc("DIRECCIÓN GENERAL", XC4, Y2D, sz=5.5, color=MUTED)

    cv.save()
    return buf.getvalue()


def exportar_estado_cuenta_xlsx(estado: dict) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

    wb = Workbook()
    ws = wb.active
    ws.title = "Estado de Cuenta"
    neg = PatternFill("solid", fgColor="374151")
    ver = PatternFill("solid", fgColor="166534")
    amb = PatternFill("solid", fgColor="92400E")
    grs = PatternFill("solid", fgColor="F3F4F6")
    thin = Border(left=Side(style="thin"), right=Side(style="thin"),
                  top=Side(style="thin"), bottom=Side(style="thin"))

    ws.merge_cells("A1:G1")
    ws["A1"] = f"Estado de Cuenta — {estado.get('mes_nombre', '')} {estado.get('anio', '')}"
    ws["A1"].font = Font(bold=True, size=13, color="FFFFFF")
    ws["A1"].fill = neg
    ws["A1"].alignment = Alignment(horizontal="center")
    ws.merge_cells("A2:D2")
    ws["A2"] = f"Total pagado: ${estado.get('total_pagado', 0):,.2f}"
    ws["A2"].font = Font(bold=True, color="15803D")
    ws.merge_cells("E2:G2")
    ws["E2"] = f"Total pendiente: ${estado.get('total_pendiente', 0):,.2f}"
    ws["E2"].font = Font(bold=True, color="B45309")

    hdrs = ["ID", "Proveedor", "Empresa", "Motivo de pago", "Monto", "Estatus", "Fecha"]
    for col, h in enumerate(hdrs, 1):
        cell = ws.cell(row=3, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = neg
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin

    for ri, pg in enumerate(estado.get("todos", []), 4):
        est = (pg.get("estatus") or "PENDIENTE").upper()
        ef = ver if est == "PAGADO" else amb
        for col, v in enumerate([
            pg.get("id", ""), pg.get("proveedor_nombre", ""),
            pg.get("empresa", ""), pg.get("motivo_pago", ""),
            pg.get("monto_total", 0), est, pg.get("fecha_proceso", ""),
        ], 1):
            cell = ws.cell(row=ri, column=col, value=v)
            cell.fill = ef if col == 6 else (grs if ri % 2 == 0 else PatternFill())
            cell.border = thin
            if col == 5:
                cell.number_format = "$#,##0.00"

    for col, w in enumerate([8, 25, 22, 35, 14, 12, 14], 1):
        ws.column_dimensions[chr(64 + col)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
