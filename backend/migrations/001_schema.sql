-- ============================================================
-- GestorPagosMarcovich — Esquema Postgres (Supabase)
-- Migrado de la app de escritorio SQLite (v60/database.py).
-- Cambios vs SQLite:
--   AUTOINCREMENT      -> GENERATED ALWAYS AS IDENTITY
--   REAL (dinero)      -> NUMERIC(14,2)
--   activo INTEGER 0/1 -> BOOLEAN
--   datetime('now')    -> now() (TIMESTAMPTZ)
-- ============================================================

-- ── Proveedores ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS proveedores (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre        TEXT NOT NULL,
    beneficiario  TEXT,
    banco         TEXT,
    clabe         TEXT,
    no_cuenta     TEXT,
    moneda        TEXT DEFAULT 'MXN',
    creado_en     TIMESTAMPTZ DEFAULT now()
);

-- ── Bancos ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bancos (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre         TEXT NOT NULL UNIQUE,
    prefijo_clabe  TEXT,
    descripcion    TEXT
);

-- ── Plantillas de observaciones ─────────────────────────
CREATE TABLE IF NOT EXISTS plantillas_observaciones (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    proveedor_patron  TEXT,
    template          TEXT NOT NULL,
    descripcion       TEXT,
    activo            BOOLEAN DEFAULT true,
    creado_en         TIMESTAMPTZ DEFAULT now()
);

-- ── Empresas / Centros de costo ─────────────────────────
CREATE TABLE IF NOT EXISTS empresas_cc (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    empresa        TEXT NOT NULL DEFAULT '',
    nom_corto      TEXT,
    sucursal       TEXT,
    centro_costos  TEXT,
    direccion      TEXT,
    tipo_gasto     TEXT DEFAULT 'GASTO'
);

-- ── Servicios recurrentes ───────────────────────────────
CREATE TABLE IF NOT EXISTS servicios_recurrentes (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    proveedor_id        BIGINT REFERENCES proveedores(id),
    empresa_cc_id       BIGINT REFERENCES empresas_cc(id),
    descripcion         TEXT,
    no_cuenta_servicio  TEXT,
    tipo                TEXT,
    monto_base          NUMERIC(14,2) DEFAULT 0,
    iva                 NUMERIC(14,2) DEFAULT 0,
    dia_limite          INTEGER,
    activo              BOOLEAN DEFAULT true
);

-- ── Pagos (historial) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS pagos (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    servicio_id       BIGINT REFERENCES servicios_recurrentes(id),
    proveedor_nombre  TEXT,
    empresa           TEXT,
    sucursal          TEXT,
    centro_costos     TEXT,
    direccion         TEXT,
    motivo_pago       TEXT,
    folio_cfdi        TEXT,
    notas_credito     NUMERIC(14,2) DEFAULT 0,
    monto_total       NUMERIC(14,2) DEFAULT 0,
    importe_letra     TEXT,
    banco             TEXT,
    clabe             TEXT,
    no_cuenta         TEXT,
    forma_pago        TEXT,
    observaciones     TEXT,
    mes_presupuesto   TEXT,
    mes_pago          TEXT,
    mes               INTEGER,
    anio              INTEGER,
    estatus           TEXT DEFAULT 'PENDIENTE',
    fecha_proceso     TEXT,
    pdf_ruta          TEXT,
    analista_nombre   TEXT,
    gerente_nombre    TEXT,
    creado_en         TIMESTAMPTZ DEFAULT now()
);

-- ── Índices útiles para el historial ────────────────────
CREATE INDEX IF NOT EXISTS idx_pagos_anio_mes  ON pagos (anio, mes);
CREATE INDEX IF NOT EXISTS idx_pagos_estatus   ON pagos (estatus);
CREATE INDEX IF NOT EXISTS idx_pagos_proveedor ON pagos (proveedor_nombre);
