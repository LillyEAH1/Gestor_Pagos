import { useState } from "react";
import { api } from "../api";
import { loadFirmantes, saveFirmantes, FIRMANTES_DEFAULT } from "../store";

const CAMPOS = [
  ["analista_nombre", "Analista de Sistemas"],
  ["gerente_nombre", "Gerente de Sistemas"],
  ["visto_bno", "Vo. Bo. / Depto. Finanzas"],
  ["depto_finanzas", "Departamento de Finanzas"],
  ["dir_financiera", "Dirección Financiera"],
  ["dir_general", "Dirección General"],
];

export default function Configuracion({ health }) {
  const [firm, setFirm] = useState(loadFirmantes);
  const [savedMsg, setSavedMsg] = useState(false);
  const [groq, setGroq] = useState(null);
  const [probando, setProbando] = useState(false);

  const set = (k, v) => setFirm((f) => ({ ...f, [k]: v }));

  function guardar() {
    saveFirmantes(firm);
    setSavedMsg(true);
    setTimeout(() => setSavedMsg(false), 2500);
  }

  async function probarGroq() {
    setProbando(true); setGroq(null);
    try { setGroq(await api.probarGroq()); }
    catch (e) { setGroq({ ok: false, mensaje: e.message }); }
    finally { setProbando(false); }
  }

  return (
    <>
      <h1 className="page-title">Configuración</h1>
      <p className="page-sub">Firmantes, conexión de OCR y estado del sistema.</p>

      <div className="card">
        <h3>Firmantes</h3>
        <p className="muted" style={{ marginTop: -8 }}>Se guardan en este navegador y se reutilizan en cada solicitud.</p>
        <div className="row">
          {CAMPOS.map(([k, l]) => (
            <div className="field" key={k} style={{ minWidth: 240 }}>
              <label>{l}</label>
              <input value={firm[k]} onChange={(e) => set(k, e.target.value)} />
            </div>
          ))}
        </div>
        <div className="btn-row">
          <button className="btn" onClick={guardar}>Guardar firmantes</button>
          <button className="btn ghost" onClick={() => setFirm({ ...FIRMANTES_DEFAULT })}>Limpiar</button>
          {savedMsg && <span className="alert ok" style={{ margin: 0 }}>Guardado ✓</span>}
        </div>
      </div>

      <div className="card">
        <h3>OCR (Groq Vision)</h3>
        <p className="muted" style={{ marginTop: -8 }}>La API key se configura en el servidor (variable <code>GROQ_API_KEY</code>), no aquí.</p>
        <div className="btn-row">
          <button className="btn" onClick={probarGroq} disabled={probando}>
            {probando ? <><span className="spinner" /> Probando…</> : "Probar conexión Groq"}
          </button>
        </div>
        {groq && <div className={"alert " + (groq.ok ? "ok" : "err")}>{groq.mensaje}</div>}
      </div>

      <div className="card">
        <h3>Estado del sistema</h3>
        <table>
          <tbody>
            <tr><td>API backend</td><td>{badge(health?.ok)}</td></tr>
            <tr><td>Groq OCR configurado</td><td>{badge(health?.groq_configurada)}</td></tr>
            <tr><td>Base de datos (Supabase)</td><td>{badge(health?.db_configurada)}</td></tr>
          </tbody>
        </table>
        <p className="muted" style={{ fontSize: 12, marginBottom: 0 }}>API: {api.base}</p>
      </div>
    </>
  );
}

function badge(ok) {
  return <span className={"badge " + (ok ? "pagado" : "pendiente")}>{ok ? "OK" : "No configurado"}</span>;
}
