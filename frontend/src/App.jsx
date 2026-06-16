import { useState, useEffect } from "react";
import { api } from "./api";
import NuevaSolicitud from "./pages/NuevaSolicitud";
import Historial from "./pages/Historial";
import Calendario from "./pages/Calendario";
import Configuracion from "./pages/Configuracion";

const NAV = [
  { key: "nueva", label: "Nueva Solicitud", icon: "📝" },
  { key: "historial", label: "Historial", icon: "📋" },
  { key: "calendario", label: "Alertas / Calendario", icon: "🔔" },
  { key: "config", label: "Configuración", icon: "⚙️" },
];

export default function App() {
  const [nav, setNav] = useState("nueva");
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ ok: false }));
  }, []);

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          GestorPagos
          <small>Grupo Marcovich · IT</small>
        </div>
        <div className="cat">Menú</div>
        {NAV.map((n) => (
          <button
            key={n.key}
            className={"nav" + (nav === n.key ? " active" : "")}
            onClick={() => setNav(n.key)}
          >
            <span>{n.icon}</span> {n.label}
          </button>
        ))}
        <div className="spacer" />
        <div className="status">
          <div>
            <span className={"dot " + (health?.ok ? "ok" : "off")} />
            API {health?.ok ? "conectada" : "sin conexión"}
          </div>
          <div>
            <span className={"dot " + (health?.groq_configurada ? "ok" : "off")} />
            Groq OCR
          </div>
          <div>
            <span className={"dot " + (health?.db_configurada ? "ok" : "off")} />
            Base de datos
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
