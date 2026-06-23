"""
exportar.py — generación de documentos.

Solicitud de Pago: llena el template Excel real con openpyxl,
convierte a PDF con LibreOffice headless (Render/Linux) o LibreOffice
para Windows en local.
"""
from __future__ import annotations
import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from datetime import date

import openpyxl

TEMPLATE = Path(__file__).resolve().parents[2] / "assets" / "solicitud_template.xlsx"


def _libreoffice_bin() -> str:
    candidates = [
        "libreoffice",
        "soffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for c in candidates:
        if shutil.which(c) or (os.path.isabs(c) and os.path.exists(c)):
            return c
    raise RuntimeError(
        "LibreOffice no encontrado. "
        "En Render: instalar con apt-get install libreoffice-calc. "
        "En Windows: instalar LibreOffice desde libreoffice.org"
    )


def exportar_solicitud_pdf(datos: dict) -> bytes:
    """Llena el template .xlsx con los datos y devuelve el PDF como bytes."""

    def g(k: str) -> str:
        return (datos.get(k) or "").strip()

    try:
        monto = float(str(datos.get("monto_total") or 0).replace(",", ""))
    except Exception:
        monto = 0.0

    wb = openpyxl.load_workbook(str(TEMPLATE))
    ws = wb["Solicitud de pago"]

    # ── Datos principales ─────────────────────────────────────────────
    ws["I10"] = g("empresa")
    ws["F14"] = g("sucursal")
    ws["T14"] = g("fecha_proceso") or date.today().strftime("%d/%m/%Y")
    ws["F16"] = g("centro_costos")
    ws["T16"] = g("direccion")
    ws["G19"] = g("proveedor_nombre")
    ws["G21"] = g("motivo_pago")
    ws["G26"] = g("folio_cfdi")
    ws["Q26"] = g("notas_credito")

    # Importe: letra (G33) y número (S33 — mantiene formato moneda del template)
    ws["G33"] = g("importe_letra")
    ws["S33"] = monto if monto else None

    # Banco / CLABE / No. de cuenta
    ws["C37"] = g("banco")
    ws["G37"] = g("clabe")
    ws["S37"] = g("no_cuenta")

    ws["G39"] = g("observaciones")

    # Exclusivo finanzas
    ws["G49"] = g("mes_presupuesto")
    ws["S49"] = g("mes_pago")
    ws["G52"] = g("centro_costos")     # CC Finanzas = mismo CC

    # Firmas
    ws["B70"] = g("analista_nombre")
    ws["G70"] = g("gerente_nombre")
    ws["C83"] = g("visto_bno")
    ws["G83"] = g("depto_finanzas")
    ws["O83"] = g("dir_financiera")
    ws["T83"] = g("dir_general")

    # ── Guardar xlsx temporal ─────────────────────────────────────────
    tmp_xlsx = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False).name
    wb.save(tmp_xlsx)

    # ── Convertir a PDF con LibreOffice ───────────────────────────────
    tmp_dir = tempfile.mkdtemp()
    try:
        subprocess.run(
            [_libreoffice_bin(), "--headless", "--norestore",
             "--convert-to", "pdf", "--outdir", tmp_dir, tmp_xlsx],
            check=True,
            capture_output=True,
            timeout=90,
        )
        pdf_name = os.path.splitext(os.path.basename(tmp_xlsx))[0] + ".pdf"
        pdf_path = os.path.join(tmp_dir, pdf_name)
        with open(pdf_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp_xlsx)
        except OSError:
            pass
        shutil.rmtree(tmp_dir, ignore_errors=True)


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
