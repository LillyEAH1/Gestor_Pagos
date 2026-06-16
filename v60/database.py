"""
database.py v25
BD SQLite — incluye tablas: proveedores, bancos, plantillas_observaciones,
empresas_cc, servicios_recurrentes, pagos.
"""
from __future__ import annotations
import sqlite3, re
from datetime import date
from pathlib import Path
from contextlib import contextmanager


class Database:
    def __init__(self, ruta_db: str):
        self.ruta = Path(ruta_db)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._inicializar()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.ruta, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _inicializar(self):
        with self._conn() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS proveedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                beneficiario TEXT,
                banco TEXT,
                clabe TEXT,
                no_cuenta TEXT,
                moneda TEXT DEFAULT 'MXN',
                creado_en TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS bancos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                prefijo_clabe TEXT,
                descripcion TEXT
            );
            CREATE TABLE IF NOT EXISTS plantillas_observaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proveedor_patron TEXT,
                template TEXT NOT NULL,
                descripcion TEXT,
                activo INTEGER DEFAULT 1,
                creado_en TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS empresas_cc (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa TEXT NOT NULL DEFAULT '',
                nom_corto TEXT,
                sucursal TEXT,
                centro_costos TEXT,
                direccion TEXT,
                tipo_gasto TEXT DEFAULT 'GASTO'
            );
            CREATE TABLE IF NOT EXISTS servicios_recurrentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proveedor_id INTEGER REFERENCES proveedores(id),
                empresa_cc_id INTEGER REFERENCES empresas_cc(id),
                descripcion TEXT,
                no_cuenta_servicio TEXT,
                tipo TEXT,
                monto_base REAL DEFAULT 0,
                iva REAL DEFAULT 0,
                dia_limite INTEGER,
                activo INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS pagos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                servicio_id INTEGER REFERENCES servicios_recurrentes(id),
                proveedor_nombre TEXT,
                empresa TEXT,
                sucursal TEXT,
                centro_costos TEXT,
                direccion TEXT,
                motivo_pago TEXT,
                folio_cfdi TEXT,
                notas_credito REAL DEFAULT 0,
                monto_total REAL DEFAULT 0,
                importe_letra TEXT,
                banco TEXT,
                clabe TEXT,
                no_cuenta TEXT,
                forma_pago TEXT,
                observaciones TEXT,
                mes_presupuesto TEXT,
                mes_pago TEXT,
                mes INTEGER,
                anio INTEGER,
                estatus TEXT DEFAULT 'PENDIENTE',
                fecha_proceso TEXT,
                pdf_ruta TEXT,
                analista_nombre TEXT,
                gerente_nombre TEXT,
                creado_en TEXT DEFAULT (datetime('now'))
            );
            """)
        # Migrar columnas nuevas si el DB es viejo
        self._migrar_columnas()
        self._auto_seed_if_empty()

    def _migrar_columnas(self):
        """Agrega columnas nuevas si el DB venía de versiones anteriores."""
        with self._conn() as c:
            cols_pagos = [r[1] for r in c.execute("PRAGMA table_info(pagos)").fetchall()]
            if "direccion" not in cols_pagos:
                c.execute("ALTER TABLE pagos ADD COLUMN direccion TEXT")
            if "analista_nombre" not in cols_pagos:
                c.execute("ALTER TABLE pagos ADD COLUMN analista_nombre TEXT")
            if "gerente_nombre" not in cols_pagos:
                c.execute("ALTER TABLE pagos ADD COLUMN gerente_nombre TEXT")
            # Verificar que existen las tablas nuevas
            tablas = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "bancos" not in tablas:
                c.execute("""CREATE TABLE bancos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL UNIQUE,
                    prefijo_clabe TEXT,
                    descripcion TEXT
                )""")
            if "plantillas_observaciones" not in tablas:
                c.execute("""CREATE TABLE plantillas_observaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proveedor_patron TEXT,
                    template TEXT NOT NULL,
                    descripcion TEXT,
                    activo INTEGER DEFAULT 1,
                    creado_en TEXT DEFAULT (datetime('now'))
                )""")

    def _auto_seed_if_empty(self):
        import sys
        with self._conn() as c:
            n = c.execute("SELECT COUNT(*) FROM proveedores").fetchone()[0]
            if n > 0:
                return
        try:
            if getattr(sys, '_MEIPASS', None):
                seed_path = Path(sys._MEIPASS) / "pagos.db"
            else:
                seed_path = Path(__file__).parent / "pagos.db"
            if not seed_path.exists() or str(seed_path) == str(self.ruta):
                return
            src = sqlite3.connect(seed_path)
            src.row_factory = sqlite3.Row
            with self._conn() as dst:
                for row in src.execute("SELECT * FROM proveedores"):
                    r = dict(row)
                    dst.execute(
                        "INSERT OR IGNORE INTO proveedores (nombre,beneficiario,banco,clabe,no_cuenta,moneda) VALUES (?,?,?,?,?,?)",
                        (r['nombre'], r.get('beneficiario',''), r.get('banco',''),
                         r.get('clabe',''), r.get('no_cuenta',''), r.get('moneda','MXN'))
                    )
                for row in src.execute("SELECT * FROM empresas_cc"):
                    r = dict(row)
                    dst.execute(
                        "INSERT OR IGNORE INTO empresas_cc (empresa,nom_corto,sucursal,centro_costos,direccion) VALUES (?,?,?,?,?)",
                        (r.get('empresa',''), r.get('nom_corto',''), r.get('sucursal',''),
                         r.get('centro_costos',''), r.get('direccion',''))
                    )
                try:
                    for row in src.execute("SELECT * FROM bancos"):
                        r = dict(row)
                        dst.execute(
                            "INSERT OR IGNORE INTO bancos (nombre,prefijo_clabe,descripcion) VALUES (?,?,?)",
                            (r['nombre'], r.get('prefijo_clabe',''), r.get('descripcion',''))
                        )
                except Exception: pass
                try:
                    for row in src.execute("SELECT * FROM plantillas_observaciones"):
                        r = dict(row)
                        dst.execute(
                            "INSERT OR IGNORE INTO plantillas_observaciones (proveedor_patron,template,descripcion) VALUES (?,?,?)",
                            (r.get('proveedor_patron',''), r['template'], r.get('descripcion',''))
                        )
                except Exception: pass
            src.close()
        except Exception:
            pass

    # ── Proveedores ────────────────────────────────────────────────────────
    def listar_proveedores(self) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM proveedores ORDER BY nombre").fetchall()]

    def get_proveedores(self) -> list[dict]:
        return self.listar_proveedores()

    def get_proveedor(self, nombre: str) -> dict | None:
        with self._conn() as c:
            r = c.execute(
                "SELECT * FROM proveedores WHERE UPPER(TRIM(nombre))=UPPER(TRIM(?))",
                (nombre,)).fetchone()
            return dict(r) if r else None

    def buscar_proveedor_por_nombre(self, nombre: str) -> dict | None:
        """Busca un proveedor por nombre (búsqueda parcial) y devuelve sus datos."""
        conn = self._conn()
        nombre_u = nombre.upper().strip()
        rows = conn.execute(
            "SELECT id, nombre, banco, clabe FROM proveedores WHERE UPPER(nombre) LIKE ? LIMIT 1",
            (f"%{nombre_u[:15]}%",)
        ).fetchall()
        if not rows: return None
        r = rows[0]
        return {"id": r[0], "nombre": r[1], "banco": r[2], "clabe": r[3]}

    def upsert_proveedor(self, datos: dict) -> int:
        with self._conn() as c:
            existente = c.execute(
                "SELECT id FROM proveedores WHERE UPPER(TRIM(nombre))=UPPER(TRIM(?))",
                (datos["nombre"],)).fetchone()
            if existente:
                c.execute("""UPDATE proveedores SET beneficiario=?,banco=?,clabe=?,
                             no_cuenta=?,moneda=? WHERE id=?""",
                          (datos.get("beneficiario",""), datos.get("banco",""),
                           datos.get("clabe",""), datos.get("no_cuenta",""),
                           datos.get("moneda","MXN"), existente["id"]))
                return existente["id"]
            else:
                cur = c.execute("""INSERT INTO proveedores
                    (nombre,beneficiario,banco,clabe,no_cuenta,moneda)
                    VALUES (?,?,?,?,?,?)""",
                    (datos["nombre"], datos.get("beneficiario",""),
                     datos.get("banco",""), datos.get("clabe",""),
                     datos.get("no_cuenta",""), datos.get("moneda","MXN")))
                return cur.lastrowid

    # ── Bancos ─────────────────────────────────────────────────────────────
    def listar_bancos(self) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM bancos ORDER BY nombre").fetchall()]

    def get_banco_por_nombre(self, nombre: str) -> dict | None:
        with self._conn() as c:
            r = c.execute(
                "SELECT * FROM bancos WHERE UPPER(TRIM(nombre))=UPPER(TRIM(?))",
                (nombre,)).fetchone()
            return dict(r) if r else None

    def get_banco_por_prefijo(self, clabe: str) -> str:
        """Dado los primeros 3 dígitos de una CLABE, devuelve el nombre del banco."""
        if not clabe or len(clabe) < 3:
            return ""
        prefijo = clabe[:3]
        with self._conn() as c:
            r = c.execute(
                "SELECT nombre FROM bancos WHERE prefijo_clabe=?",
                (prefijo,)).fetchone()
            return r["nombre"] if r else ""

    def upsert_banco(self, datos: dict) -> int:
        with self._conn() as c:
            existente = c.execute(
                "SELECT id FROM bancos WHERE UPPER(TRIM(nombre))=UPPER(TRIM(?))",
                (datos["nombre"],)).fetchone()
            if existente:
                c.execute("UPDATE bancos SET prefijo_clabe=?,descripcion=? WHERE id=?",
                          (datos.get("prefijo_clabe",""), datos.get("descripcion",""),
                           existente["id"]))
                return existente["id"]
            else:
                cur = c.execute(
                    "INSERT INTO bancos (nombre,prefijo_clabe,descripcion) VALUES (?,?,?)",
                    (datos["nombre"], datos.get("prefijo_clabe",""),
                     datos.get("descripcion","")))
                return cur.lastrowid

    def eliminar_banco(self, banco_id: int) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM bancos WHERE id=?", (banco_id,))

    # ── Plantillas de observaciones ────────────────────────────────────────
    def listar_plantillas(self) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM plantillas_observaciones WHERE activo=1 ORDER BY id"
            ).fetchall()]

    def get_plantilla_para_proveedor(self, nombre_proveedor: str) -> str:
        """Devuelve el template de observaciones para un proveedor dado."""
        nombre_upper = nombre_proveedor.upper()
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM plantillas_observaciones WHERE activo=1"
            ).fetchall()
        for row in rows:
            patron = str(row["proveedor_patron"] or "")
            for p in patron.split("|"):
                if p.strip() and p.strip() in nombre_upper:
                    return row["template"]
        return ""

    def upsert_plantilla(self, datos: dict) -> int:
        with self._conn() as c:
            if datos.get("id"):
                c.execute(
                    "UPDATE plantillas_observaciones SET proveedor_patron=?,template=?,descripcion=?,activo=? WHERE id=?",
                    (datos.get("proveedor_patron",""), datos["template"],
                     datos.get("descripcion",""), datos.get("activo",1), datos["id"]))
                return datos["id"]
            else:
                cur = c.execute(
                    "INSERT INTO plantillas_observaciones (proveedor_patron,template,descripcion) VALUES (?,?,?)",
                    (datos.get("proveedor_patron",""), datos["template"],
                     datos.get("descripcion","")))
                return cur.lastrowid

    def eliminar_plantilla(self, plantilla_id: int) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM plantillas_observaciones WHERE id=?", (plantilla_id,))

    # ── Pagos — CRUD ───────────────────────────────────────────────────────
    def crear_pago(self, datos: dict) -> int:
        campos = [
            "servicio_id","proveedor_nombre","empresa","sucursal","centro_costos","direccion",
            "motivo_pago","folio_cfdi","notas_credito","monto_total","importe_letra",
            "banco","clabe","no_cuenta","forma_pago","observaciones",
            "mes_presupuesto","mes_pago","mes","anio","estatus",
            "fecha_proceso","pdf_ruta","analista_nombre","gerente_nombre"
        ]
        vals = [datos.get(c) for c in campos]
        sql  = f"INSERT INTO pagos ({','.join(campos)}) VALUES ({','.join(['?']*len(campos))})"
        with self._conn() as c:
            cur = c.execute(sql, vals)
            return cur.lastrowid

    def get_pago(self, pago_id: int) -> dict | None:
        with self._conn() as c:
            r = c.execute("SELECT * FROM pagos WHERE id=?", (pago_id,)).fetchone()
            return dict(r) if r else None

    def actualizar_pago(self, pago_id: int, datos: dict) -> None:
        sets  = ", ".join(f"{k}=?" for k in datos)
        vals  = list(datos.values()) + [pago_id]
        with self._conn() as c:
            c.execute(f"UPDATE pagos SET {sets} WHERE id=?", vals)

    def actualizar_pdf(self, pago_id: int, ruta_pdf: str) -> None:
        self.actualizar_pago(pago_id, {"pdf_ruta": ruta_pdf})

    def eliminar_pago(self, pago_id: int) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM pagos WHERE id=?", (pago_id,))

    def get_pagos_mes(self, mes: int, anio: int) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM pagos WHERE mes=? AND anio=? ORDER BY creado_en DESC",
                (mes, anio)).fetchall()]

    def estado_cuenta_mes(self, mes: int, anio: int) -> dict:
        pagos = self.get_pagos_mes(mes, anio)
        pagados    = [p for p in pagos if p["estatus"] in ("PAGADO", "LISTO")]
        pendientes = [p for p in pagos if p["estatus"] == "PENDIENTE"]
        return {
            "mes": mes, "anio": anio,
            "pagados": pagados, "pendientes": pendientes,
            "total_pagado":    sum(p["monto_total"] or 0 for p in pagados),
            "total_pendiente": sum(p["monto_total"] or 0 for p in pendientes),
            "todos": pagos,
        }

    def buscar_pagos(self, query: str) -> list[dict]:
        q = f"%{query.upper()}%"
        with self._conn() as c:
            rows = c.execute("""
                SELECT * FROM pagos
                WHERE UPPER(proveedor_nombre) LIKE ?
                   OR UPPER(empresa)          LIKE ?
                   OR UPPER(motivo_pago)      LIKE ?
                   OR UPPER(observaciones)    LIKE ?
                   OR UPPER(folio_cfdi)       LIKE ?
                   OR UPPER(no_cuenta)        LIKE ?
                   OR UPPER(clabe)            LIKE ?
                ORDER BY creado_en DESC LIMIT 200
            """, (q,q,q,q,q,q,q)).fetchall()
            return [dict(r) for r in rows]

    # ── Servicios próximos ─────────────────────────────────────────────────
    def servicios_proximos(self, dias: int = 30) -> list[dict]:
        from datetime import timedelta
        hoy = date.today()
        mes, anio = hoy.month, hoy.year
        pagados_ids = {
            p["servicio_id"] for p in self.get_pagos_mes(mes, anio)
            if p["servicio_id"] and p["estatus"] in ("PAGADO","LISTO")
        }
        with self._conn() as c:
            servicios = [dict(r) for r in c.execute("""
                SELECT s.*, p.nombre as proveedor_nombre,
                       p.banco, p.clabe, p.no_cuenta,
                       e.empresa, e.sucursal, e.centro_costos, e.direccion
                FROM servicios_recurrentes s
                LEFT JOIN proveedores p ON s.proveedor_id=p.id
                LEFT JOIN empresas_cc e ON s.empresa_cc_id=e.id
                WHERE s.activo=1 AND s.dia_limite IS NOT NULL
            """).fetchall()]
        proximos = []
        for s in servicios:
            if s["id"] in pagados_ids: continue
            try:
                vence = date(anio, mes, int(s["dia_limite"]))
            except ValueError: continue
            delta = (vence - hoy).days
            if 0 <= delta <= dias:
                proximos.append({**s, "dias_para_vencer": delta, "fecha_limite": vence})
        return proximos

    def seed_datos_fijos(self):
        """
        Siembra datos reales de PagosIT.xlsx y grupo Marcovich.
        INSERT OR IGNORE — idempotente. Usa conexión directa sqlite3.
        """
        import sqlite3 as _sq3
        conn = _sq3.connect(self.ruta)
        conn.row_factory = _sq3.Row
        cur = conn.cursor()

        EMP_MAP = {
            "01. SELECT SHOP MB":              "SELECT SHOP MB SA DE CV",
            "02. ENFERMERAS UNIDAS PLUS":      "ENFERMERAS UNIDAS PLUS SA DE V",
            "03. BH BE HEALTHY":               "BH. BE HEALTHY COMERCIALIZADORA SA DE CV",
            "04. BH SOLAR":                    "BH SOLAR SA DE CV",
            "05. SM DISTRIBUIDORA DIGITAL":    "SM DISTRIBUIDORA DIGITAL SA DE CV",
            "06. COMERCIALIZADORA DE MARCAS JSB": "COMERCIALIZADORA DE MARCAS JSB SA DE CV",
            "07. MB COMERCIALIZADORA EN LINEA":"MB COMERCIALIZADORA EN LINEA SA DE CV",
            "08. COMERCIALIZADORA ONLINE NH":  "COMERCIALIZADORA ONLINE NH SA DE CV",
            "11. BLOOM BLUSH":                 "BLOOM & BLUSH SA DE CV",
            "12. ALEAGARAT":                   "ALEGARAT SA DE CV",
            "91. MOSAIC CARE & HEALTH":        "MOSAIC CARE & HEALTH SA DE CV",
            "92. EISHEL":                      "INMOBILIARIA EISHEL SA DE CV",
        }
        SUC_MAP = {
            "POLANCO PISO 13": "CORPORATIVO POLANCO PISO 13",
            "POLANCO PISO 16": "CORPORATIVO POLANCO PISO 16",
            "T. POLANCO":      "CORPORATIVO POLANCO PISO 13",
            "MW MED SUPPLY":   "CORPORATIVO POLANCO PISO 13",
        }

        def norm_emp(cod):
            return EMP_MAP.get(str(cod).strip(), str(cod).strip())

        def norm_suc(s):
            s = str(s).strip() if s else ""
            return SUC_MAP.get(s, s)

        def norm_dia(d):
            import re as _re
            m = _re.search(r"[0-9]+", str(d or ""))
            return int(m.group()) if m else 0

        def norm_monto(v):
            if v is None: return 0.0
            try: return float(str(v).replace(",","."))
            except: return 0.0

        def get_prov_id(nombre):
            r = cur.execute("SELECT id FROM proveedores WHERE nombre=?", (nombre,)).fetchone()
            return r[0] if r else None

        def get_emp_id(emp_cod):
            nombre = norm_emp(emp_cod)
            r = cur.execute("SELECT id FROM empresas_cc WHERE empresa=? LIMIT 1", (nombre,)).fetchone()
            return r[0] if r else None

        # ── Bancos ───────────────────────────────────────────────────────
        bancos = [
            ("BBVA","012"),("BANAMEX","002"),("BANORTE","072"),("HSBC","021"),
            ("SANTANDER","014"),("SCOTIABANK","044"),("INBURSA","036"),
            ("BAJIO","030"),("STP","646"),("AZTECA","127"),("BANREGIO","058"),
            ("MULTIVA","132"),("AFIRME","062"),("BANCOPPEL","137"),
            ("CITIBANAMEX","002"),("MIFEL","042"),("FONDEADORA","699"),
        ]
        for n,p in bancos:
            cur.execute("INSERT OR IGNORE INTO bancos (nombre,prefijo_clabe) VALUES (?,?)",(n,p))

        # ── Proveedores ──────────────────────────────────────────────────
        provs = [
            ("TELEFONOS DE MEXICO SAB DE CV","BBVA",""),
            ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV","BBVA",""),
            ("RADIOMOVIL DIPSA SA DE CV","BBVA",""),
            ("BICENTEL","BBVA",""),("IZZI NEGOCIOS","BBVA",""),
            ("PUBLIC VALUE","BBVA",""),("DE LAGE LANDEN","BBVA",""),
            ("DLL LEASING","BBVA",""),
            ("CFE COMISION FEDERAL DE ELECTRICIDAD","BBVA",""),
        ]
        for n,b,cl in provs:
            cur.execute("INSERT OR IGNORE INTO proveedores (nombre,banco,clabe) VALUES (?,?,?)",(n,b,cl))

        # ── Empresas y sucursales ────────────────────────────────────────
        emps = [
            ("SELECT SHOP MB SA DE CV","CORPORATIVO POLANCO PISO 13","ADMINISTRACION","ADMINISTRACION"),
            ("SELECT SHOP MB SA DE CV","CORPORATIVO POLANCO PISO 16","ADMINISTRACION","ADMINISTRACION"),
            ("SELECT SHOP MB SA DE CV","TEPOTZOTLAN II","LOGISTICA","LOGISTICA"),
            ("ENFERMERAS UNIDAS PLUS SA DE V","CORPORATIVO POLANCO PISO 13","ADMINISTRACION","ADMINISTRACION"),
            ("ENFERMERAS UNIDAS PLUS SA DE V","IZTAPALAPA","LOGISTICA","LOGISTICA"),
            ("ENFERMERAS UNIDAS PLUS SA DE V","T. CUERNAVACA","TIENDAS","TIENDAS"),
            ("ENFERMERAS UNIDAS PLUS SA DE V","T. ARAGON","TIENDAS","TIENDAS"),
            ("BH. BE HEALTHY COMERCIALIZADORA SA DE CV","CORPORATIVO POLANCO PISO 13","ADMINISTRACION","ADMINISTRACION"),
            ("BH SOLAR SA DE CV","CORPORATIVO POLANCO PISO 13","LOGISTICA","LOGISTICA"),
            ("SM DISTRIBUIDORA DIGITAL SA DE CV","CORPORATIVO POLANCO PISO 13","ADMINISTRACION","ADMINISTRACION"),
            ("COMERCIALIZADORA DE MARCAS JSB SA DE CV","CORPORATIVO POLANCO PISO 13","ADMINISTRACION","ADMINISTRACION"),
            ("COMERCIALIZADORA DE MARCAS JSB SA DE CV","TEPOTZOTLAN II","LOGISTICA","LOGISTICA"),
            ("MB COMERCIALIZADORA EN LINEA SA DE CV","CORPORATIVO POLANCO PISO 13","ADMINISTRACION","ADMINISTRACION"),
            ("COMERCIALIZADORA ONLINE NH SA DE CV","CORPORATIVO POLANCO PISO 13","ADMINISTRACION","ADMINISTRACION"),
            ("BLOOM & BLUSH SA DE CV","TEPOTZOTLAN III","LOGISTICA","LOGISTICA"),
            ("BLOOM & BLUSH SA DE CV","CORPORATIVO POLANCO PISO 13","FINANZAS","FINANZAS"),
            ("ALEGARAT SA DE CV","CORPORATIVO POLANCO PISO 13","FINANZAS","FINANZAS"),
            ("INMOBILIARIA EISHEL SA DE CV","CORPORATIVO POLANCO PISO 13","ADMINISTRACION","ADMINISTRACION"),
            ("MOSAIC CARE & HEALTH SA DE CV","CORPORATIVO POLANCO PISO 13","ADMINISTRACION","ADMINISTRACION"),
            ("MW MED SUPPLY MEDICAL SC PRL DE CV","CORPORATIVO POLANCO PISO 13","ADMINISTRACION","ADMINISTRACION"),
            ("GOLDEN YEARS MANAGEMENT SA DE CV","CORPORATIVO POLANCO PISO 13","ADMINISTRACION","ADMINISTRACION"),
        ]
        for emp,suc,cc,dr in emps:
            cur.execute("INSERT OR IGNORE INTO empresas_cc (empresa,sucursal,centro_costos,direccion) VALUES (?,?,?,?)",
                        (emp,suc,cc,dr))

        # ── Servicios recurrentes + pagos históricos Abril y Mayo 2026 ───
        ROWS = [
            ("TELEFONOS DE MEXICO SAB DE CV","5516683541","TELEFONIA E INTERNET",336.9,"07. MB COMERCIALIZADORA EN LINEA","POLANCO PISO 13","ADMINISTRACION",1,True,True),
            ("TELEFONOS DE MEXICO SAB DE CV","5516683579","TELEFONIA E INTERNET",798.0,"02. ENFERMERAS UNIDAS PLUS","MW MED SUPPLY","",1,True,True),
            ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV","0200660076","TELEFONIA E INTERNET",766.38,"01. SELECT SHOP MB","TEPOTZOTLAN II","LOGISTICA",4,False,True),
            ("PUBLIC VALUE","MANTENIMIENTO ERP","SERVICIO ERP",139200.0,"01. SELECT SHOP MB","T. POLANCO","FINANZAS",4,None,True),
            ("TELEFONOS DE MEXICO SAB DE CV","5552725727","TELEFONIA E INTERNET",336.9,"03. BH BE HEALTHY","POLANCO PISO 13","ADMINISTRACION",6,False,True),
            ("TELEFONOS DE MEXICO SAB DE CV","5556693389","TELEFONIA E INTERNET",198.0,"92. EISHEL","POLANCO PISO 13","ADMINISTRACION",6,True,True),
            ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV","0200707972","TELEFONIA E INTERNET",588.83,"03. BH BE HEALTHY","POLANCO PISO 13","ADMINISTRACION",7,False,True),
            ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV","0200723031","TELEFONIA E INTERNET",1723.27,"01. SELECT SHOP MB","POLANCO PISO 13","ADMINISTRACION",7,False,True),
            ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV","0200774234","TELEFONIA E INTERNET",4525.86,"01. SELECT SHOP MB","TEPOTZOTLAN II","LOGISTICA",7,False,True),
            ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV","0200774235","TELEFONIA E INTERNET",4525.86,"01. SELECT SHOP MB","TEPOTZOTLAN II","LOGISTICA",7,False,True),
            ("DE LAGE LANDEN","009-0036157-000","ARRENDAMIENTO",24247.22,"01. SELECT SHOP MB","T. POLANCO","FINANZAS",8,None,True),
            ("DLL LEASING","023-0230311-000","ARRENDAMIENTO",15228.91,"01. SELECT SHOP MB","T. POLANCO","FINANZAS",8,None,True),
            ("DLL LEASING","023-0230033-000","ARRENDAMIENTO",23116.88,"01. SELECT SHOP MB","T. POLANCO","FINANZAS",8,None,True),
            ("DLL LEASING","023-0230140-000","ARRENDAMIENTO",28726.29,"01. SELECT SHOP MB","T. POLANCO","FINANZAS",8,None,True),
            ("TELEFONOS DE MEXICO SAB DE CV","5550872370","TELEFONIA E INTERNET",336.9,"01. SELECT SHOP MB","POLANCO PISO 13","ADMINISTRACION",10,True,True),
            ("TELEFONOS DE MEXICO SAB DE CV","5556871130","TELEFONIA E INTERNET",336.9,"02. ENFERMERAS UNIDAS PLUS","POLANCO PISO 13","ADMINISTRACION",11,True,True),
            ("TELEFONOS DE MEXICO SAB DE CV","5591293910","TELEFONIA E INTERNET",423.1,"08. COMERCIALIZADORA ONLINE NH","POLANCO PISO 13","ADMINISTRACION",11,False,True),
            ("TELEFONOS DE MEXICO SAB DE CV","5552551893","TELEFONIA E INTERNET",423.1,"05. SM DISTRIBUIDORA DIGITAL","POLANCO PISO 13","ADMINISTRACION",12,True,True),
            ("TELEFONOS DE MEXICO SAB DE CV","CTA MAESTRA 0F06717","CUENTA MAESTRA TELMEX",4681.93,"02. ENFERMERAS UNIDAS PLUS","POLANCO PISO 13","FINANZAS",15,True,None),
            ("TELEFONOS DE MEXICO SAB DE CV","CTA MAESTRA 0F58191","CUENTA MAESTRA TELMEX BH",507.53,"03. BH BE HEALTHY","POLANCO PISO 13","FINANZAS",15,True,None),
            ("IZZI NEGOCIOS","48105784","INTERNET IZZI",439.0,"12. ALEAGARAT","POLANCO PISO 13","FINANZAS",15,True,None),
            ("TELEFONOS DE MEXICO SAB DE CV","5552039579","TELEFONIA E INTERNET",478.55,"02. ENFERMERAS UNIDAS PLUS","T. POLANCO","TIENDAS",16,True,None),
            ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV","0200835275","TELEFONIA E INTERNET",2280.0,"01. SELECT SHOP MB","POLANCO PISO 13","ADMINISTRACION",16,True,None),
            ("TELEFONOS DE MEXICO SAB DE CV","5556850241","TELEFONIA E INTERNET",463.55,"02. ENFERMERAS UNIDAS PLUS","IZTAPALAPA","LOGISTICA",17,True,None),
            ("TELEFONOS DE MEXICO SAB DE CV","5556854768","TELEFONIA E INTERNET",463.55,"02. ENFERMERAS UNIDAS PLUS","IZTAPALAPA","LOGISTICA",17,True,None),
            ("TELEFONOS DE MEXICO SAB DE CV","5556855148","TELEFONIA E INTERNET",1145.22,"02. ENFERMERAS UNIDAS PLUS","IZTAPALAPA","LOGISTICA",17,True,None),
            ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV","0105751751","TELEFONIA E INTERNET",800.0,"06. COMERCIALIZADORA DE MARCAS JSB","POLANCO PISO 13","ADMINISTRACION",18,True,False),
            ("IZZI NEGOCIOS","INTERNET MARZO","INTERNET IZZI",590.0,"11. BLOOM BLUSH","POLANCO PISO 13","FINANZAS",19,True,None),
            ("BICENTEL","MICROSOFT","LICENCIAS",2187.34,"01. SELECT SHOP MB","","FINANZAS",20,True,True),
            ("TELEFONOS DE MEXICO SAB DE CV","5524773274","TELEFONIA E INTERNET",423.1,"11. BLOOM BLUSH","TEPOTZOTLAN III","LOGISTICA",21,True,None),
            ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV","0200835961","TELEFONIA E INTERNET",2280.0,"11. BLOOM BLUSH","TEPOTZOTLAN III","LOGISTICA",22,True,None),
            ("TELEFONOS DE MEXICO SAB DE CV","5559100988","TELEFONIA E INTERNET",336.9,"04. BH SOLAR","POLANCO PISO 13","LOGISTICA",23,True,None),
            ("TELEFONOS DE MEXICO SAB DE CV","5511008625","TELEFONIA E INTERNET",423.1,"06. COMERCIALIZADORA DE MARCAS JSB","TEPOTZOTLAN II","LOGISTICA",24,True,None),
            ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV","0200804119","TELEFONIA E INTERNET",2373.96,"11. BLOOM BLUSH","TEPOTZOTLAN III","LOGISTICA",26,True,False),
            ("TELEFONOS DE MEXICO SAB DE CV","5522373301","TELEFONIA E INTERNET",389.0,"02. ENFERMERAS UNIDAS PLUS","","",27,True,None),
            ("TELEFONOS DE MEXICO SAB DE CV","5550880352","TELEFONIA E INTERNET",236.0,"06. COMERCIALIZADORA DE MARCAS JSB","","",27,True,None),
            ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV","0200666296","TELEFONIA E INTERNET",6000.0,"01. SELECT SHOP MB","TEPOTZOTLAN II","LOGISTICA",28,True,None),
            ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV","0200666297","TELEFONIA E INTERNET",6000.0,"01. SELECT SHOP MB","TEPOTZOTLAN II","LOGISTICA",28,True,None),
            ("TELEFONOS DE MEXICO SAB DE CV","5556854664","TELEFONIA E INTERNET",1145.22,"02. ENFERMERAS UNIDAS PLUS","IZTAPALAPA","LOGISTICA",28,True,None),
            ("TOTAL PLAY TELECOMUNICACIONES SAPI DE CV","0200741885","TELEFONIA E INTERNET",1637.07,"06. COMERCIALIZADORA DE MARCAS JSB","TEPOTZOTLAN II","LOGISTICA",29,True,None),
            ("BICENTEL","TODO INCLUIDO UC","TELEFONIA E INTERNET",45753.07,"01. SELECT SHOP MB","","FINANZAS",30,True,True),
            ("TELEFONOS DE MEXICO SAB DE CV","5522373301 B","TELEFONIA E INTERNET",328.44,"06. COMERCIALIZADORA DE MARCAS JSB","TEPOTZOTLAN II","LOGISTICA",30,True,None),
            ("TELEFONOS DE MEXICO SAB DE CV","5550880292","TELEFONIA E INTERNET",198.0,"91. MOSAIC CARE & HEALTH","POLANCO PISO 13","ADMINISTRACION",30,True,None),
            ("TELEFONOS DE MEXICO SAB DE CV","7771001628","TELEFONIA E INTERNET",463.55,"02. ENFERMERAS UNIDAS PLUS","T. CUERNAVACA","TIENDAS",28,True,False),
            ("TELEFONOS DE MEXICO SAB DE CV","5557608176","TELEFONIA E INTERNET",463.55,"02. ENFERMERAS UNIDAS PLUS","T. ARAGON","TIENDAS",28,True,None),
        ]

        for prov_nom, cuenta, concepto, monto, emp_cod, suc, cc, dia, pag_abr, pag_may in ROWS:
            prov_id = get_prov_id(prov_nom)
            emp_id  = get_emp_id(emp_cod)
            emp_nom = norm_emp(emp_cod)
            suc_norm= norm_suc(suc) if suc else ""
            desc = f"{prov_nom[:25]} {cuenta}"
            cur.execute("""INSERT OR IGNORE INTO servicios_recurrentes
                           (proveedor_id,empresa_cc_id,descripcion,no_cuenta_servicio,
                            dia_limite,monto_base,iva,activo)
                           VALUES (?,?,?,?,?,?,?,1)""",
                        (prov_id, emp_id, desc, cuenta, dia, monto, 0))
            srv_id = cur.lastrowid or cur.execute(
                "SELECT id FROM servicios_recurrentes WHERE descripcion=? AND no_cuenta_servicio=?",
                (desc, cuenta)).fetchone()[0]

            for mes_num, mes_nom, pagado in [(4,"Abril",pag_abr),(5,"Mayo",pag_may)]:
                if pagado is None: continue
                estatus = "PAGADO" if pagado else "PENDIENTE"
                dia_real = min(dia, 28) if dia else 15
                fecha_proc = f"2026-{mes_num:02d}-{dia_real:02d}"
                motivo = f"SERV {cuenta} {mes_nom.upper()} 2026"
                cur.execute("""INSERT OR IGNORE INTO pagos
                               (servicio_id,proveedor_nombre,empresa,sucursal,
                                centro_costos,motivo_pago,monto_total,importe_letra,
                                banco,clabe,no_cuenta,observaciones,
                                mes_presupuesto,mes_pago,mes,anio,
                                estatus,fecha_proceso,analista_nombre,gerente_nombre)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (srv_id, prov_nom, emp_nom, suc_norm, cc,
                             motivo, monto, "", "BBVA", "", cuenta, "",
                             mes_nom, mes_nom, mes_num, 2026,
                             estatus, fecha_proc, "", ""))

        conn.commit()
        conn.close()

    def upsert_proveedor(self, datos: dict):
        conn = self._conn()
        nombre = datos.get("nombre","").strip()
        if not nombre: return
        existing = conn.execute("SELECT id FROM proveedores WHERE nombre=?", (nombre,)).fetchone()
        if existing:
            conn.execute("""UPDATE proveedores SET banco=COALESCE(NULLIF(?,''),banco),
                           clabe=COALESCE(NULLIF(?,''),clabe) WHERE nombre=?""",
                        (datos.get("banco",""), datos.get("clabe",""), nombre))
        else:
            conn.execute("INSERT INTO proveedores (nombre,banco,clabe) VALUES (?,?,?)",
                        (nombre, datos.get("banco",""), datos.get("clabe","")))
        conn.commit()

    def upsert_banco(self, datos: dict):
        conn = self._conn()
        nombre = datos.get("nombre","").strip().upper()
        if not nombre: return
        existing = conn.execute("SELECT id FROM bancos WHERE nombre=?", (nombre,)).fetchone()
        if not existing:
            conn.execute("INSERT INTO bancos (nombre,prefijo_clabe) VALUES (?,?)",
                        (nombre, datos.get("prefijo_clabe","")))
            conn.commit()


    def exportar_csv(self, mes: int, anio: int, ruta: str) -> int:
        import csv
        pagos = self.get_pagos_mes(mes, anio)
        if not pagos: return 0
        with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=pagos[0].keys())
            w.writeheader(); w.writerows(pagos)
        return len(pagos)
