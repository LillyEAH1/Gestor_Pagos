import { useState, useEffect } from "react";
import { api } from "../api";

export default function Calendario({ health }) {
  const [items, setItems] = useState([]);
  const [dias, setDias] = useState(30);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    if (!health?.db_configurada) return;
    setLoading(true);
    api.proximos(dias)
      .then(setItems)
      .catch((e) => setMsg({ t: "err", m: e.message }))
      .finally(() => setLoading(false));
  }, [dias, health]);

  if (!health?.db_configurada) {
    return (
      <>
        <h1 className="page-title">Alertas / Calendario</h1>
        <div className="alert warn">Requiere base de datos configurada (Supabase). Aquí aparecerán los servicios recurrentes por vencer.</div>
        <div className="alert info">Los recordatorios en Outlook se migrarán a Microsoft Graph (Fase 4).</div>
      </>
    );
  }

  return (
    <>
      <h1 className="page-title">Alertas / Calendario</h1>
      <p className="page-sub">Servicios recurrentes próximos a vencer este mes.</p>

      <div className="card">
        <div className="field" style={{ maxWidth: 220 }}>
          <label>Ventana (días)</label>
          <select value={dias} onChange={(e) => setDias(+e.target.value)}>
            {[7, 15, 30, 60].map((d) => <option key={d} value={d}>{d} días</option>)}
          </select>
        </div>
      </div>

      {msg && <div className={"alert " + msg.t}>{msg.m}</div>}

      <div className="card">
        {loading ? <p className="muted"><span className="spinner" style={{ borderColor: "#999", borderTopColor: "transparent" }} /> Cargando…</p> : (
          <table>
            <thead><tr><th>Proveedor</th><th>Cuenta / Servicio</th><th>Empresa</th><th>Vence</th><th>Días</th><th>Monto</th></tr></thead>
            <tbody>
              {items.length === 0 && <tr><td colSpan={6} className="muted">Nada por vencer en esta ventana. 🎉</td></tr>}
              {items.map((s) => (
                <tr key={s.id}>
                  <td>{s.proveedor_nombre}</td>
                  <td>{s.no_cuenta_servicio || s.descripcion}</td>
                  <td>{s.empresa}</td>
                  <td>{s.fecha_limite}</td>
                  <td><span className={"badge " + (s.dias_para_vencer <= 3 ? "pendiente" : "pagado")}>{s.dias_para_vencer} d</span></td>
                  <td>${Number(s.monto_base || 0).toLocaleString("es-MX", { minimumFractionDigits: 2 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
