import { useState, useEffect } from "react";
import { api } from "./api";
import { loadFirmantes } from "./store";
import NuevaSolicitud from "./pages/NuevaSolicitud";
import Historial from "./pages/Historial";
import Calendario from "./pages/Calendario";
import Configuracion from "./pages/Configuracion";

const GRUPOS = [
  { cat: "Principal", items: [
    { key: "nueva", label: "+ Nuevo pago" },
    { key: "historial", label: "Historial" },
  ]},
  { cat: "Calendario", items: [
    { key: "calendario", label: "Alertas" },
  ]},
  { cat: "Ajustes", items: [
    { key: "config", label: "Configuración" },
  ]},
];

function iniciales(nombre) {
  const p = (nombre || "").trim().split(/\s+/).filter(Boolean);
  if (!p.length) return "SS";
  return ((p[0][0] || "") + (p[1]?.[0] || "")).toUpperCase();
}

export default function App() {
  const [nav, setNav] = useState("nueva");
  const [health, setHealth] = useState(null);
  const usuario = loadFirmantes().analista_nombre || "Select Shop MB";

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ ok: false }));
  }, []);

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo-box">
            <img src="/selectshop_logo.png" alt="Select Shop" />
          </div>
          <small>Pagos corporativos</small>
        </div>

        {GRUPOS.map((g) => (
          <div key={g.cat}>
            <div className="cat">{g.cat}</div>
            {g.items.map((n) => (
              <button
                key={n.key}
                className={"nav" + (nav === n.key ? " active" : "")}
                onClick={() => setNav(n.key)}
              >
                {n.label}
              </button>
            ))}
          </div>
        ))}

        <div className="spacer" />

        <div className="userbox">
          <div className="avatar">{iniciales(usuario)}</div>
          <div>
            <div className="nm">{usuario}</div>
            <div className="st">
              <span className={"dot " + (health?.ok ? "ok" : "off")} />
              <span style={{ color: health?.ok ? "#7bd88f" : "#e98" }}>
                {health?.ok ? "Sistema en línea" : "Sin conexión"}
              </span>
            </div>
          </div>
        </div>
      </aside>

      <main className="content">
        {nav === "nueva" && <NuevaSolicitud health={health} />}
        {nav === "historial" && <Historial health={health} />}
        {nav === "calendario" && <Calendario health={health} />}
        {nav === "config" && <Configuracion health={health} onHealth={setHealth} />}
      </main>
    </div>
  );
}
