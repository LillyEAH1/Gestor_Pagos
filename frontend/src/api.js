// Cliente de la API del backend FastAPI.
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function handle(res) {
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type") || "";
  if (!res.ok) {
    let detail = res.statusText;
    if (ct.includes("application/json")) {
      try { detail = (await res.json()).detail || detail; } catch {}
    }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  if (ct.includes("application/json")) return res.json();
  return res;
}

export const api = {
  base: BASE,

  // ── Salud ──────────────────────────────────────────
  health: (timeoutMs = 12000) => {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeoutMs);
    return fetch(`${BASE}/health`, { signal: ctrl.signal })
      .then(handle)
      .catch(() => ({ ok: false, groq_configurada: false, db_configurada: false }))
      .finally(() => clearTimeout(t));
  },

  // ── OCR ────────────────────────────────────────────
  escanear: (file, tipoDoc = "recibo") => {
    const fd = new FormData();
    fd.append("archivo", file);
    fd.append("tipo_doc", tipoDoc);
    return fetch(`${BASE}/api/ocr/escanear`, { method: "POST", body: fd }).then(handle);
  },
  probarGroq: () => fetch(`${BASE}/api/ocr/probar`).then(handle),

  // ── Documentos ─────────────────────────────────────
  generarPdf: (datos) =>
    fetch(`${BASE}/api/documentos/pdf`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ datos }),
    }).then((r) => { if (!r.ok) throw new Error("Error generando PDF"); return r.blob(); }),
  numeroLetra: (monto) =>
    fetch(`${BASE}/api/documentos/numero-letra`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ monto }),
    }).then(handle),
  excelUrl: (mes, anio) => `${BASE}/api/documentos/excel?mes=${mes}&anio=${anio}`,

  // ── Pagos ──────────────────────────────────────────
  listarPagos: (mes, anio) => fetch(`${BASE}/api/pagos?mes=${mes}&anio=${anio}`).then(handle),
  buscarPagos: (q) => fetch(`${BASE}/api/pagos/buscar?q=${encodeURIComponent(q)}`).then(handle),
  estadoCuenta: (mes, anio) => fetch(`${BASE}/api/pagos/estado-cuenta?mes=${mes}&anio=${anio}`).then(handle),
  proximos: (dias = 30) => fetch(`${BASE}/api/pagos/proximos?dias=${dias}`).then(handle),
  crearPago: (datos) =>
    fetch(`${BASE}/api/pagos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datos),
    }).then(handle),
  actualizarPago: (id, datos) =>
    fetch(`${BASE}/api/pagos/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datos),
    }).then(handle),
  eliminarPago: (id) => fetch(`${BASE}/api/pagos/${id}`, { method: "DELETE" }).then(handle),

  // ── Catálogos ──────────────────────────────────────
  proveedores: () => fetch(`${BASE}/api/catalogos/proveedores?nombres_only=true`).then(handle),
  bancos: () => fetch(`${BASE}/api/catalogos/bancos`).then(handle),
  empresas: () => fetch(`${BASE}/api/catalogos/empresas`).then(handle),
};
