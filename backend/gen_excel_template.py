"""
gen_excel_template.py — genera solicitud_template.xlsx
Corre UNA SOLA VEZ en Windows.
Toma el .xlsm real, borra hojas auxiliares, limpia celdas de datos y guarda
como .xlsx en backend/assets/ para que la app lo llene con openpyxl.
"""
import win32com.client as w32
import os, shutil

SRC = r'C:\Users\Analista de sistemas\OneDrive - SELECT SHOP MB SA DE CV\New era\SOLICITUD DE PAGO - OK (SIMULTANEO) 12.xlsm'
DST = r'C:\Users\Analista de sistemas\Documents\GestorPagosIT_v60\backend\assets\solicitud_template.xlsx'

TMP = r'C:\Users\Analista de sistemas\Desktop\solicitud_template_tmp.xlsx'

xl = w32.Dispatch('Excel.Application')
xl.DisplayAlerts = False

wb = xl.Workbooks.Open(os.path.abspath(SRC))

# ── Borrar hojas auxiliares (mantener SOLO 'Solicitud de pago') ─────
to_delete = []
for i in range(wb.Sheets.Count, 0, -1):
    ws = wb.Sheets(i)
    if ws.Name != 'Solicitud de pago':
        to_delete.append(ws)
for ws in to_delete:
    ws.Delete()

print(f"Hojas restantes: {[wb.Sheets(i).Name for i in range(1, wb.Sheets.Count+1)]}")

ws = wb.Sheets(1)

# ── Celdas de DATOS que la app llenará ──────────────────────────────
DATA_CELLS = [
    "C8",   # logo empresa (fórmula que referencia Master — borramos)
    "I10",  # empresa nombre
    "F14",  # sucursal
    "T14",  # fecha de solicitud
    "F16",  # centro de costos
    "T16",  # dirección
    "G19",  # beneficiario (proveedor)
    "G21",  # motivo de pago
    "G26",  # folio CFDI
    "Q26",  # nota de crédito
    "G33",  # importe en letra
    "S33",  # importe en número
    "C37",  # banco
    "G37",  # CLABE
    "S37",  # no. de cuenta
    "G39",  # observaciones
    "G49",  # mes presupuesto
    "S49",  # mes pago
    "G52",  # CC finanzas
    "B70",  # analista nombre
    "G70",  # gerente nombre
    "C83",  # vo.bo.
    "G83",  # depto finanzas
    "O83",  # dirección financiera
    "T83",  # dirección general
]

for addr in DATA_CELLS:
    try:
        ws.Range(addr).MergeArea.ClearContents()
        print(f"  Cleared {addr}")
    except Exception as e:
        print(f"  Warning {addr}: {e}")

# ── Configurar página (ya está fit-to-1-page) ────────────────────────
ps = ws.PageSetup
ps.Zoom = False
ps.FitToPagesWide = 1
ps.FitToPagesTall = 1
ps.Orientation = 1   # xlPortrait

# ── Guardar como .xlsx (sin VBA) ─────────────────────────────────────
wb.SaveAs(TMP, FileFormat=51)  # 51 = xlOpenXMLWorkbook (.xlsx)
wb.Close(False)
xl.Quit()

shutil.copy2(TMP, DST)
os.remove(TMP)

print(f"\nTemplate guardado: {DST}")
print(f"Tamaño: {os.path.getsize(DST)} bytes")
print("DONE")
