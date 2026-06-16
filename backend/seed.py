"""
Seed de datos reales del Grupo Marcovich para Supabase Postgres.
Portado de v60/database.py::seed_datos_fijos (mismos datos).

Idempotente: si la tabla `proveedores` ya tiene filas, no hace nada.

Uso:
    cd backend
    # con DATABASE_URL en el entorno o en ../.env
    .venv/Scripts/python seed.py
"""
from __future__ import annotations
import psycopg
from app.config import get_settings

EMP_MAP = {
    "01. SELECT SHOP MB": "SELECT SHOP MB SA DE CV",
    "02. ENFERMERAS UNIDAS PLUS": "ENFERMERAS UNIDAS PLUS SA DE V",
    "03. BH BE HEALTHY": "BH. BE HEALTHY COMERCIALIZADORA SA DE CV",
    "04. BH SOLAR": "BH SOLAR SA DE CV",
    "05. SM DISTRIBUIDORA DIGITAL": "SM DISTRIBUIDORA DIGITAL SA DE CV",
    "06. COMERCIALIZADORA DE MARCAS JSB": "COMERCIALIZADORA DE MARCAS JSB SA DE CV",
    "07. MB COMERCIALIZADORA EN LINEA": "MB COMERCIALIZADORA EN LINEA SA DE CV",
    "08. COMERCIALIZADORA ONLINE NH": "COMERCIALIZADORA ONLINE NH SA DE CV",
    "11. BLOOM BLUSH": "BLOOM & BLUSH SA DE CV",
    "12. ALEAGARAT": "ALEGARAT SA DE CV",
    "91. MOSAIC CARE & HEALTH": "MOSAIC CARE & HEALTH SA DE CV",
    "92. EISHEL": "INMOBILIARIA EISHEL SA DE CV",
}
SUC_MAP = {
    "POLANCO PISO 13": "CORPORATIVO POLANCO PISO 13",
    "POLANCO PISO 16": "CORPORATIVO POLANCO PISO 16",
    "T. POLANCO": "CORPORATIVO POLANCO PISO 13",
    "MW MED SUPPLY": "CORPORATIVO POLANCO PISO 13",
}


def norm_emp(cod):
    return EMP_MAP.get(str(cod).strip(), str(cod).strip())


def norm_suc(s):
    s = str(s).strip() if s else ""
    return SUC_MAP.get(s, s)


BANCOS = [
    ("BBVA", "012"), ("BANAMEX", "002"), ("BANORTE", "072"), ("HSBC", "021"),
    ("SANTANDER", "014"), ("SCOTIABANK", "044"), ("INBURSA", "036"),
    ("BAJIO", "030"), ("STP", "646"), ("AZTECA", "127"), ("BANREGIO", "058"),
    ("MULTIVA", "132"), ("AFIRME", "062"), ("BANCOPPEL", "137"),
    ("CITIBANAMEX", "002"), ("MIFEL", "042"), ("FONDEADORA", "699"),
]

PROVS = [
    ("TELEFONOS DE MEXICO SAB DE CV", "BBVA", ""),
    ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV", "BBVA", ""),
    ("RADIOMOVIL DIPSA SA DE CV", "BBVA", ""),
    ("BICENTEL", "BBVA", ""), ("IZZI NEGOCIOS", "BBVA", ""),
    ("PUBLIC VALUE", "BBVA", ""), ("DE LAGE LANDEN", "BBVA", ""),
    ("DLL LEASING", "BBVA", ""),
    ("CFE COMISION FEDERAL DE ELECTRICIDAD", "BBVA", ""),
]

EMPS = [
    ("SELECT SHOP MB SA DE CV", "CORPORATIVO POLANCO PISO 13", "ADMINISTRACION", "ADMINISTRACION"),
    ("SELECT SHOP MB SA DE CV", "CORPORATIVO POLANCO PISO 16", "ADMINISTRACION", "ADMINISTRACION"),
    ("SELECT SHOP MB SA DE CV", "TEPOTZOTLAN II", "LOGISTICA", "LOGISTICA"),
    ("ENFERMERAS UNIDAS PLUS SA DE V", "CORPORATIVO POLANCO PISO 13", "ADMINISTRACION", "ADMINISTRACION"),
    ("ENFERMERAS UNIDAS PLUS SA DE V", "IZTAPALAPA", "LOGISTICA", "LOGISTICA"),
    ("ENFERMERAS UNIDAS PLUS SA DE V", "T. CUERNAVACA", "TIENDAS", "TIENDAS"),
    ("ENFERMERAS UNIDAS PLUS SA DE V", "T. ARAGON", "TIENDAS", "TIENDAS"),
    ("BH. BE HEALTHY COMERCIALIZADORA SA DE CV", "CORPORATIVO POLANCO PISO 13", "ADMINISTRACION", "ADMINISTRACION"),
    ("BH SOLAR SA DE CV", "CORPORATIVO POLANCO PISO 13", "LOGISTICA", "LOGISTICA"),
    ("SM DISTRIBUIDORA DIGITAL SA DE CV", "CORPORATIVO POLANCO PISO 13", "ADMINISTRACION", "ADMINISTRACION"),
    ("COMERCIALIZADORA DE MARCAS JSB SA DE CV", "CORPORATIVO POLANCO PISO 13", "ADMINISTRACION", "ADMINISTRACION"),
    ("COMERCIALIZADORA DE MARCAS JSB SA DE CV", "TEPOTZOTLAN II", "LOGISTICA", "LOGISTICA"),
    ("MB COMERCIALIZADORA EN LINEA SA DE CV", "CORPORATIVO POLANCO PISO 13", "ADMINISTRACION", "ADMINISTRACION"),
    ("COMERCIALIZADORA ONLINE NH SA DE CV", "CORPORATIVO POLANCO PISO 13", "ADMINISTRACION", "ADMINISTRACION"),
    ("BLOOM & BLUSH SA DE CV", "TEPOTZOTLAN III", "LOGISTICA", "LOGISTICA"),
    ("BLOOM & BLUSH SA DE CV", "CORPORATIVO POLANCO PISO 13", "FINANZAS", "FINANZAS"),
    ("ALEGARAT SA DE CV", "CORPORATIVO POLANCO PISO 13", "FINANZAS", "FINANZAS"),
    ("INMOBILIARIA EISHEL SA DE CV", "CORPORATIVO POLANCO PISO 13", "ADMINISTRACION", "ADMINISTRACION"),
    ("MOSAIC CARE & HEALTH SA DE CV", "CORPORATIVO POLANCO PISO 13", "ADMINISTRACION", "ADMINISTRACION"),
    ("MW MED SUPPLY MEDICAL SC PRL DE CV", "CORPORATIVO POLANCO PISO 13", "ADMINISTRACION", "ADMINISTRACION"),
    ("GOLDEN YEARS MANAGEMENT SA DE CV", "CORPORATIVO POLANCO PISO 13", "ADMINISTRACION", "ADMINISTRACION"),
]

# prov, cuenta, concepto, monto, emp_cod, suc, cc, dia, pag_abr, pag_may
ROWS = [
    ("TELEFONOS DE MEXICO SAB DE CV", "5516683541", "TELEFONIA E INTERNET", 336.9, "07. MB COMERCIALIZADORA EN LINEA", "POLANCO PISO 13", "ADMINISTRACION", 1, True, True),
    ("TELEFONOS DE MEXICO SAB DE CV", "5516683579", "TELEFONIA E INTERNET", 798.0, "02. ENFERMERAS UNIDAS PLUS", "MW MED SUPPLY", "", 1, True, True),
    ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV", "0200660076", "TELEFONIA E INTERNET", 766.38, "01. SELECT SHOP MB", "TEPOTZOTLAN II", "LOGISTICA", 4, False, True),
    ("PUBLIC VALUE", "MANTENIMIENTO ERP", "SERVICIO ERP", 139200.0, "01. SELECT SHOP MB", "T. POLANCO", "FINANZAS", 4, None, True),
    ("TELEFONOS DE MEXICO SAB DE CV", "5552725727", "TELEFONIA E INTERNET", 336.9, "03. BH BE HEALTHY", "POLANCO PISO 13", "ADMINISTRACION", 6, False, True),
    ("TELEFONOS DE MEXICO SAB DE CV", "5556693389", "TELEFONIA E INTERNET", 198.0, "92. EISHEL", "POLANCO PISO 13", "ADMINISTRACION", 6, True, True),
    ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV", "0200707972", "TELEFONIA E INTERNET", 588.83, "03. BH BE HEALTHY", "POLANCO PISO 13", "ADMINISTRACION", 7, False, True),
    ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV", "0200723031", "TELEFONIA E INTERNET", 1723.27, "01. SELECT SHOP MB", "POLANCO PISO 13", "ADMINISTRACION", 7, False, True),
    ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV", "0200774234", "TELEFONIA E INTERNET", 4525.86, "01. SELECT SHOP MB", "TEPOTZOTLAN II", "LOGISTICA", 7, False, True),
    ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV", "0200774235", "TELEFONIA E INTERNET", 4525.86, "01. SELECT SHOP MB", "TEPOTZOTLAN II", "LOGISTICA", 7, False, True),
    ("DE LAGE LANDEN", "009-0036157-000", "ARRENDAMIENTO", 24247.22, "01. SELECT SHOP MB", "T. POLANCO", "FINANZAS", 8, None, True),
    ("DLL LEASING", "023-0230311-000", "ARRENDAMIENTO", 15228.91, "01. SELECT SHOP MB", "T. POLANCO", "FINANZAS", 8, None, True),
    ("DLL LEASING", "023-0230033-000", "ARRENDAMIENTO", 23116.88, "01. SELECT SHOP MB", "T. POLANCO", "FINANZAS", 8, None, True),
    ("DLL LEASING", "023-0230140-000", "ARRENDAMIENTO", 28726.29, "01. SELECT SHOP MB", "T. POLANCO", "FINANZAS", 8, None, True),
    ("TELEFONOS DE MEXICO SAB DE CV", "5550872370", "TELEFONIA E INTERNET", 336.9, "01. SELECT SHOP MB", "POLANCO PISO 13", "ADMINISTRACION", 10, True, True),
    ("TELEFONOS DE MEXICO SAB DE CV", "5556871130", "TELEFONIA E INTERNET", 336.9, "02. ENFERMERAS UNIDAS PLUS", "POLANCO PISO 13", "ADMINISTRACION", 11, True, True),
    ("TELEFONOS DE MEXICO SAB DE CV", "5591293910", "TELEFONIA E INTERNET", 423.1, "08. COMERCIALIZADORA ONLINE NH", "POLANCO PISO 13", "ADMINISTRACION", 11, False, True),
    ("TELEFONOS DE MEXICO SAB DE CV", "5552551893", "TELEFONIA E INTERNET", 423.1, "05. SM DISTRIBUIDORA DIGITAL", "POLANCO PISO 13", "ADMINISTRACION", 12, True, True),
    ("TELEFONOS DE MEXICO SAB DE CV", "CTA MAESTRA 0F06717", "CUENTA MAESTRA TELMEX", 4681.93, "02. ENFERMERAS UNIDAS PLUS", "POLANCO PISO 13", "FINANZAS", 15, True, None),
    ("TELEFONOS DE MEXICO SAB DE CV", "CTA MAESTRA 0F58191", "CUENTA MAESTRA TELMEX BH", 507.53, "03. BH BE HEALTHY", "POLANCO PISO 13", "FINANZAS", 15, True, None),
    ("IZZI NEGOCIOS", "48105784", "INTERNET IZZI", 439.0, "12. ALEAGARAT", "POLANCO PISO 13", "FINANZAS", 15, True, None),
    ("TELEFONOS DE MEXICO SAB DE CV", "5552039579", "TELEFONIA E INTERNET", 478.55, "02. ENFERMERAS UNIDAS PLUS", "T. POLANCO", "TIENDAS", 16, True, None),
    ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV", "0200835275", "TELEFONIA E INTERNET", 2280.0, "01. SELECT SHOP MB", "POLANCO PISO 13", "ADMINISTRACION", 16, True, None),
    ("TELEFONOS DE MEXICO SAB DE CV", "5556850241", "TELEFONIA E INTERNET", 463.55, "02. ENFERMERAS UNIDAS PLUS", "IZTAPALAPA", "LOGISTICA", 17, True, None),
    ("TELEFONOS DE MEXICO SAB DE CV", "5556854768", "TELEFONIA E INTERNET", 463.55, "02. ENFERMERAS UNIDAS PLUS", "IZTAPALAPA", "LOGISTICA", 17, True, None),
    ("TELEFONOS DE MEXICO SAB DE CV", "5556855148", "TELEFONIA E INTERNET", 1145.22, "02. ENFERMERAS UNIDAS PLUS", "IZTAPALAPA", "LOGISTICA", 17, True, None),
    ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV", "0105751751", "TELEFONIA E INTERNET", 800.0, "06. COMERCIALIZADORA DE MARCAS JSB", "POLANCO PISO 13", "ADMINISTRACION", 18, True, False),
    ("IZZI NEGOCIOS", "INTERNET MARZO", "INTERNET IZZI", 590.0, "11. BLOOM BLUSH", "POLANCO PISO 13", "FINANZAS", 19, True, None),
    ("BICENTEL", "MICROSOFT", "LICENCIAS", 2187.34, "01. SELECT SHOP MB", "", "FINANZAS", 20, True, True),
    ("TELEFONOS DE MEXICO SAB DE CV", "5524773274", "TELEFONIA E INTERNET", 423.1, "11. BLOOM BLUSH", "TEPOTZOTLAN III", "LOGISTICA", 21, True, None),
    ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV", "0200835961", "TELEFONIA E INTERNET", 2280.0, "11. BLOOM BLUSH", "TEPOTZOTLAN III", "LOGISTICA", 22, True, None),
    ("TELEFONOS DE MEXICO SAB DE CV", "5559100988", "TELEFONIA E INTERNET", 336.9, "04. BH SOLAR", "POLANCO PISO 13", "LOGISTICA", 23, True, None),
    ("TELEFONOS DE MEXICO SAB DE CV", "5511008625", "TELEFONIA E INTERNET", 423.1, "06. COMERCIALIZADORA DE MARCAS JSB", "TEPOTZOTLAN II", "LOGISTICA", 24, True, None),
    ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV", "0200804119", "TELEFONIA E INTERNET", 2373.96, "11. BLOOM BLUSH", "TEPOTZOTLAN III", "LOGISTICA", 26, True, False),
    ("TELEFONOS DE MEXICO SAB DE CV", "5522373301", "TELEFONIA E INTERNET", 389.0, "02. ENFERMERAS UNIDAS PLUS", "", "", 27, True, None),
    ("TELEFONOS DE MEXICO SAB DE CV", "5550880352", "TELEFONIA E INTERNET", 236.0, "06. COMERCIALIZADORA DE MARCAS JSB", "", "", 27, True, None),
    ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV", "0200666296", "TELEFONIA E INTERNET", 6000.0, "01. SELECT SHOP MB", "TEPOTZOTLAN II", "LOGISTICA", 28, True, None),
    ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV", "0200666297", "TELEFONIA E INTERNET", 6000.0, "01. SELECT SHOP MB", "TEPOTZOTLAN II", "LOGISTICA", 28, True, None),
    ("TELEFONOS DE MEXICO SAB DE CV", "5556854664", "TELEFONIA E INTERNET", 1145.22, "02. ENFERMERAS UNIDAS PLUS", "IZTAPALAPA", "LOGISTICA", 28, True, None),
    ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV", "0200741885", "TELEFONIA E INTERNET", 1637.07, "06. COMERCIALIZADORA DE MARCAS JSB", "TEPOTZOTLAN II", "LOGISTICA", 29, True, None),
    ("BICENTEL", "TODO INCLUIDO UC", "TELEFONIA E INTERNET", 45753.07, "01. SELECT SHOP MB", "", "FINANZAS", 30, True, True),
    ("TELEFONOS DE MEXICO SAB DE CV", "5522373301 B", "TELEFONIA E INTERNET", 328.44, "06. COMERCIALIZADORA DE MARCAS JSB", "TEPOTZOTLAN II", "LOGISTICA", 30, True, None),
    ("TELEFONOS DE MEXICO SAB DE CV", "5550880292", "TELEFONIA E INTERNET", 198.0, "91. MOSAIC CARE & HEALTH", "POLANCO PISO 13", "ADMINISTRACION", 30, True, None),
    ("TELEFONOS DE MEXICO SAB DE CV", "7771001628", "TELEFONIA E INTERNET", 463.55, "02. ENFERMERAS UNIDAS PLUS", "T. CUERNAVACA", "TIENDAS", 28, True, False),
    ("TELEFONOS DE MEXICO SAB DE CV", "5557608176", "TELEFONIA E INTERNET", 463.55, "02. ENFERMERAS UNIDAS PLUS", "T. ARAGON", "TIENDAS", 28, True, None),
]


def seed(conn) -> None:
    cur = conn.cursor()

    n = cur.execute("SELECT COUNT(*) AS n FROM proveedores").fetchone()[0]
    if n and n > 0:
        print(f"Seed omitido: proveedores ya tiene {n} filas.")
        return

    for nom, pref in BANCOS:
        cur.execute(
            "INSERT INTO bancos (nombre,prefijo_clabe) VALUES (%s,%s) ON CONFLICT (nombre) DO NOTHING",
            (nom, pref),
        )

    for nom, banco, clabe in PROVS:
        cur.execute(
            "INSERT INTO proveedores (nombre,banco,clabe) VALUES (%s,%s,%s)",
            (nom, banco, clabe),
        )

    for emp, suc, cc, dr in EMPS:
        cur.execute(
            "INSERT INTO empresas_cc (empresa,sucursal,centro_costos,direccion) VALUES (%s,%s,%s,%s)",
            (emp, suc, cc, dr),
        )

    def get_prov_id(nombre):
        r = cur.execute("SELECT id FROM proveedores WHERE nombre=%s", (nombre,)).fetchone()
        return r[0] if r else None

    def get_emp_id(emp_cod):
        nombre = norm_emp(emp_cod)
        r = cur.execute("SELECT id FROM empresas_cc WHERE empresa=%s LIMIT 1", (nombre,)).fetchone()
        return r[0] if r else None

    n_srv = n_pag = 0
    for prov_nom, cuenta, concepto, monto, emp_cod, suc, cc, dia, pag_abr, pag_may in ROWS:
        prov_id = get_prov_id(prov_nom)
        emp_id = get_emp_id(emp_cod)
        emp_nom = norm_emp(emp_cod)
        suc_norm = norm_suc(suc) if suc else ""
        desc = f"{prov_nom[:25]} {cuenta}"
        srv_id = cur.execute(
            """INSERT INTO servicios_recurrentes
               (proveedor_id,empresa_cc_id,descripcion,no_cuenta_servicio,
                dia_limite,monto_base,iva,activo)
               VALUES (%s,%s,%s,%s,%s,%s,%s,true) RETURNING id""",
            (prov_id, emp_id, desc, cuenta, dia, monto, 0),
        ).fetchone()[0]
        n_srv += 1

        for mes_num, mes_nom, pagado in [(4, "Abril", pag_abr), (5, "Mayo", pag_may)]:
            if pagado is None:
                continue
            estatus = "PAGADO" if pagado else "PENDIENTE"
            dia_real = min(dia, 28) if dia else 15
            fecha_proc = f"2026-{mes_num:02d}-{dia_real:02d}"
            motivo = f"SERV {cuenta} {mes_nom.upper()} 2026"
            cur.execute(
                """INSERT INTO pagos
                   (servicio_id,proveedor_nombre,empresa,sucursal,
                    centro_costos,motivo_pago,monto_total,importe_letra,
                    banco,clabe,no_cuenta,observaciones,
                    mes_presupuesto,mes_pago,mes,anio,
                    estatus,fecha_proceso,analista_nombre,gerente_nombre)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (srv_id, prov_nom, emp_nom, suc_norm, cc,
                 motivo, monto, "", "BBVA", "", cuenta, "",
                 mes_nom, mes_nom, mes_num, 2026,
                 estatus, fecha_proc, "", ""),
            )
            n_pag += 1

    conn.commit()
    print(f"Seed OK: {len(BANCOS)} bancos, {len(PROVS)} proveedores, "
          f"{len(EMPS)} empresas, {n_srv} servicios, {n_pag} pagos.")


def main():
    dsn = get_settings().database_url
    if not dsn:
        raise SystemExit("DATABASE_URL no configurada (ponla en ../.env o el entorno).")
    with psycopg.connect(dsn) as conn:
        seed(conn)


if __name__ == "__main__":
    main()
