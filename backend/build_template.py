"""
Genera el nuevo JPG template desde formato.xlsx:
1. Abre el Excel
2. Borra celdas de datos y nombres de firmantes
3. Exporta a PDF (fit 1 página)
4. Convierte a JPG 1275x1650px (150 DPI) → reemplaza formato2_page-0001.jpg
"""
import win32com.client as w32
import fitz
import os, shutil

SRC     = r'C:\Users\Analista de sistemas\Documents\formato.xlsx'
TMP     = r'C:\Users\Analista de sistemas\Desktop\formato_blank.xlsx'
PDF_TMP = r'C:\Users\Analista de sistemas\Desktop\formato_blank.pdf'
JPG_OUT = r'C:\Users\Analista de sistemas\Documents\GestorPagosIT_v60\backend\assets\logos\formato2_page-0001.jpg'

shutil.copy2(SRC, TMP)

xl = w32.Dispatch('Excel.Application')
xl.DisplayAlerts = False
wb = xl.Workbooks.Open(os.path.abspath(TMP))
ws = wb.Sheets(1)

# ── Limpiar CELDAS DE DATOS (mantener etiquetas y estructura) ──────────
DATA_CELLS = [
    "E7",   # sucursal
    "S7",   # fecha
    "E9",   # centro de costos
    "S9",   # dirección
    "F12",  # beneficiario
    "F14",  # motivo de pago
    "F19",  # folio CFDI
    "O19",  # nota de crédito
    "F25",  # importe en letra
    "R25",  # importe en número
    "B30",  # banco
    "F30",  # clabe
    "R30",  # no. cuenta
    "F32",  # observaciones
    "F35",  # forma de pago solicitada
    "F42",  # mes presupuesto
    "R42",  # mes pago
    "F45",  # CC finanzas
    # Nombres de firmantes (los dibujamos programáticamente)
    "A63",  # analista nombre
    "F63",  # gerente nombre
    "B76",  # vo.bo.
    "F76",  # depto finanzas
    "N76",  # dirección financiera
    "S76",  # dirección general
    # Celdas extras que pudieran tener datos
    "F46",
    "R46",
    "F50",
    "F51",
]

for cell_addr in DATA_CELLS:
    try:
        ws.Range(cell_addr).MergeArea.ClearContents()
        print(f"  Cleared {cell_addr}")
    except Exception as e:
        try:
            ws.Range(cell_addr).ClearContents()
            print(f"  Cleared {cell_addr} (direct)")
        except Exception as e2:
            print(f"  Warning {cell_addr}: {e2}")

# ── Fit to 1 page ────────────────────────────────────────────────────
ps = ws.PageSetup
ps.Zoom = False
ps.FitToPagesWide = 1
ps.FitToPagesTall = 1
ps.Orientation = 1   # xlPortrait

wb.Save()
wb.ExportAsFixedFormat(0, PDF_TMP, Quality=0,
                       IncludeDocProperties=False,
                       IgnorePrintAreas=False)
print(f"PDF creado: {PDF_TMP} ({os.path.getsize(PDF_TMP)} bytes)")

wb.Close(False)
xl.Quit()

# ── PDF → JPG 1275x1650 px (150 DPI, letter) ─────────────────────────
doc = fitz.open(PDF_TMP)
page = doc[0]
pw, ph = page.rect.width, page.rect.height
print(f"Página PDF: {pw:.0f}x{ph:.0f}pts")

# 150 DPI: 612pt → 1275px  (zoom = 1275/612 = 2.0833...)
zoom = 1275.0 / pw
mat  = fitz.Matrix(zoom, zoom)
pix  = page.get_pixmap(matrix=mat, alpha=False)
pix.save(JPG_OUT)

print(f"JPG guardado: {JPG_OUT}")
print(f"Dimensiones: {pix.width}x{pix.height}px")
print(f"Tamaño: {os.path.getsize(JPG_OUT)} bytes")
doc.close()

print("DONE — nuevo template listo")
