"""
Capa de datos Postgres (Supabase) — portada de v60/database.py.

Usa psycopg 3 con pool de conexión. Las consultas devuelven dicts (dict_row),
igual que el sqlite3.Row del original. Placeholders %s (Postgres) en vez de ? .
"""
from __future__ import annotations
from contextlib import contextmanager
from datetime import date

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_settings

_pool: ConnectionPool | None = None

# Columnas insertables de un pago (id/creado_en los pone la BD)
PAGO_CAMPOS = [
    "servicio_id", "proveedor_nombre", "empresa", "sucursal", "centro_costos", "direccion",
    "motivo_pago", "folio_cfdi", "notas_credito", "monto_total", "importe_letra",
    "banco", "clabe", "no_cuenta", "forma_pago", "observaciones",
    "mes_presupuesto", "mes_pago", "mes", "anio", "estatus",
    "fecha_proceso", "pdf_ruta", "analista_nombre", "gerente_nombre",
]


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        dsn = get_settings().database_url
        if not dsn:
            raise RuntimeError(
                "DATABASE_URL no configurada. Pon el Connection string de Supabase en .env"
            )
        _pool = ConnectionPool(dsn, min_size=1, max_size=5, kwargs={"row_factory": dict_row})
    return _pool


@contextmanager
def get_conn():
    with get_pool().connection() as conn:
        yield conn


def db_disponible() -> bool:
    return bool(get_settings().database_url)


# ── Pagos ────────────────────────────────────────────────────────────────

def crear_pago(datos: dict) -> int:
    cols = ", ".join(PAGO_CAMPOS)
    ph = ", ".join(["%s"] * len(PAGO_CAMPOS))
    vals = [datos.get(c) for c in PAGO_CAMPOS]
    with get_conn() as c:
        row = c.execute(
            f"INSERT INTO pagos ({cols}) VALUES ({ph}) RETURNING id", vals
        ).fetchone()
        return row["id"]


def get_pago(pago_id: int) -> dict | None:
    with get_conn() as c:
        return c.execute("SELECT * FROM pagos WHERE id=%s", (pago_id,)).fetchone()


def actualizar_pago(pago_id: int, datos: dict) -> None:
    if not datos:
        return
    sets = ", ".join(f"{k}=%s" for k in datos)
    vals = list(datos.values()) + [pago_id]
    with get_conn() as c:
        c.execute(f"UPDATE pagos SET {sets} WHERE id=%s", vals)


def eliminar_pago(pago_id: int) -> None:
    with get_conn() as c:
        c.execute("DELETE FROM pagos WHERE id=%s", (pago_id,))


def get_pagos_mes(mes: int, anio: int) -> list[dict]:
    with get_conn() as c:
        return c.execute(
            "SELECT * FROM pagos WHERE mes=%s AND anio=%s ORDER BY creado_en DESC",
            (mes, anio),
        ).fetchall()


def estado_cuenta_mes(mes: int, anio: int) -> dict:
    pagos = get_pagos_mes(mes, anio)
    pagados = [p for p in pagos if p["estatus"] in ("PAGADO", "LISTO")]
    pendientes = [p for p in pagos if p["estatus"] == "PENDIENTE"]
    return {
        "mes": mes, "anio": anio,
        "pagados": pagados, "pendientes": pendientes,
        "total_pagado": float(sum(p["monto_total"] or 0 for p in pagados)),
        "total_pendiente": float(sum(p["monto_total"] or 0 for p in pendientes)),
        "todos": pagos,
    }


def buscar_pagos(query: str) -> list[dict]:
    q = f"%{query.upper()}%"
    with get_conn() as c:
        return c.execute(
            """
            SELECT * FROM pagos
            WHERE UPPER(proveedor_nombre) LIKE %s
               OR UPPER(empresa)          LIKE %s
               OR UPPER(motivo_pago)      LIKE %s
               OR UPPER(observaciones)    LIKE %s
               OR UPPER(folio_cfdi)       LIKE %s
               OR UPPER(no_cuenta)        LIKE %s
               OR UPPER(clabe)            LIKE %s
            ORDER BY creado_en DESC LIMIT 200
            """,
            (q, q, q, q, q, q, q),
        ).fetchall()


def servicios_proximos(dias: int = 30) -> list[dict]:
    hoy = date.today()
    mes, anio = hoy.month, hoy.year
    pagados_ids = {
        p["servicio_id"] for p in get_pagos_mes(mes, anio)
        if p["servicio_id"] and p["estatus"] in ("PAGADO", "LISTO")
    }
    with get_conn() as c:
        servicios = c.execute(
            """
            SELECT s.*, p.nombre AS proveedor_nombre,
                   p.banco, p.clabe, p.no_cuenta,
                   e.empresa, e.sucursal, e.centro_costos, e.direccion
            FROM servicios_recurrentes s
            LEFT JOIN proveedores p ON s.proveedor_id = p.id
            LEFT JOIN empresas_cc e ON s.empresa_cc_id = e.id
            WHERE s.activo = true AND s.dia_limite IS NOT NULL
            """
        ).fetchall()
    proximos = []
    for s in servicios:
        if s["id"] in pagados_ids:
            continue
        try:
            vence = date(anio, mes, int(s["dia_limite"]))
        except ValueError:
            continue
        delta = (vence - hoy).days
        if 0 <= delta <= dias:
            proximos.append({**s, "dias_para_vencer": delta, "fecha_limite": vence.isoformat()})
    return proximos


# ── Catálogos ────────────────────────────────────────────────────────────

def list_proveedores() -> list[dict]:
    with get_conn() as c:
        return c.execute("SELECT * FROM proveedores ORDER BY nombre").fetchall()


def list_nombres_proveedores() -> list[str]:
    with get_conn() as c:
        rows = c.execute("SELECT nombre FROM proveedores ORDER BY nombre").fetchall()
        return [r["nombre"] for r in rows]


def list_bancos() -> list[dict]:
    with get_conn() as c:
        return c.execute("SELECT * FROM bancos ORDER BY nombre").fetchall()


def list_empresas_cc() -> list[dict]:
    with get_conn() as c:
        return c.execute("SELECT * FROM empresas_cc ORDER BY empresa, sucursal").fetchall()


def upsert_proveedor(datos: dict) -> None:
    nombre = (datos.get("nombre") or "").strip()
    if not nombre:
        return
    with get_conn() as c:
        existing = c.execute("SELECT id FROM proveedores WHERE nombre=%s", (nombre,)).fetchone()
        if existing:
            c.execute(
                """UPDATE proveedores SET banco=COALESCE(NULLIF(%s,''),banco),
                   clabe=COALESCE(NULLIF(%s,''),clabe) WHERE nombre=%s""",
                (datos.get("banco", ""), datos.get("clabe", ""), nombre),
            )
        else:
            c.execute(
                "INSERT INTO proveedores (nombre,banco,clabe) VALUES (%s,%s,%s)",
                (nombre, datos.get("banco", ""), datos.get("clabe", "")),
            )


def upsert_banco(datos: dict) -> None:
    nombre = (datos.get("nombre") or "").strip().upper()
    if not nombre:
        return
    with get_conn() as c:
        existing = c.execute("SELECT id FROM bancos WHERE nombre=%s", (nombre,)).fetchone()
        if not existing:
            c.execute(
                "INSERT INTO bancos (nombre,prefijo_clabe) VALUES (%s,%s)",
                (nombre, datos.get("prefijo_clabe", "")),
            )
