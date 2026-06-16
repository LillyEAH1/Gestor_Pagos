import { useState, useEffect, useRef } from "react";
import { api } from "../api";
import { loadFirmantes, MESES } from "../store";

const FORM_VACIO = {
  empresa: "", sucursal: "", centro_costos: "", direccion: "",
  proveedor_nombre: "", motivo_pago: "", folio_cfdi: "", notas_credito: "",
  monto_total: "", importe_letra: "", banco: "", clabe: "", no_cuenta: "",
  forma_pago: "TRANSFERENCIA", observaciones: "", mes_presupuesto: "", mes_pago: "",
};

const MAP_OCR = {
  proveedor: "proveedor_nombre", empresa_cliente: "empresa", sucursal: "sucursal",
  no_cuenta: "no_cuenta", factura_no: "folio_cfdi", monto: "monto_total",
  banco: "banco", clabe: "clabe", observaciones: "observaciones",
  motivo_pago: "motivo_pago", mes_presupuesto: "mes_presupuesto", mes_pago: "mes_pago",
};

export default function NuevaSolicitud({ health }) {
  const [tipoDoc, setTipoDoc] = useState("recibo");
  const [file, setFile] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [form, setForm] = useState(FORM_VACIO);
  const [cat, setCat] = useState({ empresas: [], proveedores: [], bancos: [] });
  const [msg, setMsg] = useState(null);
  const [debug, setDebug] = useState("");
  const [pdfUrl, setPdfUrl] = useState("");
  const [busyPdf, setBusyPdf] = useState(false);
  const fileRef = useRef();

  useEffect(() => {
    if (!health?.db_configurada) return;
    Promise.all([api.empresas(), api.proveedores(), api.bancos()])
      .then(([empresas, proveedores, bancos]) => setCat({ empresas, proveedores, bancos }))
      .catch(() => {});
  }, [health]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  async function escanear() {
    if (!file) { setMsg({ t: "warn", m: "Selecciona un archivo PDF o imagen primero." }); return; }
    setScanning(true); setMsg(null); setDebug("");
    try {
      const r = await api.escanear(file, tipoDoc);
      const next = { ...form };
      for (const [src, dst] of Object.entries(MAP_OCR)) {
        if (r[src]) next[dst] = r[src];
      }
      setForm(next);
      setDebug(r.debug_log || "");
      setMsg(r.error
        ? { t: "warn", m: "Lectura parcial: " + r.error + ". Revisa y completa los campos." }
        : { t: "ok", m: "Recibo escaneado. Revisa los campos antes de generar el PDF." });
    } catch (e) {
      setMsg({ t: "err", m: "Error al escanear: " + e.message });
    } finally {
      setScanning(false);
    }
  }

  async function calcularLetra() {
    const monto = parseFloat(String(form.monto_total).replace(/,/g, ""));
    if (!monto) return;
    try { const r = await api.numeroLetra(monto); set("importe_letra", r.letra); } catch {}
  }

  async function generarPdf() {
    setBusyPdf(true); setMsg(null);
    try {
      const datos = {
        ...form,
        ...loadFirmantes(),
        fecha_proceso: new Date().toLocaleDateString("es-MX"),
      };
      const blob = await api.generarPdf(datos);
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
      setPdfUrl(URL.createObjectURL(blob));
      setMsg({ t: "ok", m: "PDF generado. Vista previa abajo." });
    } catch (e) {
      setMsg({ t: "err", m: "Error generando PDF: " + e.message });
    } finally {
      setBusyPdf(false);
    }
  }

  async function guardar() {
    try {
      const monto = parseFloat(String(form.monto_total).replace(/,/g, "")) || 0;
      const payload = {
        ...form,
        monto_total: monto,
        notas_credito: parseFloat(String(form.notas_credito).replace(/,/g, "")) || 0,
        mes: MESES.indexOf(form.mes_pago) || null,
        anio: new Date().getFullYear(),
        fecha_proceso: new Date().toISOString().slice(0, 10),
        ...loadFirmantes(),
      };
      const r = await api.crearPago(payload);
      setMsg({ t: "ok", m: `Guardado en historial (#${r.id}).` });
    } catch (e) {
      setMsg({ t: "err", m: "No se pudo guardar: " + e.message });
    }
  }

  function limpiar() {
    setForm(FORM_VACIO); setFile(null); setDebug(""); setMsg(null);
    if (pdfUrl) { URL.revokeObjectURL(pdfUrl); setPdfUrl(""); }
    if (fileRef.current) fileRef.current.value = "";
  }

  const empresasU = [...new Set(cat.empresas.map((e) => e.empresa).filter(Boolean))];
  const sucursalesU = [...new Set(cat.empresas.map((e) => e.sucursal).filter(Boolean))];
  const bancosU = cat.bancos.map((b) => b.nombre);
  const provsU = cat.proveedores.map((p) => p.nombre);

  return (
    <>
      <h1 className="page-title">Nueva Solicitud de Pago</h1>
      <p className="page-sub">Escanea un recibo o factura, revisa los datos y genera el PDF oficial.</p>

      <div className="card">
        <h3>1 · Escanear documento</h3>
        <div className="seg" style={{ marginBottom: 14 }}>
          {[["recibo", "Recibo"], ["telmex", "Recibo Telmex"], ["factura", "Factura CFDI"]].map(([v, l]) => (
            <button key={v} className={tipoDoc === v ? "active" : ""} onClick={() => setTipoDoc(v)}>{l}</button>
          ))}
        </div>
        <div className="row" style={{ alignItems: "flex-end" }}>
          <div className="field" style={{ flex: 2 }}>
            <label>Archivo (PDF o imagen)</label>
            <input ref={fileRef} type="file" accept=".pdf,.png,.jpg,.jpeg"
              onChange={(e) => setFile(e.target.files[0])} />
          </div>
          <div className="field" style={{ flex: 0, minWidth: 160 }}>
            <button className="btn" onClick={escanear} disabled={scanning}>
              {scanning ? <><span className="spinner" /> Escaneando…</> : "Escanear"}
            </button>
          </div>
        </div>
        {!health?.groq_configurada && (
          <div className="alert warn">Groq OCR no está configurado en el servidor — el escaneo puede no funcionar.</div>
        )}
        {msg && <div className={"alert " + (msg.t === "ok" ? "ok" : msg.t === "warn" ? "warn" : "err")}>{msg.m}</div>}
        {debug && <details><summary className="muted" style={{ cursor: "pointer", fontSize: 12 }}>Ver log del OCR</summary>
          <pre style={{ fontSize: 11, whiteSpace: "pre-wrap", color: "#6b7280" }}>{debug}</pre></details>}
      </div>

      <div className="card">
        <h3>2 · Datos de la solicitud</h3>
        <div className="row">
          <Field l="Empresa" v={form.empresa} on={(v) => set("empresa", v)} list="l-emp" opts={empresasU} />
          <Field l="Sucursal" v={form.sucursal} on={(v) => set("sucursal", v)} list="l-suc" opts={sucursalesU} />
        </div>
        <div className="row">
          <Field l="Centro de costos" v={form.centro_costos} on={(v) => set("centro_costos", v)} />
          <Field l="Dirección" v={form.direccion} on={(v) => set("direccion", v)} />
        </div>
        <div className="row">
          <Field l="Beneficiario / Proveedor" v={form.proveedor_nombre} on={(v) => set("proveedor_nombre", v)} list="l-prov" opts={provsU} />
          <Field l="Folio CFDI / Factura" v={form.folio_cfdi} on={(v) => set("folio_cfdi", v)} />
        </div>
        <div className="field">
          <label>Motivo de pago</label>
          <input value={form.motivo_pago} onChange={(e) => set("motivo_pago", e.target.value)} />
        </div>
        <div className="row">
          <Field l="Monto total" v={form.monto_total} on={(v) => set("monto_total", v)} onBlur={calcularLetra} />
          <Field l="Notas de crédito" v={form.notas_credito} on={(v) => set("notas_credito", v)} />
        </div>
        <div className="field">
          <label>Importe en letra</label>
          <div style={{ display: "flex", gap: 8 }}>
            <input style={{ flex: 1 }} value={form.importe_letra} onChange={(e) => set("importe_letra", e.target.value)} />
            <button className="btn ghost" type="button" onClick={calcularLetra}>Calcular</button>
          </div>
        </div>
        <div className="row">
          <Field l="Banco" v={form.banco} on={(v) => set("banco", v)} list="l-bco" opts={bancosU} />
          <Field l="CLABE" v={form.clabe} on={(v) => set("clabe", v)} />
          <Field l="No. de cuenta" v={form.no_cuenta} on={(v) => set("no_cuenta", v)} />
        </div>
        <div className="field">
          <label>Observaciones</label>
          <textarea value={form.observaciones} onChange={(e) => set("observaciones", e.target.value)} />
        </div>
        <div className="row">
          <SelectMes l="Mes del presupuesto" v={form.mes_presupuesto} on={(v) => set("mes_presupuesto", v)} />
          <SelectMes l="Mes del pago" v={form.mes_pago} on={(v) => set("mes_pago", v)} />
        </div>

        <div className="btn-row">
          <button className="btn" onClick={generarPdf} disabled={busyPdf}>
            {busyPdf ? <><span className="spinner" /> Generando…</> : "Generar PDF"}
          </button>
          <button className="btn ghost" onClick={guardar} disabled={!health?.db_configurada}
            title={health?.db_configurada ? "" : "Requiere base de datos configurada"}>
            Guardar en historial
          </button>
          <button className="btn ghost" onClick={limpiar}>Limpiar</button>
        </div>
      </div>

      <datalist id="l-emp">{empresasU.map((o) => <option key={o} value={o} />)}</datalist>
      <datalist id="l-suc">{sucursalesU.map((o) => <option key={o} value={o} />)}</datalist>
      <datalist id="l-prov">{provsU.map((o) => <option key={o} value={o} />)}</datalist>
      <datalist id="l-bco">{bancosU.map((o) => <option key={o} value={o} />)}</datalist>

      {pdfUrl && (
        <div className="card">
          <h3>Vista previa del PDF</h3>
          <iframe className="preview-frame" src={pdfUrl} title="PDF" />
          <div className="btn-row">
            <a className="btn" href={pdfUrl} download="Solicitud.pdf">Descargar PDF</a>
          </div>
        </div>
      )}
    </>
  );
}

function Field({ l, v, on, onBlur, list, opts }) {
  return (
    <div className="field">
      <label>{l}</label>
      <input value={v} list={list} onChange={(e) => on(e.target.value)} onBlur={onBlur} />
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
