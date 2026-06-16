import { useState, useEffect, useCallback } from "react";
import { api } from "../api";
import { MESES, loadFirmantes } from "../store";

const hoy = new Date();

export default function Historial({ health }) {
  const [mes, setMes] = useState(hoy.getMonth() + 1);
  const [anio, setAnio] = useState(hoy.getFullYear());
  const [pagos, setPagos] = useState([]);
  const [estado, setEstado] = useState(null);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState(null);

  const cargar = useCallback(async () => {
    if (!health?.db_configurada) return;
    setLoading(true); setMsg(null);
    try {
      const [lista, est] = await Promise.all([api.listarPagos(mes, anio), api.estadoCuenta(mes, anio)]);
      setPagos(lista); setEstado(est);
    } catch (e) {
      setMsg({ t: "err", m: e.message });
    } finally { setLoading(false); }
  }, [mes, anio, health]);

  useEffect(() => { cargar(); }, [cargar]);

  async function buscar() {
    if (!q.trim()) { cargar(); return; }
    setLoading(true);
    try { setPagos(await api.buscarPagos(q)); setEstado(null); }
    catch (e) { setMsg({ t: "err", m: e.message }); }
    finally { setLoading(false); }
  }

  async function toggleEstatus(p) {
    const nuevo = p.estatus === "PAGADO" ? "PENDIENTE" : "PAGADO";
    try { await api.actualizarPago(p.id, { estatus: nuevo }); cargar(); }
    catch (e) { setMsg({ t: "err", m: e.message }); }
  }

  async function eliminar(p) {
    if (!confirm(`¿Eliminar el pago #${p.id} (${p.proveedor_nombre})?`)) return;
    try { await api.eliminarPago(p.id); cargar(); }
    catch (e) { setMsg({ t: "err", m: e.message }); }
  }

  async function pdf(p) {
    try {
      const datos = { ...p, ...loadFirmantes(), proveedor_nombre: p.proveedor_nombre };
      const blob = await api.generarPdf(datos);
      window.open(URL.createObjectURL(blob), "_blank");
    } catch (e) { setMsg({ t: "err", m: e.message }); }
  }

  if (!health?.db_configurada) {
    return (
      <>
        <h1 className="page-title">Historial</h1>
        <div className="alert warn">La base de datos no está configurada en el servidor (falta <code>DATABASE_URL</code> de Supabase). El historial estará disponible cuando se conecte.</div>
      </>
    );
  }

  return (
    <>
      <h1 className="page-title">Historial de Pagos</h1>
      <p className="page-sub">Consulta, filtra y administra los pagos registrados.</p>

      <div className="card">
        <div className="row" style={{ alignItems: "flex-end" }}>
          <div className="field" style={{ minWidth: 150 }}>
            <label>Mes</label>
            <select value={mes} onChange={(e) => setMes(+e.target.value)}>
              {MESES.slice(1).map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
            </select>
          </div>
          <div className="field" style={{ minWidth: 110 }}>
            <label>Año</label>
            <input type="number" value={anio} onChange={(e) => setAnio(+e.target.value)} />
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>Buscar</label>
            <input value={q} onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && buscar()}
              placeholder="Proveedor, empresa, motivo, folio, cuenta…" />
          </div>
          <div className="field" style={{ flex: 0 }}>
            <button className="btn" onClick={buscar}>Buscar</button>
          </div>
          <div className="field" style={{ flex: 0 }}>
            <a className="btn ghost" href={api.excelUrl(mes, anio)}>Excel</a>
          </div>
        </div>
      </div>

      {estado && (
        <div className="metrics">
          <div className="metric"><div className="v">{pagos.length}</div><div className="l">Pagos del mes</div></div>
          <div className="metric"><div className="v" style={{ color: "var(--green)" }}>${estado.total_pagado.toLocaleString("es-MX", { minimumFractionDigits: 2 })}</div><div className="l">Total pagado</div></div>
          <div className="metric"><div className="v" style={{ color: "var(--amber)" }}>${estado.total_pendiente.toLocaleString("es-MX", { minimumFractionDigits: 2 })}</div><div className="l">Total pendiente</div></div>
        </div>
      )}

      {msg && <div className={"alert " + msg.t}>{msg.m}</div>}

      <div className="card">
        {loading ? <p className="muted"><span className="spinner" style={{ borderColor: "#999", borderTopColor: "transparent" }} /> Cargando…</p> : (
          <table>
            <thead>
              <tr><th>ID</th><th>Proveedor</th><th>Empresa</th><th>Motivo</th><th>Monto</th><th>Estatus</th><th>Fecha</th><th></th></tr>
            </thead>
            <tbody>
              {pagos.length === 0 && <tr><td colSpan={8} className="muted">Sin pagos para este filtro.</td></tr>}
              {pagos.map((p) => (
                <tr key={p.id}>
                  <td>{p.id}</td>
                  <td>{p.proveedor_nombre}</td>
                  <td>{p.empresa}</td>
                  <td style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.motivo_pago}</td>
                  <td>${Number(p.monto_total || 0).toLocaleString("es-MX", { minimumFractionDigits: 2 })}</td>
                  <td><span className={"badge " + (p.estatus === "PAGADO" ? "pagado" : "pendiente")}>{p.estatus}</span></td>
                  <td>{p.fecha_proceso || "—"}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button className="btn ghost" style={btnSm} onClick={() => toggleEstatus(p)}>↺</button>
                    <button className="btn ghost" style={btnSm} onClick={() => pdf(p)}>PDF</button>
                    <button className="btn danger" style={btnSm} onClick={() => eliminar(p)}>✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

const btnSm = { padding: "4px 8px", fontSize: 12, marginRight: 4 };
