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

      {loading ? (
        <p className="muted"><span className="spinner" style={{ borderColor: "#999", borderTopColor: "transparent" }} /> Cargando…</p>
      ) : items.length === 0 ? (
        <div className="card flat"><p className="muted" style={{ margin: 0 }}>Nada por vencer en esta ventana. 🎉</p></div>
      ) : (
        items.map((s) => {
          const monto = Number(s.monto_base || 0).toLocaleString("es-MX", { minimumFractionDigits: 2 });
          const urgente = s.dias_para_vencer <= 3;
          return (
            <div key={s.id} className={"alert-card" + (urgente ? "" : " soft")}>
              <div>
                <div className="t">{s.proveedor_nombre}</div>
                <div className="s">{(s.no_cuenta_servicio || s.descripcion)} · ${monto} MXN · {s.empresa}</div>
              </div>
              <div className="due">
                Vence el {s.fecha_limite}<br />
                <strong>{s.dias_para_vencer === 0 ? "Hoy" : `${s.dias_para_vencer} día(s)`}</strong>
              </div>
            </div>
          );
        })
      )}
    </>
  );
}
