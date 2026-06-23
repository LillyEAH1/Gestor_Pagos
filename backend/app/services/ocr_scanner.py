"""
ocr_scanner.py (backend) — portado de v60/ocr_scanner.py.

Cambios para correr en servidor (Linux/Render), sin Windows:
- PDF -> imagen: PyMuPDF (fitz) en vez de PowerShell + Windows.Data.Pdf.
- Fallback: extracción regex del texto nativo del PDF (pypdf), en vez de
  Windows.Media.Ocr.
- Trabaja con BYTES (lo que sube el navegador), no rutas de archivo.
- BUGFIX vs v60: ahora SÍ se pasa `texto_crudo` a _normalizar_groq, así los
  "salvavidas regex" funcionan (en v60 nunca recibían el texto -> dead code).

La lógica de prompts, mapas y normalización se conserva intacta.
"""
from __future__ import annotations
import re
import io
import json
import base64
import urllib.request
import urllib.error
from datetime import date

from app.config import get_settings

PROVEEDORES_MAP = {
    "TELMEX":                "TELEFONOS DE MEXICO SAB DE CV",
    "TELEFONOS DE MEXICO":   "TELEFONOS DE MEXICO SAB DE CV",
    "TOTALPLAY":             "TOTAL PLAY TELECOMUNICACIONES SAPI DE CV",
    "TOTAL PLAY":            "TOTAL PLAY TELECOMUNICACIONES SAPI DE CV",
    "IZZI":                  "IZZI NEGOCIOS",
    "DIGITAL COPY":          "DIGITAL COPY TECHNOLOGIES",
    "CFE":                   "CFE COMISION FEDERAL DE ELECTRICIDAD",
    "COMISION FEDERAL":      "CFE COMISION FEDERAL DE ELECTRICIDAD",
    "TELCEL":                "RADIOMOVIL DIPSA SA DE CV",
    "RADIOMOVIL":            "RADIOMOVIL DIPSA SA DE CV",
    "AT&T":                  "AT&T MEXICO",
    "BICENTEL":              "BICENTEL",
    "UNIFIED KNOWLEDGE":     "UNIFIED KNOWLEDGE AND ASSOCIATES",
    "UNIKA":                 "UNIFIED KNOWLEDGE AND ASSOCIATES",
    "INNOVACION ORTOPEDICA": "INNOVACION ORTOPEDICA SA DE CV",
}

EMPRESAS_CONOCIDAS = [
    "MW MED SUPPLY MEDICAL", "BLOOM & BLUSH", "BH. BE HEALTHY COMERCIALIZADORA",
    "BH BE HEALTHY", "BH SOLAR", "ENFERMERAS UNIDAS PLUS",
    "GOLDEN YEARS MANAGEMENT", "MB COMERCIALIZADORA EN LINEA",
    "COMERCIALIZADORA DE MARCAS JSB", "COMERCIALIZADORA ONLINE NH",
    "SELECT SHOP MB", "SM DISTRIBUIDORA DIGITAL", "MOSAIC CARE & HEALTH",
    "INMOBILIARIA EISHEL", "ALEGARAT", "ZONA ZELU", "DONKERTECH",
]

BANCO_MAP = {
    "BANCOMER": "BBVA", "BBVA": "BBVA",
    "BANAMEX": "BANAMEX", "CITIBANAMEX": "BANAMEX",
    "BANORTE": "BANORTE", "HSBC": "HSBC",
    "SANTANDER": "SANTANDER", "SCOTIABANK": "SCOTIABANK",
    "BANCO AZTECA": "AZTECA", "AZTECA": "AZTECA",
    "INBURSA": "INBURSA", "BANREGIO": "BANREGIO",
    "BAJIO": "BAJIO", "STP": "STP", "BASE": "BASE",
}

PREFIJO_BANCO = {
    "012": "BBVA", "021": "HSBC", "002": "BANAMEX", "014": "SANTANDER",
    "044": "SCOTIABANK", "072": "BANORTE", "058": "BANREGIO",
    "127": "AZTECA", "036": "INBURSA", "030": "BAJIO", "646": "STP",
}

GROQ_PROMPT_RECIBO = """Eres un asistente experto en leer RECIBOS de servicios mexicanos (Telmex, Totalplay, Telcel, Izzi, Bicentel, Digital Copy, etc.).
REGLAS ABSOLUTAS — sin excepción:
1. SOLO analiza la PRIMERA PÁGINA. Ignora publicidad y páginas adicionales.
2. EMPRESA_CLIENTE: Lee ESTRICTAMENTE del encabezado, sección "Nombre o Razón Social" o "Cliente". NO inventes ni mezcles nombres. Si dice "ENFERMERAS UNIDAS PLUS" pon exactamente eso.
3. SUCURSAL: Es la dirección del cliente en el recibo (ej: "Iztapalapa", "Nebraska 170"). NO es la dirección del proveedor.
4. FACTURA_NO: ÚNICAMENTE el número junto a "Factura No." PROHIBIDO usar teléfono, cuenta o UUID. Si no hay, deja "".
5. OBSERVACIONES: Lee el bloque del código de barras al FINAL. Extrae banco, DV y número del código. Formato: "BBVA DV 7 REFERENCIA 5556851480001349004". Si dice BANCOMER escribe BBVA.
6. MES_PRESUPUESTO: Mes de facturación del recibo (ej: Abril).
7. MES_PAGO: Mes siguiente al de facturación (ej: Mayo).
8. MOTIVO_PAGO: Construye "SERV CTA [teléfono/cuenta] [MES_PRESUPUESTO] [AÑO]". Usa el teléfono de la carátula, NO el del código de barras.
9. NO_CUENTA (interno): teléfono o número de cuenta de la carátula. BANCO (interno): banco para depósito. DV (interno): dígito verificador. REFERENCIA_20_DIGITOS (interno): número de 20 dígitos del código de barras.

FORMATO JSON — Devuelve SOLO este JSON válido, sin markdown ni texto extra:
{
  "empresa_cliente": "Empresa que paga (del encabezado, exacto)",
  "sucursal": "Dirección o zona del cliente",
  "proveedor": "Empresa que presta el servicio",
  "motivo_pago": "SERV CTA [telefono_10_digitos] [MES] [AÑO]",
  "factura_no": "Número de Factura No. Si no hay, vacío.",
  "monto": "Total a pagar en decimal",
  "observaciones": "BBVA DV [n] REFERENCIA [codigo_barras_largo]",
  "mes_presupuesto": "Mes de facturación",
  "mes_pago": "Mes de pago",
  "anio_factura": "Año",
  "banco": "interno",
  "no_cuenta": "interno",
  "dv": "interno",
  "referencia_20_digitos": "interno"
}"""

GROQ_PROMPT_TELMEX = """Eres un asistente de extracción de datos. Analiza este recibo de Telmex y devuelve ÚNICAMENTE un JSON válido, sin texto adicional ni markdown.

DÓNDE ESTÁ CADA CAMPO EN EL RECIBO:
- empresa_cliente → encabezado IZQUIERDO: "Nombre o Razón Social" o "CLIENTE". NUNCA es Telmex.
- sucursal       → ciudad o colonia de la dirección del cliente (ej: "IZTAPALAPA", "NEBRASKA").
- no_cuenta      → encabezado DERECHO: campo explícito "Teléfono:" — 10 dígitos. NO tomes el número del código de barras.
- factura_no     → encabezado DERECHO: campo "Factura No." o "NO. FOLIO(S) DE CFD(I)s". Solo dígitos.
- monto          → encabezado DERECHO: "Total a Pagar" o "Saldo al Corte". Solo el número.
- mes_factura    → encabezado DERECHO: campo "Mes de Facturación".
- anio_factura   → año del recibo (4 dígitos).
- banco          → siempre BBVA.
- dv             → SECCIÓN INFERIOR (hoja de pago, cerca del código de barras): el ÚNICO dígito que sigue a las letras "DV". Ejemplo: "DV 7" → "7".
- referencia_20_digitos → SECCIÓN INFERIOR: el número de exactamente 20 dígitos impreso DEBAJO del código de barras.

Ejemplo guía (mapeo campo por campo):

{
  "empresa_cliente": "ENFERMERAS UNIDAS PLUS",
  "sucursal": "IZTAPALAPA",
  "proveedor": "TELEFONOS DE MEXICO SAB DE CV",
  "no_cuenta": "5556855148",
  "factura_no": "130126040074041",
  "monto": "1349.00",
  "banco": "BBVA",
  "dv": "7",
  "mes_factura": "Abril",
  "anio_factura": "2026",
  "referencia_20_digitos": "55568551480001349004"
}
"""

GROQ_PROMPT_FACTURA = """Eres un asistente experto en leer FACTURAS (CFDIs) mexicanas.
REGLAS OBLIGATORIAS:
1. SOLO analiza la PRIMERA PÁGINA. Si un campo no existe pon "".
2. EMPRESA_CLIENTE: La empresa que RECIBE y PAGA. Busca en "Razón Social del receptor" o "CLIENTE".
3. FACTURA_NO: El número de factura corto (ej: FA-000000000564109722). PROHIBIDO el UUID/Folio Fiscal.
4. MOTIVO_PAGO: Descripción del concepto de la factura.
5. OBSERVACIONES: Datos relevantes de pago (banco, CLABE, referencia si existen).
6. MES_PRESUPUESTO: Mes de la fecha de emisión.
7. MES_PAGO: Mes en que se realizará el pago.

FORMATO JSON — Devuelve SOLO este JSON válido, sin markdown:
{
  "empresa_cliente": "Empresa que paga",
  "sucursal": "Dirección o sede del cliente",
  "proveedor": "Empresa que emite la factura",
  "motivo_pago": "Descripción del concepto",
  "factura_no": "Número de factura corto. NO UUID.",
  "monto": "Total a pagar en decimal",
  "observaciones": "Datos de pago: banco, CLABE, referencia si existen",
  "mes_presupuesto": "Mes de la factura",
  "mes_pago": "Mes de pago",
  "anio_factura": "Año",
  "banco": "interno",
  "clabe": "interno"
}"""


# ── Entradas públicas ────────────────────────────────────────────────────

def _autodetectar_tipo(texto: str) -> str:
    """Detecta el tipo de documento por palabras clave en el texto nativo del PDF."""
    t = texto.upper()
    if "TELEFONOS DE MEXICO" in t or "TELMEX" in t:
        return "telmex"
    return "recibo"


def escanear_recibo_bytes(data: bytes, filename: str,
                          groq_api_key: str = "", tipo_doc: str = "recibo") -> dict:
    """
    Escanea un recibo/factura recibido como bytes (lo que sube el navegador).
    Devuelve el dict de campos normalizados + 'debug_log'.
    """
    log: list[str] = []
    if not groq_api_key:
        groq_api_key = get_settings().groq_api_key
        log.append("Key de entorno" if groq_api_key else "Sin Groq API Key configurada")

    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    texto_nativo = ""
    img_bytes = b""
    mime = "image/png"

    if ext == ".pdf":
        texto_nativo = _pdf_texto_nativo(data)
        log.append(f"Texto nativo extraído: {len(texto_nativo.strip())} chars")
        img_bytes, mime = _pdf_a_imagen(data)
        if img_bytes:
            log.append(f"PDF->JPEG OK ({len(img_bytes) // 1024} KB)")
        else:
            log.append("PDF->JPEG falló")
            if len(texto_nativo.strip()) > 50:
                r = _extraer_campos_texto(texto_nativo)
                r["debug_log"] = "\n".join(log) + "\nFallback: extracción por texto"
                return r
            return _vacio("No se pudo convertir el PDF a imagen", log)
    else:
        img_bytes = data
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
        log.append(f"Imagen directa: {ext or '(sin extensión)'}")

    # Auto-detectar proveedor cuando el frontend manda tipo_doc genérico
    if tipo_doc == "recibo" and texto_nativo:
        tipo_doc = _autodetectar_tipo(texto_nativo)
        log.append(f"Tipo detectado automáticamente: {tipo_doc}")

    if groq_api_key and img_bytes:
        log.append(f"Llamando a Groq Vision (prompt: {tipo_doc})...")
        resultado, groq_log = _groq_vision(img_bytes, mime, groq_api_key, tipo_doc,
                                           texto_crudo=texto_nativo)
        log.extend(groq_log)
        if resultado.get("proveedor") or resultado.get("monto"):
            log.append("✓ Groq extrajo campos")
            resultado["debug_log"] = "\n".join(log)
            return resultado
        log.append("Groq no extrajo campos")

    # Fallback cross-platform: regex sobre el texto nativo del PDF
    if texto_nativo and len(texto_nativo.strip()) > 20:
        log.append("Fallback: extracción regex del texto nativo")
        r = _extraer_campos_texto(texto_nativo)
        r["debug_log"] = "\n".join(log)
        return r

    return _vacio("No se pudo leer el recibo", log)


def probar_groq_conexion(api_key: str) -> tuple[bool, str]:
    """Prueba la conexión a Groq con texto (rápido, sin imagen)."""
    try:
        payload = json.dumps({
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": "Responde solo: OK"}],
            "max_tokens": 5,
        }).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "groq-python/0.11.0",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        resp = data["choices"][0]["message"]["content"].strip()
        return True, f"✓ Groq conectado. Respuesta: {resp}"
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        if e.code == 401:
            return False, "✗ API Key inválida o expirada (401)"
        if e.code == 429:
            return False, "✗ Límite de requests alcanzado (429)"
        return False, f"✗ Error HTTP {e.code}: {body[:150]}"
    except Exception as e:
        return False, f"✗ Error de conexión: {str(e)[:150]}"


# ── PDF / imagen (cross-platform) ────────────────────────────────────────

def _pdf_texto_nativo(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages[:2])
    except Exception:
        return ""


def _pdf_a_imagen(data: bytes, ancho_px: int = 1024) -> tuple[bytes, str]:
    """Rasteriza la primera página del PDF a JPEG usando PyMuPDF.
    Devuelve (bytes, mime). JPEG reduce el payload ~20x vs PNG a 1800px."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=data, filetype="pdf")
        page = doc.load_page(0)
        zoom = ancho_px / page.rect.width if page.rect.width else 1.5
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        out = pix.tobytes("jpeg", jpg_quality=88)
        doc.close()
        return out, "image/jpeg"
    except Exception:
        return b"", "image/jpeg"


# ── Groq Vision ──────────────────────────────────────────────────────────

def _groq_vision(img_bytes: bytes, mime: str, api_key: str,
                 tipo_doc: str = "recibo", texto_crudo: str = "") -> tuple[dict, list]:
    log: list[str] = []
    try:
        img_b64 = base64.b64encode(img_bytes).decode()
        log.append(f"Imagen base64: {len(img_b64) // 1024} KB")

        system = (GROQ_PROMPT_TELMEX if tipo_doc == "telmex"
                  else GROQ_PROMPT_FACTURA if tipo_doc == "factura"
                  else GROQ_PROMPT_RECIBO)

        payload = json.dumps({
            "model": get_settings().groq_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
                    {"type": "text",
                     "text": "Extrae los campos de este recibo en JSON. "
                             "Identifica el nombre de la empresa cliente (no el proveedor), "
                             "el numero de telefono/cuenta, el banco y la referencia de pago."},
                ]},
            ],
            "max_tokens": 700,
            "temperature": 0,
        }).encode("utf-8")
        log.append(f"Payload: {len(payload) // 1024} KB — enviando a Groq...")

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "groq-python/0.11.0",
            },
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read())

        content = data["choices"][0]["message"]["content"].strip()
        log.append(f"Groq respondió ({len(content)} chars)")
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.MULTILINE).strip()
        parsed = json.loads(content)
        log.append(f"JSON parseado: {list(parsed.keys())}")
        # BUGFIX: pasar texto_crudo para que los salvavidas regex funcionen.
        return _normalizar_groq(parsed, texto_crudo=texto_crudo), log

    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        log.append(f"✗ Groq HTTP {e.code}: {body[:200]}")
        return _vacio(), log
    except json.JSONDecodeError as e:
        log.append(f"✗ JSON inválido de Groq: {e}")
        return _vacio(), log
    except Exception as e:
        log.append(f"✗ Excepción: {str(e)[:200]}")
        return _vacio(), log


OUTPUT_FIELDS = [
    "empresa_cliente", "sucursal", "proveedor",
    "motivo_pago", "factura_no", "monto",
    "observaciones", "mes_presupuesto", "mes_pago", "anio_factura",
]


def _normalizar_groq(data: dict, texto_crudo: str = "") -> dict:
    # Campos internos de trabajo + campos de salida
    r = {k: "" for k in OUTPUT_FIELDS + ["no_cuenta", "banco", "clabe", "mes_factura"]}

    prov_raw = str(data.get("proveedor") or "").upper()
    for kw, nom in PROVEEDORES_MAP.items():
        if kw in prov_raw:
            r["proveedor"] = nom
            break
    if not r["proveedor"]:
        r["proveedor"] = str(data.get("proveedor") or "").strip()

    emp_raw = str(data.get("empresa_cliente") or "").upper()
    for emp in EMPRESAS_CONOCIDAS:
        if emp.upper()[:12] in emp_raw or emp_raw[:12] in emp.upper():
            r["empresa_cliente"] = emp
            break
    if not r["empresa_cliente"]:
        r["empresa_cliente"] = str(data.get("empresa_cliente") or "").strip()

    suc_raw = str(data.get("sucursal") or "").upper()
    if "NEBRASKA" in suc_raw:
        r["sucursal"] = "NEBRASKA"
    elif "ESCOBEDO" in suc_raw or "ANZURES" in suc_raw or "PISO 13" in suc_raw:
        r["sucursal"] = "CORPORATIVO POLANCO PISO 13"
    elif "PISO 16" in suc_raw:
        r["sucursal"] = "CORPORATIVO POLANCO PISO 16"
    elif "NAUCALPAN" in suc_raw:
        r["sucursal"] = "NAUCALPAN BH BE HEALTHY"
    elif "TEPOTZOTLAN" in suc_raw or "TEPOTZOTLÁN" in suc_raw:
        r["sucursal"] = "TEPOTZOTLAN III"
    elif "IZTAPALAPA" in suc_raw:
        r["sucursal"] = "IZTAPALAPA"
    elif "CISNE" in suc_raw:
        r["sucursal"] = "CISNES"
    elif "HORACIO" in suc_raw:
        r["sucursal"] = "HORACIO 1840"
    else:
        r["sucursal"] = str(data.get("sucursal") or "").strip()

    r["no_cuenta"] = re.sub(r"[\s,\-]", "", str(data.get("no_cuenta") or ""))
    if not r["no_cuenta"]:
        for _alias in ["telefono", "tel", "numero_cuenta", "numero", "cuenta"]:
            _v = str(data.get(_alias) or "").strip()
            if _v and _v.isdigit() and 7 <= len(_v) <= 12:
                r["no_cuenta"] = _v
                break
    # Fallback: extraer teléfono/cuenta del motivo_pago que devuelve el prompt genérico
    # Ej: "SERV CTA 5556855148 ABRIL 2026" → "5556855148"
    if not r["no_cuenta"]:
        _mp = str(data.get("motivo_pago") or "")
        _m = re.search(r"SERV CTA (\d{7,12})", _mp, re.IGNORECASE)
        if _m:
            r["no_cuenta"] = _m.group(1)
    if not r["no_cuenta"] and texto_crudo:
        _pu = str(data.get("proveedor") or "").upper()
        if "TELMEX" in _pu or "TELEFONOS" in _pu:
            _m = re.search(r"[Tt]el[eé]fono[:\s]+(\d[\d ]{8,11})", texto_crudo)
            if _m:
                r["no_cuenta"] = re.sub(r"\s+", "", _m.group(1))[:10]
            if not r["no_cuenta"]:
                _m = re.search(r"\b((?:55|33|81|77|22)\d{8})\b", texto_crudo)
                if _m:
                    r["no_cuenta"] = _m.group(1)
        elif "TOTALPLAY" in _pu or "TOTAL PLAY" in _pu:
            _m = re.search(r"\b(02\d{8})\b", texto_crudo)
            if _m:
                r["no_cuenta"] = _m.group(1)

    folio_raw = "".join(filter(str.isdigit, str(data.get("factura_no", "") or "")))
    if not folio_raw and texto_crudo:
        m_fol = re.search(r"(?i)factura\s*no\.?\s*[:\s]?(\d{10,16})", texto_crudo)
        if m_fol:
            folio_raw = m_fol.group(1)
    r["factura_no"] = folio_raw

    if not str(data.get("referencia_20_digitos", "") or "").strip() and texto_crudo:
        m_r20 = re.search(r"\b(55\d{18})\b", texto_crudo) or re.search(r"\b(\d{20})\b", texto_crudo)
        if m_r20:
            data["referencia_20_digitos"] = m_r20.group(1)

    monto_raw = re.sub(r"[^\d.]", "", str(data.get("monto") or "").replace(",", ""))
    try:
        r["monto"] = f"{float(monto_raw):.2f}" if monto_raw else ""
    except Exception:
        r["monto"] = ""

    banco_raw = str(data.get("banco") or "").upper().strip()
    banco_raw = banco_raw.replace("BANCOMER", "BBVA").replace("BANCO BBVA", "BBVA").strip()
    r["banco"] = BANCO_MAP.get(banco_raw, banco_raw.title() if banco_raw else "")

    clabe_raw = str(data.get("clabe") or "").strip()
    r["clabe"] = "" if not clabe_raw else re.sub(r"[\s\-]", "", clabe_raw)
    if not r["banco"] and len(r["clabe"]) >= 3:
        r["banco"] = PREFIJO_BANCO.get(r["clabe"][:3], "")

    dv_crudo = str(data.get("dv", "")).strip()
    # Fallback: extraer DV del campo observaciones que devuelve el prompt genérico
    # Ej: "BBVA DV 7 REFERENCIA 55568551480001349004" → "7"
    if not dv_crudo:
        _obs_dv = str(data.get("observaciones") or "")
        m_dv_obs = re.search(r"DV\s*(\d)", _obs_dv, re.IGNORECASE)
        if m_dv_obs:
            dv_crudo = m_dv_obs.group(1)
    if not dv_crudo and texto_crudo:
        m_dv = re.search(r"DV[\s\:\-]*(\d)", texto_crudo, re.IGNORECASE)
        if m_dv:
            dv_crudo = m_dv.group(1)

    # ── Escudo matemático Telmex ─────────────────────────
    prov_u = r["proveedor"].upper()
    if "TELMEX" in prov_u or "TELEFONOS" in prov_u:
        ref_cruda = str(data.get("referencia_20_digitos", ""))
        ref_solo_nums = "".join(filter(str.isdigit, ref_cruda))
        # Fallback: extraer referencia del campo observaciones del prompt genérico
        # Ej: "BBVA DV 7 REFERENCIA 55568551480001349004"
        if len(ref_solo_nums) < 20:
            _obs_ref = str(data.get("observaciones") or "")
            m_ref_obs = re.search(r"REFERENCIA[:\s]+(\d{15,22})", _obs_ref, re.IGNORECASE)
            if m_ref_obs:
                ref_solo_nums = m_ref_obs.group(1)
        if len(ref_solo_nums) < 20 and texto_crudo:
            m_ref = re.search(r"\b(55\d{18})\b", texto_crudo)
            if m_ref:
                ref_solo_nums = m_ref.group(1)
        ultimo_digito = ref_solo_nums[-1] if ref_solo_nums else "1"
        if r["no_cuenta"] and r["monto"]:
            centavos = str(int(float(r["monto"]) * 100)).zfill(9)
            ref_perfecta = f"{r['no_cuenta']}{centavos}{ultimo_digito}"
            r["observaciones"] = f"{r.get('banco') or 'BBVA'} DV {dv_crudo} REFERENCIA {ref_perfecta}"
        else:
            r["observaciones"] = f"{r.get('banco') or 'BBVA'} DV {dv_crudo} REFERENCIA {ref_solo_nums}"
    else:
        obs_raw = str(data.get("observaciones") or "").strip()
        if obs_raw:
            r["observaciones"] = obs_raw
        elif r.get("clabe"):
            prov_u2 = r["proveedor"].upper()
            if "TOTALPLAY" in prov_u2 or "TOTAL PLAY" in prov_u2:
                r["observaciones"] = f"BBVA CONV.1278800 REFERENCIA: {r['clabe']}"
            elif "RADIOMOVIL" in prov_u2 or "TELCEL" in prov_u2:
                r["observaciones"] = f"CONVENIO: 182251 REFENCIA: {r['clabe']}"

    mes_raw = str(data.get("mes_factura") or "").capitalize()
    r["mes_factura"] = mes_raw
    anio_raw = str(data.get("anio_factura") or "")
    r["anio_factura"] = anio_raw if re.match(r"20\d{2}", anio_raw) else str(date.today().year)
    r["mes_presupuesto"] = str(data.get("mes_presupuesto") or r["mes_factura"] or "").capitalize()
    r["mes_pago"] = str(data.get("mes_pago") or r["mes_factura"] or "").capitalize()

    _mes_mp = r["mes_factura"] or r["mes_presupuesto"]
    if r["no_cuenta"] and _mes_mp and r["anio_factura"]:
        r["motivo_pago"] = f"SERV CTA {r['no_cuenta']} {_mes_mp.upper()} {r['anio_factura']}".strip()
    elif r["no_cuenta"] and _mes_mp:
        r["motivo_pago"] = f"SERV CTA {r['no_cuenta']} {_mes_mp.upper()}".strip()
    elif r["no_cuenta"]:
        r["motivo_pago"] = f"SERV CTA {r['no_cuenta']}"
    elif not r["motivo_pago"]:
        _pt = r.get("proveedor", "").upper()
        if "TELMEX" in _pt or "TELEFONOS" in _pt:
            r["motivo_pago"] = f"SERV CTA TELMEX {_mes_mp.upper()} {r['anio_factura']}".strip()

    return {k: r[k] for k in OUTPUT_FIELDS}


def _extraer_campos_texto(texto: str) -> dict:
    """Extracción por regex del texto nativo del PDF. Salvavidas si Groq falla."""
    r = _vacio("Extracción por texto nativo")
    t = texto

    if re.search(r"TELEFONOS DE MEXICO|TELMEX", t, re.I):
        r["proveedor"] = "TELEFONOS DE MEXICO SAB DE CV"
    elif re.search(r"TOTAL\s*PLAY", t, re.I):
        r["proveedor"] = "TOTAL PLAY TELECOMUNICACIONES SAPI DE CV"
    elif re.search(r"RADIOMOVIL|TELCEL", t, re.I):
        r["proveedor"] = "RADIOMOVIL DIPSA SA DE CV"

    m = re.search(r"(?:Nombre o Razon Social|RAZON SOCIAL|CLIENTE)[^\n]{0,3}\n?\s*([A-Z][A-Z &.,]+)", t, re.I)
    if m:
        r["empresa_cliente"] = m.group(1).strip()

    m_folio = re.search(r"(?i)factura\s*no\.?\s*[:\s]?(\d{10,16})", t)
    if m_folio:
        r["factura_no"] = m_folio.group(1).strip()

    m_tel = re.search(r"[Tt]el[eé]fono[:\s]+(\d[\d ]{8,11})", t)
    if m_tel:
        r["no_cuenta"] = re.sub(r"\s+", "", m_tel.group(1))[:10]
    if not r["no_cuenta"]:
        m_tel2 = re.search(r"\b((55|33|81|77)\d{8})\b", t)
        if m_tel2:
            r["no_cuenta"] = m_tel2.group(1)
    if not r["no_cuenta"]:
        m_tp = re.search(r"(02\d{8})", t)
        if m_tp:
            r["no_cuenta"] = m_tp.group(1)

    m_monto = re.search(r"(?:Total a Pagar|Saldo al Corte|TOTAL A PAGAR)[:\s]*\$?\s*([\d,]+\.\d{2})", t, re.I)
    if m_monto:
        r["monto"] = m_monto.group(1).replace(",", "")

    for mes in ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]:
        if re.search(rf"Mes de Facturaci[oó]n[:\s]*{mes}", t, re.I):
            r["mes_factura"] = mes
            break

    m_yr = re.search(r"20(2[3-9]|[3-9]\d)", t)
    if m_yr:
        r["anio_factura"] = m_yr.group(0)

    m_ref20 = re.search(r"(55\d{18})", t) or re.search(r"(\d{20})", t)
    ref20 = m_ref20.group(1) if m_ref20 else ""
    m_dv = re.search(r"DV\s*(\d)", t)
    dv = m_dv.group(1) if m_dv else ""

    if r["no_cuenta"] and r["monto"]:
        try:
            centavos = str(int(float(r["monto"]) * 100)).zfill(9)
            ultimo = ref20[-1] if ref20 else "1"
            ref_perf = f"{r['no_cuenta']}{centavos}{ultimo}"
            r["observaciones"] = f"BBVA DV {dv} REFERENCIA {ref_perf}"
        except Exception:
            r["observaciones"] = f"BBVA DV {dv} REFERENCIA {ref20}"
    elif ref20:
        r["observaciones"] = f"BBVA DV {dv} REFERENCIA {ref20}"

    if r["no_cuenta"] and r["mes_factura"]:
        r["motivo_pago"] = f"SERV CTA {r['no_cuenta']} {r['mes_factura'].upper()} {r['anio_factura']}"
    elif r["no_cuenta"]:
        r["motivo_pago"] = f"SERV CTA {r['no_cuenta']}"
    elif r["proveedor"]:
        r["motivo_pago"] = "SERV CTA TELMEX"

    return {k: r.get(k, "") for k in OUTPUT_FIELDS}


def _vacio(razon: str = "", log: list | None = None) -> dict:
    r = {k: "" for k in OUTPUT_FIELDS}
    r["error"] = razon
    r["debug_log"] = "\n".join(log or []) + (f"\n{razon}" if razon else "")
    return r
