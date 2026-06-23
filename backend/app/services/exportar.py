"""
exportar.py — generación de documentos.

Solicitud de Pago: overlay de texto sobre solicitud_bg.pdf
(formulario en blanco exportado desde el Excel real con Excel/win32com)
usando PyMuPDF con coordenadas calibradas en cell_coords.json.
Sin dependencia de LibreOffice en Render.
"""
from __future__ import annotations
import io
import json
from pathlib import Path
from datetime import date

import fitz  # PyMuPDF

ASSETS = Path(__file__).resolve().parents[2] / "assets"
BG_PDF = ASSETS / "solicitud_bg.pdf"
CELL_COORDS = ASSETS / "cell_coords.json"


def _load_coords() -> dict:
    return json.loads(CELL_COORDS.read_text(encoding="utf-8"))


def exportar_solicitud_pdf(datos: dict) -> bytes:
    """Inserta los datos sobre el PDF de fondo del formulario real."""

    def g(k: str) -> str:
        return (datos.get(k) or "").strip()

    try:
        monto = float(str(datos.get("monto_total") or 0).replace(",", ""))
    except Exception:
        monto = 0.0

    fields = {
        "I10": g("empresa"),
        "F14": g("sucursal"),
        "T14": g("fecha_proceso") or date.today().strftime("%d/%m/%Y"),
        "F16": g("centro_costos"),
        "T16": g("direccion"),
        "G19": g("proveedor_nombre"),
        "G21": g("motivo_pago"),
        "G26": g("folio_cfdi"),
        "P26": g("notas_credito"),
        "G33": g("importe_letra"),
        "S33": f"$ {monto:,.2f}" if monto else "",
        "C37": g("banco"),
        "G37": g("clabe"),
        "S37": g("no_cuenta"),
        "G39": g("observaciones"),
        "G49": g("mes_presupuesto"),
        "S49": g("mes_pago"),
        "G52": g("centro_costos"),
        "B70": g("analista_nombre"),
        "G70": g("gerente_nombre"),
        "C83": g("visto_bno"),
        "G83": g("depto_finanzas"),
        "O83": g("dir_financiera"),
        "T83": g("dir_general"),
    }

    coords = _load_coords()
    doc = fitz.open(str(BG_PDF))
    page = doc[0]

    for cell_id, text in fields.items():
        if not text or cell_id not in coords:
            continue
        pos = coords[cell_id]
        # Tamaño real de fuente derivado de la altura del bbox de calibración
        h = pos["y1"] - pos["y0"]
        sz = max(5.0, round(h / 0.91, 1))
        # y1 del marcador (sin descendentes) ≈ línea base del texto
        point = fitz.Point(pos["x0"], pos["y1"])
        page.insert_text(point, text, fontname="helv", fontsize=sz, color=(0, 0, 0))

    return doc.tobytes()


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
