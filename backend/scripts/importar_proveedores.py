"""
Importa todos los proveedores desde el Excel maestro a Supabase.
Fuente: SOLICITUD DE PAGO - OK (SIMULTANEO) 12.xlsm  →  hoja BASE
"""
import os
import sys
import win32com.client
import psycopg

EXCEL_PATH = (
    r"c:\Users\Analista de sistemas\OneDrive - SELECT SHOP MB SA DE CV"
    r"\New era\SOLICITUD DE PAGO - OK (SIMULTANEO) 12.xlsm"
)
HOJA = "BASE"


def leer_excel():
    xl = win32com.client.Dispatch("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    wb = xl.Workbooks.Open(EXCEL_PATH)
    ws = wb.Sheets(HOJA)
    rows = ws.UsedRange.Rows.Count

    proveedores = []
    for r in range(2, rows + 1):
        nombre = ws.Cells(r, 1).Text.strip()
        beneficiario = ws.Cells(r, 2).Text.strip()
        banco = ws.Cells(r, 3).Text.strip()
        clabe = ws.Cells(r, 4).Text.strip()
        no_cuenta = ws.Cells(r, 5).Text.strip()
        moneda = ws.Cells(r, 6).Text.strip() or "MXN"

        if not nombre:
            continue

        # Limpiar prefijos de formato (ej. "01-", "07-") que no son parte de CLABE real
        # Solo si el valor parece ser CLABE real (18 dígitos)
        clabe_clean = clabe.replace("-", "").replace(" ", "")
        if len(clabe_clean) == 18 and clabe_clean.isdigit():
            clabe = clabe_clean
        no_cuenta_clean = no_cuenta.replace("-", "").replace(" ", "")
        if len(no_cuenta_clean) <= 12 and no_cuenta_clean.isdigit():
            no_cuenta = no_cuenta_clean

        proveedores.append({
            "nombre": nombre,
            "beneficiario": beneficiario or nombre,
            "banco": banco,
            "clabe": clabe,
            "no_cuenta": no_cuenta,
            "moneda": moneda,
        })

    wb.Close(False)
    xl.Quit()
    return proveedores


def upsert_proveedores(proveedores: list[dict], db_url: str):
    insertados = 0
    actualizados = 0

    with psycopg.connect(db_url) as conn:
        for p in proveedores:
            existing = conn.execute(
                "SELECT id, banco, clabe, no_cuenta FROM proveedores WHERE nombre=%s",
                (p["nombre"],),
            ).fetchone()

            if existing:
                conn.execute(
                    """UPDATE proveedores
                       SET beneficiario = %s,
                           banco        = COALESCE(NULLIF(%s,''), banco),
                           clabe        = COALESCE(NULLIF(%s,''), clabe),
                           no_cuenta    = COALESCE(NULLIF(%s,''), no_cuenta),
                           moneda       = COALESCE(NULLIF(%s,''), moneda)
                       WHERE nombre = %s""",
                    (
                        p["beneficiario"],
                        p["banco"], p["clabe"], p["no_cuenta"], p["moneda"],
                        p["nombre"],
                    ),
                )
                actualizados += 1
            else:
                conn.execute(
                    """INSERT INTO proveedores (nombre, beneficiario, banco, clabe, no_cuenta, moneda)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (
                        p["nombre"], p["beneficiario"], p["banco"],
                        p["clabe"], p["no_cuenta"], p["moneda"],
                    ),
                )
                insertados += 1

        conn.commit()

    return insertados, actualizados


if __name__ == "__main__":
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL no configurada")
        sys.exit(1)

    print("Leyendo Excel...")
    proveedores = leer_excel()
    print(f"  {len(proveedores)} proveedores encontrados en el Excel")

    print("Sincronizando con Supabase...")
    ins, upd = upsert_proveedores(proveedores, db_url)
    print(f"  Insertados: {ins}")
    print(f"  Actualizados: {upd}")
    print("Listo.")
