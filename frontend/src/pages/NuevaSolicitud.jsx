import { useState, useEffect, useRef } from "react";
import { api } from "../api";
import { loadFirmantes, saveFirmantes, MESES } from "../store";

const NOM_CORTO = {
  "BH. BE HEALTHY COMERCIALIZADORA": "BH",
  "BH SOLAR": "BH SOL",
  "BLOOM & BLUSH": "B&B",
  "COMERCIALIZADORA DE MARCAS JSB": "JSB",
  "COMERCIALIZADORA ONLINE NH": "NH",
  "ENFERMERAS UNIDAS PLUS": "EUP",
  "GOLDEN YEARS MANAGEMENT": "GYM",
  "MB COMERCIALIZADORA EN LINEA": "MB",
  "MOSAIC CARE & HEALTH": "MH&C",
  "SELECT SHOP MB": "SSMB",
  "SM DISTRIBUIDORA DIGITAL": "SMD",
  "INMOBILIARIA EISHEL": "EISH",
  "ALEGARAT": "ALGT",
  "ZONA ZELU": "ZZ",
  "DONKERTECH": "DNKT",
  "MW MED SUPPLY MEDICAL": "MW MED",
};

const MESES_ABREV = {
  enero: "ENE", febrero: "FEB", marzo: "MAR", abril: "ABR",
  mayo: "MAY", junio: "JUN", julio: "JUL", agosto: "AGO",
  septiembre: "SEP", octubre: "OCT", noviembre: "NOV", diciembre: "DIC",
};

const SUFIJOS_LEGALES = /\s+(SAB\s+DE\s+CV|SAPI\s+DE\s+CV|SA\s+DE\s+CV|S\.A\.\s+DE\s+C\.V\.|SA\s+DE\s+C\.V\.)$/i;

function nombrePdf(datos) {
  const empresa = (datos.empresa || "").toUpperCase();
  let nomCorto = "";
  for (const [k, v] of Object.entries(NOM_CORTO)) {
    if (empresa.includes(k.toUpperCase()) || k.toUpperCase().startsWith(empresa.slice(0, 10))) {
      nomCorto = v; break;
    }
  }
  if (!nomCorto) nomCorto = empresa.split(" ")[0] || "";

  const prov = (datos.proveedor_nombre || "PAGO").toUpperCase().replace(SUFIJOS_LEGALES, "").trim();

  const fecha = datos.fecha_proceso || new Date().toLocaleDateString("es-MX");
  let fechaStr = "";
  try { const [d, m, y] = fecha.split("/"); fechaStr = `${d}${m}${y.slice(-2)}`; }
  catch { fechaStr = fecha.replace(/\//g, ""); }

  const mesRaw = (datos.mes_pago || datos.mes_presupuesto || "").toLowerCase();
  const mesAbrev = MESES_ABREV[mesRaw] || mesRaw.slice(0, 3).toUpperCase();

  return ["Solicitud", nomCorto, prov, fechaStr, mesAbrev].filter(Boolean).join("_") + ".pdf";
}

const FORM_VACIO = {
  empresa: "", sucursal: "", centro_costos: "", direccion: "",
  proveedor_nombre: "", motivo_pago: "", folio_cfdi: "", notas_credito: "",
  monto_total: "", banco: "", clabe: "", no_cuenta: "",
  observaciones: "", mes_presupuesto: "", mes_pago: "", anio: new Date().getFullYear(),
};

const MAP_OCR = {
  proveedor: "proveedor_nombre", empresa_cliente: "empresa", sucursal: "sucursal",
  no_cuenta: "no_cuenta", factura_no: "folio_cfdi", monto: "monto_total",
  banco: "banco", clabe: "clabe", observaciones: "observaciones",
  motivo_pago: "motivo_pago", mes_presupuesto: "mes_presupuesto", mes_pago: "mes_pago",
};

export default function NuevaSolicitud({ health }) {
  const [tipoDoc, setTipoDoc] = useState("recibo");      // recibo | factura
  const [modo, setModo] = useState(null);                // null | ocr | manual
  const [file, setFile] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [form, setForm] = useState(FORM_VACIO);
  const [firm, setFirm] = useState(loadFirmantes);
  const [cat, setCat] = useState({ empresas: [], proveedores: [], bancos: [] });
  const [msg, setMsg] = useState(null);
  const [debug, setDebug] = useState("");
  const [pdfUrl, setPdfUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef();

  useEffect(() => {
    if (!health?.db_configurada) return;
    Promise.all([api.empresas(), api.proveedores(), api.bancos()])
      .then(([empresas, proveedores, bancos]) => setCat({ empresas, proveedores, bancos }))
      .catch(() => {});
  }, [health]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const setF = (k, v) => setFirm((f) => ({ ...f, [k]: v }));
  const bloqueado = modo === null;

  async function escanear() {
    if (!file) { setMsg({ t: "warn", m: "Selecciona un archivo PDF o imagen primero." }); return; }
    setScanning(true); setMsg(null); setDebug("");
    try {
      const r = await api.escanear(file, tipoDoc);
      const next = { ...form };
      for (const [src, dst] of Object.entries(MAP_OCR)) if (r[src]) next[dst] = r[src];
      setForm(next);
      setDebug(r.debug_log || "");
      setMsg(r.error
        ? { t: "warn", m: "Lectura parcial: " + r.error + ". Revisa y completa los campos." }
        : { t: "ok", m: "Recibo escaneado. Revisa los campos antes de generar la solicitud." });
    } catch (e) {
      setMsg({ t: "err", m: "Error al escanear: " + e.message });
    } finally { setScanning(false); }
  }

  function datosPDF() {
    saveFirmantes(firm);
    return { ...form, ...firm, fecha_proceso: new Date().toLocaleDateString("es-MX") };
  }

  async function vistaPrevia() {
    setBusy(true); setMsg(null);
    try {
      const blob = await api.generarPdf(datosPDF());
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
      setPdfUrl(URL.createObjectURL(blob));
      setMsg({ t: "ok", m: "Vista previa generada abajo." });
    } catch (e) { setMsg({ t: "err", m: "Error generando PDF: " + e.message }); }
    finally { setBusy(false); }
  }

  async function generarSolicitud() {
    setBusy(true); setMsg(null);
    try {
      const blob = await api.generarPdf(datosPDF());
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
      const url = URL.createObjectURL(blob);
      setPdfUrl(url);
      // Guardar en historial si hay BD
      if (health?.db_configurada) {
        const monto = parseFloat(String(form.monto_total).replace(/,/g, "")) || 0;
        await api.crearPago({
          ...form, ...firm, monto_total: monto,
          notas_credito: parseFloat(String(form.notas_credito).replace(/,/g, "")) || 0,
          mes: MESES.indexOf(form.mes_pago) || null,
          anio: parseInt(form.anio) || new Date().getFullYear(),
          fecha_proceso: new Date().toISOString().slice(0, 10),
        });
        setMsg({ t: "ok", m: "Solicitud generada y guardada en el historial." });
      } else {
        setMsg({ t: "ok", m: "Solicitud generada (sin guardar: BD no configurada)." });
      }
      const a = document.createElement("a");
      a.href = url; a.download = nombrePdf(datosPDF()); a.click();
    } catch (e) { setMsg({ t: "err", m: "Error: " + e.message }); }
    finally { setBusy(false); }
  }

  function nuevaSolicitud() {
    setForm(FORM_VACIO); setFile(null); setDebug(""); setMsg(null); setModo(null);
    if (pdfUrl) { URL.revokeObjectURL(pdfUrl); setPdfUrl(""); }
    if (fileRef.current) fileRef.current.value = "";
  }

  const empresasU = [...new Set(cat.empresas.map((e) => e.empresa).filter(Boolean))];
  const sucursalesU = [...new Set(cat.empresas.map((e) => e.sucursal).filter(Boolean))];
  const bancosU = cat.bancos.map((b) => b.nombre);
  const provsU = cat.proveedores.map((p) => p.nombre);

  return (
    <>
      <h1 className="page-title">Nueva solicitud de pago</h1>

      {/* Tipo de documento + modo */}
      <div className="card flat">
        <div className="radio-row">
          <strong style={{ marginRight: 4 }}>Tipo de documento:</strong>
          <label><input type="radio" name="tipo" checked={tipoDoc === "recibo"} onChange={() => setTipoDoc("recibo")} /> Recibo de servicio</label>
          <label><input type="radio" name="tipo" checked={tipoDoc === "factura"} onChange={() => setTipoDoc("factura")} /> Factura CFDI</label>
        </div>

        <p style={{ fontWeight: 600, margin: "16px 0 8px" }}>¿Cómo vas a llenar la solicitud?</p>
        <div className="mode-row">
          <button className={"btn" + (modo === "ocr" ? "" : " ghost")} onClick={() => setModo("ocr")}>
            Subir recibo del proveedor (PDF/imagen)
          </button>
          <span className="muted">o</span>
          <button className={"btn" + (modo === "manual" ? " dark" : " ghost")} onClick={() => setModo("manual")}>
            Llenado manual
          </button>
        </div>

        {modo === "ocr" && (
          <div className="row" style={{ alignItems: "flex-end", marginTop: 14 }}>
            <div className="field" style={{ flex: 2 }}>
              <label>Archivo (PDF o imagen)</label>
              <input ref={fileRef} type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={(e) => setFile(e.target.files[0])} />
            </div>
            <div className="field" style={{ flex: 0, minWidth: 150 }}>
              <button className="btn" onClick={escanear} disabled={scanning}>
                {scanning ? <><span className="spinner" /> Escaneando…</> : "Escanear con OCR"}
              </button>
            </div>
          </div>
        )}
        {modo === null && <div className="modo-hint">← Elige un modo para habilitar el formulario</div>}
        {modo === "ocr" && !health?.groq_configurada && (
          <div className="alert warn">Groq OCR no está configurado en el servidor.</div>
        )}
        {msg && <div className={"alert " + (msg.t === "ok" ? "ok" : msg.t === "warn" ? "warn" : "err")}>{msg.m}</div>}
        {debug && <details><summary className="muted" style={{ cursor: "pointer", fontSize: 12 }}>Ver log del OCR</summary>
          <pre style={{ fontSize: 11, whiteSpace: "pre-wrap", color: "#6b7280" }}>{debug}</pre></details>}
      </div>

      <fieldset disabled={bloqueado} style={{ border: 0, padding: 0, margin: 0, opacity: bloqueado ? 0.55 : 1 }}>
        <div className="card">
          <h3>Datos de la empresa</h3>
          <div className="row">
            <Field l="Empresa" v={form.empresa} on={(v) => set("empresa", v)} list="l-emp" opts={empresasU} />
            <Field l="Sucursal" v={form.sucursal} on={(v) => set("sucursal", v)} list="l-suc" opts={sucursalesU} />
          </div>
          <div className="row">
            <Field l="Centro de costos" v={form.centro_costos} on={(v) => set("centro_costos", v)} />
            <Field l="Dirección" v={form.direccion} on={(v) => set("direccion", v)} />
          </div>
        </div>

        <div className="card">
          <h3>Beneficiario / Proveedor</h3>
          <div className="row">
            <Field l="Proveedor" v={form.proveedor_nombre} on={(v) => set("proveedor_nombre", v)} list="l-prov" opts={provsU} />
            <Field l="Motivo de pago" v={form.motivo_pago} on={(v) => set("motivo_pago", v)} />
          </div>
        </div>

        <div className="card">
          <h3>Datos de CFDI</h3>
          <div className="row">
            <Field l="No. Folio(s) CFDI / Folio Fiscal" v={form.folio_cfdi} on={(v) => set("folio_cfdi", v)} />
            <Field l="Nota(s) de crédito" v={form.notas_credito} on={(v) => set("notas_credito", v)} />
          </div>
        </div>

        <div className="card">
          <h3>Datos de pago</h3>
          <div className="field" style={{ maxWidth: 260 }}>
            <label>Importe total (MXN)</label>
            <input value={form.monto_total} onChange={(e) => set("monto_total", e.target.value)} />
          </div>
          <div className="row">
            <Field l="Banco" v={form.banco} on={(v) => set("banco", v)} list="l-bco" opts={bancosU} />
            <Field l="CLABE" v={form.clabe} on={(v) => set("clabe", v)} />
            <Field l="No. cuenta" v={form.no_cuenta} on={(v) => set("no_cuenta", v)} />
          </div>
          <div className="field">
            <label>Observaciones / Referencia</label>
            <textarea value={form.observaciones} onChange={(e) => set("observaciones", e.target.value)} />
          </div>
        </div>

        <div className="card">
          <h3>Exclusivo — Departamento de Finanzas</h3>
          <div className="row">
            <SelectMes l="Mes presupuesto" v={form.mes_presupuesto} on={(v) => set("mes_presupuesto", v)} />
            <SelectMes l="Mes pago" v={form.mes_pago} on={(v) => set("mes_pago", v)} />
            <Field l="Año" v={form.anio} on={(v) => set("anio", v)} />
          </div>
        </div>

        <div className="card">
          <h3>Nombres de firmantes</h3>
          <div className="row">
            <Field l="Solicitante / Analista" v={firm.analista_nombre} on={(v) => setF("analista_nombre", v)} />
            <Field l="Gerente de Sistemas" v={firm.gerente_nombre} on={(v) => setF("gerente_nombre", v)} />
          </div>
          <div className="row">
            <Field l="Vo. Bo. (Finanzas)" v={firm.visto_bno} on={(v) => setF("visto_bno", v)} />
            <Field l="Depto. Finanzas Presupuesto" v={firm.depto_finanzas} on={(v) => setF("depto_finanzas", v)} />
          </div>
          <div className="row">
            <Field l="Dirección Financiera" v={firm.dir_financiera} on={(v) => setF("dir_financiera", v)} />
            <Field l="Dirección General" v={firm.dir_general} on={(v) => setF("dir_general", v)} />
          </div>
        </div>
      </fieldset>

      <datalist id="l-emp">{empresasU.map((o) => <option key={o} value={o} />)}</datalist>
      <datalist id="l-suc">{sucursalesU.map((o) => <option key={o} value={o} />)}</datalist>
      <datalist id="l-prov">{provsU.map((o) => <option key={o} value={o} />)}</datalist>
      <datalist id="l-bco">{bancosU.map((o) => <option key={o} value={o} />)}</datalist>

      {/* Barra de acciones */}
      <div className="card flat actions">
        <button className="btn dark" onClick={vistaPrevia} disabled={bloqueado || busy}>Vista previa (PDF)</button>
        <button className="btn" onClick={generarSolicitud} disabled={bloqueado || busy}>
          {busy ? <><span className="spinner" /> Generando…</> : "Generar Solicitud de Pago (PDF)"}
        </button>
        <button className="btn ghost" onClick={nuevaSolicitud}>Nueva solicitud</button>
      </div>

      {pdfUrl && (
        <div className="card">
          <h3>Vista previa del PDF</h3>
          <iframe className="preview-frame" src={pdfUrl} title="PDF" />
        </div>
      )}
    </>
  );
}

function Field({ l, v, on, list, opts }) {
  return (
    <div className="field">
      <label>{l}</label>
      <input value={v} list={list} onChange={(e) => on(e.target.value)} />
      {list && opts && <datalist id={list}>{opts.map((o) => <option key={o} value={o} />)}</datalist>}
    </div>
  );
}

function SelectMes({ l, v, on }) {
  return (
    <div className="field">
      <label>{l}</label>
      <select value={v} onChange={(e) => on(e.target.value)}>
        <option value="">—</option>
        {MESES.slice(1).map((m) => <option key={m} value={m}>{m}</option>)}
      </select>
    </div>
  );
}
