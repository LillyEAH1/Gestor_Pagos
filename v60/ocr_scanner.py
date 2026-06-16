"""
ocr_scanner.py v60
- Groq Vision como motor principal (llama-4-scout-17b-16e-instruct)
- Logging detallado: devuelve debug_log para mostrar al usuario qué pasó
- probar_groq_conexion(): test rápido de key + visión
- Windows.Media.Ocr como fallback
"""
from __future__ import annotations
import re, os, json, base64, subprocess
from pathlib import Path
from datetime import date

PROVEEDORES_MAP = {
    "TELMEX":               "TELEFONOS DE MEXICO SAB DE CV",
    "TELEFONOS DE MEXICO":  "TELEFONOS DE MEXICO SAB DE CV",
    "TOTALPLAY":            "TOTAL PLAY TELECOMUNICACIONES SAPI DE CV",
    "TOTAL PLAY":           "TOTAL PLAY TELECOMUNICACIONES SAPI DE CV",
    "IZZI":                 "IZZI NEGOCIOS",
    "DIGITAL COPY":         "DIGITAL COPY TECHNOLOGIES",
    "CFE":                  "CFE COMISION FEDERAL DE ELECTRICIDAD",
    "COMISION FEDERAL":     "CFE COMISION FEDERAL DE ELECTRICIDAD",
    "TELCEL":               "RADIOMOVIL DIPSA SA DE CV",
    "RADIOMOVIL":           "RADIOMOVIL DIPSA SA DE CV",
    "AT&T":                 "AT&T MEXICO",
    "BICENTEL":             "BICENTEL",
    "UNIFIED KNOWLEDGE":    "UNIFIED KNOWLEDGE AND ASSOCIATES",
    "UNIKA":                "UNIFIED KNOWLEDGE AND ASSOCIATES",
    "INNOVACION ORTOPEDICA":"INNOVACION ORTOPEDICA SA DE CV",
}

EMPRESAS_CONOCIDAS = [
    "MW MED SUPPLY MEDICAL","BLOOM & BLUSH","BH. BE HEALTHY COMERCIALIZADORA",
    "BH BE HEALTHY","BH SOLAR","ENFERMERAS UNIDAS PLUS",
    "GOLDEN YEARS MANAGEMENT","MB COMERCIALIZADORA EN LINEA",
    "COMERCIALIZADORA DE MARCAS JSB","COMERCIALIZADORA ONLINE NH",
    "SELECT SHOP MB","SM DISTRIBUIDORA DIGITAL","MOSAIC CARE & HEALTH",
    "INMOBILIARIA EISHEL","ALEGARAT","ZONA ZELU","DONKERTECH",
]

BANCO_MAP = {
    "BANCOMER":"BBVA","BBVA":"BBVA",
    "BANAMEX":"BANAMEX","CITIBANAMEX":"BANAMEX",
    "BANORTE":"BANORTE","HSBC":"HSBC",
    "SANTANDER":"SANTANDER","SCOTIABANK":"SCOTIABANK",
    "BANCO AZTECA":"AZTECA","AZTECA":"AZTECA",
    "INBURSA":"INBURSA","BANREGIO":"BANREGIO",
    "BAJIO":"BAJIO","STP":"STP","BASE":"BASE",
}

PREFIJO_BANCO = {
    "012":"BBVA","021":"HSBC","002":"BANAMEX","014":"SANTANDER",
    "044":"SCOTIABANK","072":"BANORTE","058":"BANREGIO",
    "127":"AZTECA","036":"INBURSA","030":"BAJIO","646":"STP",
}

GROQ_PROMPT_RECIBO = """Eres un asistente experto en leer RECIBOS de servicios mexicanos (Telmex, Totalplay, Telcel, Izzi, Bicentel, Digital Copy, etc.).
REGLAS ABSOLUTAS — sin excepción:
1. SOLO analiza la PRIMERA PÁGINA. Ignora publicidad y páginas adicionales.
2. EMPRESA_CLIENTE: Lee ESTRICTAMENTE del encabezado del documento, sección "Nombre o Razón Social" o "Cliente". NO inventes ni mezcles nombres de otras empresas. Si dice "ENFERMERAS UNIDAS PLUS" pon exactamente eso. Si dice "MW MED SUPPLY" pon exactamente eso.
3. SUCURSAL: Es la dirección del cliente en el recibo (ej: "Iztapalapa", "Nebraska 170", "Mariano Escobedo 476"). NO es la dirección del proveedor.
4. FACTURA_NO: Extrae ÚNICAMENTE el número junto al texto "Factura No." (ej: 130126040074041). ESTRICTAMENTE PROHIBIDO usar el teléfono, número de cuenta o UUID/Folio Fiscal. Si no hay Factura No. visible, deja en blanco "".
5. CLABE: Deja COMPLETAMENTE VACÍO "". No extraigas nada.
6. OBSERVACIONES: Lee el bloque del código de barras al FINAL de la primera hoja. Extrae banco, DV y el número del código de barras. Formato: "BBVA DV 7 REFERENCIA 5556851480001349004". Si dice BANCOMER escribe BBVA.
7. MES_PRESUPUESTO: Mes de facturación del recibo (ej: Abril).
8. MES_PAGO: Mes siguiente al de facturación, o el mes actual si ya pasó (ej: Mayo).
9. MOTIVO_PAGO: Construye "SERV CTA [teléfono/cuenta] [MES_PRESUPUESTO] [AÑO]". Usa el teléfono de la carátula, NO el código de barras.
10. Compatibilidad: Funciona para Telmex, Totalplay, Telcel, Izzi, Bicentel y Digital Copy.

FORMATO JSON — Devuelve SOLO este JSON válido, sin markdown ni texto extra:
{
  "empresa_cliente": "Empresa que paga (del encabezado del recibo, exacto)",
  "sucursal": "Dirección o zona del cliente en el recibo",
  "proveedor": "Empresa que presta el servicio",
  "motivo_pago": "SERV CTA [telefono_10_digitos] [MES] [AÑO]",
  "factura_no": "Solo el número de Factura No. corto. Si no hay, dejar vacío.",
  "monto": "Total a pagar en decimal",
  "banco": "Banco para depósito (BBVA, BANORTE, etc.)",
  "clabe": "",
  "observaciones": "BBVA DV [n] REFERENCIA [codigo_barras_largo]",
  "mes_presupuesto": "Mes de facturación",
  "mes_pago": "Mes de pago",
  "anio_factura": "Año"
}"""

GROQ_PROMPT_TELMEX = """Eres un asistente de extracción de datos. Analiza este recibo de Telmex y devuelve ÚNICAMENTE un JSON válido, sin texto adicional ni markdown.

Usa este ejemplo como guía EXACTA de mapeo campo por campo:

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

Notas de mapeo:
- empresa_cliente: Nombre o Razón Social del CLIENTE (nunca Telmex ni Teléfonos de México)
- sucursal: Zona o ciudad de la dirección del cliente
- no_cuenta: Número de teléfono de 10 dígitos del campo "Teléfono:"
- factura_no: Solo los números del campo "Factura No."
- monto: Número del "Total a Pagar"
- banco: Siempre BBVA
- dv: Solo el dígito que aparece junto al código de barras (ej: "DV 7" → "7")
- mes_factura: Mes de facturación del recibo
- anio_factura: Año del recibo
- referencia_20_digitos: El número largo bajo el código de barras (20 dígitos exactos)
"""

GROQ_PROMPT_FACTURA = """Eres un asistente experto en leer FACTURAS (CFDIs) mexicanas de cualquier departamento.
REGLAS OBLIGATORIAS:
1. SOLO analiza la PRIMERA PÁGINA.
2. Extrae los 12 campos del JSON. Si un campo no existe pon "".
3. EMPRESA CLIENTE: La empresa que RECIBE y PAGA. Busca en "Razón Social del receptor" o "CLIENTE".
4. FACTURA_NO: El número de factura corto (ej: FA-000000000564109722). PROHIBIDO el UUID/Folio Fiscal.
5. CLABE: Extrae la CLABE interbancaria si aparece en opciones de pago. Si no hay, deja vacío.
6. BANCO: Busca en la sección de opciones de pago.
7. MES: Extrae el mes de la fecha de emisión.

FORMATO JSON — Devuelve SOLO este JSON válido, sin markdown:
{
  "empresa_cliente": "Empresa que paga",
  "sucursal": "Dirección del cliente",
  "proveedor": "Empresa que emite la factura",
  "motivo_pago": "Descripción del concepto de la factura",
  "factura_no": "Número de factura corto. NO UUID.",
  "monto": "Total a pagar en decimal",
  "banco": "Banco para depósito",
  "clabe": "CLABE de 18 dígitos si existe, si no vacío",
  "observaciones": "Datos de pago relevantes",
  "mes_presupuesto": "Mes de la factura",
  "mes_pago": "Mes de pago",
  "anio_factura": "Año"
}"""

# Mantener GROQ_SYSTEM_PROMPT como alias del de recibo para compatibilidad
GROQ_SYSTEM_PROMPT = GROQ_PROMPT_RECIBO

PS_PDF_A_PNG = r"""
param([string]$PdfPath,[string]$PngPath)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
function Await1($task,$type){
    $m=[System.WindowsRuntimeSystemExtensions].GetMethods()|Where-Object{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'}|Select-Object -First 1
    $t=$m.MakeGenericMethod($type).Invoke($null,@($task));$t.Wait();return $t.Result
}
function AwaitAction($task){
    $m=[System.WindowsRuntimeSystemExtensions].GetMethods()|Where-Object{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction'}|Select-Object -First 1
    $t=$m.Invoke($null,@($task));$t.Wait()
}
$null=[Windows.Data.Pdf.PdfDocument,Windows.Data.Pdf,ContentType=WindowsRuntime]
$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Storage.StorageFolder,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Storage.Streams.InMemoryRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
$null=[Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$null=[Windows.Graphics.Imaging.BitmapEncoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$pdfFile=Await1 ([Windows.Storage.StorageFile]::GetFileFromPathAsync($PdfPath)) ([Windows.Storage.StorageFile])
$pdfDoc=Await1 ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($pdfFile)) ([Windows.Data.Pdf.PdfDocument])
$page=$pdfDoc.GetPage(0)
$rs=[Windows.Storage.Streams.InMemoryRandomAccessStream]::new()
$opts=[Windows.Data.Pdf.PdfPageRenderOptions]::new();$opts.DestinationWidth=1800
AwaitAction ($page.RenderToStreamAsync($rs,$opts))
$rs.Seek(0)
$dec=Await1 ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($rs)) ([Windows.Graphics.Imaging.BitmapDecoder])
$sb=Await1 ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$dir=[System.IO.Path]::GetDirectoryName($PngPath)
$name=[System.IO.Path]::GetFileName($PngPath)
$fol=Await1 ([Windows.Storage.StorageFolder]::GetFolderFromPathAsync($dir)) ([Windows.Storage.StorageFolder])
$fil=Await1 ($fol.CreateFileAsync($name,[Windows.Storage.CreationCollisionOption]::ReplaceExisting)) ([Windows.Storage.StorageFile])
$out=Await1 ($fil.OpenAsync([Windows.Storage.FileAccessMode]::ReadWrite)) ([Windows.Storage.Streams.IRandomAccessStream])
$enc=Await1 ([Windows.Graphics.Imaging.BitmapEncoder]::CreateAsync([Windows.Graphics.Imaging.BitmapEncoder]::PngEncoderId,$out)) ([Windows.Graphics.Imaging.BitmapEncoder])
$enc.SetSoftwareBitmap($sb)
AwaitAction ($enc.FlushAsync())
$out.Dispose()
Write-Host "PNG_OK"
"""

PS_OCR_WIN = r"""
param([string]$ImgPath,[string]$OutFile)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
function Await1($task,$type){
    $m=[System.WindowsRuntimeSystemExtensions].GetMethods()|Where-Object{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'}|Select-Object -First 1
    $t=$m.MakeGenericMethod($type).Invoke($null,@($task));$t.Wait();return $t.Result
}
$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Media.Ocr.OcrEngine,Windows.Media.Ocr,ContentType=WindowsRuntime]
$null=[Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$imgFile=Await1 ([Windows.Storage.StorageFile]::GetFileFromPathAsync($ImgPath)) ([Windows.Storage.StorageFile])
$stream=Await1 ($imgFile.OpenReadAsync()) ([Windows.Storage.Streams.IRandomAccessStreamWithContentType])
$dec=Await1 ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$sb=Await1 ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$lang=$null
foreach($tag in @('es-MX','es','en-US','en')){
    try{$l=[Windows.Globalization.Language]::new($tag);if([Windows.Media.Ocr.OcrEngine]::IsLanguageSupported($l)){$lang=$l;break}}catch{}
}
if($null -eq $lang){$avail=[Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages;if($avail.Count -gt 0){$lang=$avail[0]}}
$engine=[Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
$result=Await1 ($engine.RecognizeAsync($sb)) ([Windows.Media.Ocr.OcrResult])
$lines=@();foreach($line in $result.Lines){$lines+=$line.Text}
[System.IO.File]::WriteAllText($OutFile,($lines -join "`n"),[System.Text.Encoding]::UTF8)
Write-Host "OCR_OK"
"""


def escanear_recibo(ruta: str, groq_api_key: str = "", tipo_doc: str = "recibo") -> dict:
    log = []
    if not groq_api_key:
        groq_api_key = _cargar_groq_key()
        if groq_api_key:
            log.append(f"Key cargada de config: {groq_api_key[:8]}...")
        else:
            log.append("Sin Groq API Key en config")

    ruta_abs = str(Path(ruta).resolve())
    ext = Path(ruta).suffix.lower()
    safe_dir = os.path.join(os.environ.get("TEMP","C:\\Temp"), "GestorOCR")
    os.makedirs(safe_dir, exist_ok=True)
    png_path = os.path.join(safe_dir, "recibo.png")

    if ext == ".pdf":
        texto_nativo = _pdf_texto_nativo(ruta_abs)
        log.append(f"Texto nativo extraido: {len(texto_nativo.strip())} chars")
        
        # Siempre convertir a PNG para Groq
        log.append("Convirtiendo PDF a imagen...")
        ok = _pdf_a_png(ruta_abs, png_path, safe_dir)
        if ok:
            log.append(f"PDF->PNG OK: {png_path}")
        else:
            log.append("PDF->PNG FALLO — usando texto nativo")
            if len(texto_nativo.strip()) > 50:
                r = _extraer_campos_texto(texto_nativo)
                r["debug_log"] = "\n".join(log) + "\nFallback: extraccion por texto"
                return r
            return _vacio("No se pudo convertir PDF a imagen", log)
    else:
        png_path = ruta_abs
        log.append(f"Imagen directa: {ext}")

    # Intentar Groq Vision
    if groq_api_key and os.path.exists(png_path):
        log.append(f"Llamando a Groq Vision con modelo llama-4-scout...")
        texto_para_regex = texto_nativo if ext == ".pdf" else ""
        resultado, groq_log = _groq_vision(png_path, groq_api_key, tipo_doc,
                                            texto_crudo=texto_para_regex)
        log.extend(groq_log)
        if resultado.get("proveedor") or resultado.get("monto"):
            log.append("✓ Groq extrajo campos exitosamente")
            resultado["debug_log"] = "\n".join(log)
            return resultado
        else:
            log.append("Groq no extrajo campos — usando Windows OCR")
    elif not groq_api_key:
        log.append("Sin key — usando Windows OCR")
    else:
        log.append("Imagen no encontrada para Groq")

    # Fallback Windows OCR
    if os.path.exists(png_path):
        log.append("Ejecutando Windows.Media.Ocr...")
        txt_path = os.path.join(safe_dir, "ocr.txt")
        texto = _windows_ocr(png_path, txt_path, safe_dir)
        if texto and len(texto.strip()) > 20:
            log.append(f"Windows OCR extrajo {len(texto)} chars")
            r = _extraer_campos_texto(texto)
            r["debug_log"] = "\n".join(log)
            return r
        else:
            log.append("Windows OCR no extrajo texto")

    return _vacio("No se pudo leer el recibo", log)


def probar_groq_conexion(api_key: str) -> tuple[bool, str]:
    """
    Prueba la conexión a Groq con texto (rápido, sin imagen).
    Retorna (exito, mensaje).
    """
    import urllib.request, urllib.error
    try:
        payload = json.dumps({
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role":"user","content":"Responde solo: OK"}],
            "max_tokens": 5
        }).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
            }
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        resp = data["choices"][0]["message"]["content"].strip()
        return True, f"✓ Groq conectado correctamente. Respuesta: {resp}"
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        if e.code == 401:
            return False, "✗ API Key inválida o expirada (error 401)"
        elif e.code == 403:
            return False, f"✗ Acceso denegado (error 403): {body[:100]}"
        elif e.code == 429:
            return False, "✗ Límite de requests alcanzado (error 429) — espera un momento"
        else:
            return False, f"✗ Error HTTP {e.code}: {body[:150]}"
    except Exception as e:
        return False, f"✗ Error de conexión: {str(e)[:150]}"


def _cargar_groq_key() -> str:
    try:
        cfg_file = Path(os.environ.get("LOCALAPPDATA","")) / "GestorPagosIT" / "config.json"
        if cfg_file.exists():
            return json.loads(cfg_file.read_text()).get("groq_api_key","")
    except Exception:
        pass
    return ""


def _pdf_texto_nativo(ruta: str) -> str:
    try:
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(ruta).pages[:2])
    except Exception:
        return ""


def _pdf_a_png(pdf_path: str, png_path: str, safe_dir: str) -> bool:
    ps1 = os.path.join(safe_dir, "pdf2png.ps1")
    with open(ps1, "w", encoding="utf-8") as f:
        f.write(PS_PDF_A_PNG)
    try:
        r = subprocess.run(
            ["powershell","-NoProfile","-ExecutionPolicy","Bypass",
             "-File",ps1,"-PdfPath",pdf_path,"-PngPath",png_path],
            capture_output=True, text=True, timeout=60)
        return "PNG_OK" in r.stdout and os.path.exists(png_path)
    except Exception:
        return False


def _windows_ocr(img_path: str, txt_path: str, safe_dir: str) -> str:
    try:
        if os.path.exists(txt_path): os.remove(txt_path)
    except Exception: pass
    ps1 = os.path.join(safe_dir, "ocr_win.ps1")
    with open(ps1, "w", encoding="utf-8") as f:
        f.write(PS_OCR_WIN)
    try:
        subprocess.run(
            ["powershell","-NoProfile","-ExecutionPolicy","Bypass",
             "-File",ps1,"-ImgPath",img_path,"-OutFile",txt_path],
            capture_output=True, text=True, timeout=60)
        if os.path.exists(txt_path):
            return open(txt_path, encoding="utf-8", errors="ignore").read()
    except Exception:
        pass
    return ""


def _groq_vision(img_path: str, api_key: str, tipo_doc: str = "recibo", texto_crudo: str = "") -> tuple[dict, list]:
    """Retorna (resultado, log_list)"""
    import urllib.request, urllib.error
    log = []
    try:
        file_size = os.path.getsize(img_path)
        log.append(f"Imagen: {img_path} ({file_size//1024} KB)")
        
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        log.append(f"Base64: {len(img_b64)//1024} KB")

        ext = Path(img_path).suffix.lower()
        mime = "image/png" if ext == ".png" else "image/jpeg"

        payload = json.dumps({
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {"role":"system","content": (
                    GROQ_PROMPT_TELMEX if tipo_doc == "telmex"
                    else GROQ_PROMPT_FACTURA if tipo_doc == "factura"
                    else GROQ_PROMPT_RECIBO
                )},
                {"role":"user","content":[
                    {"type":"image_url",
                     "image_url":{"url":f"data:{mime};base64,{img_b64}"}},
                    {"type":"text",
                     "text":"Extrae los campos de este recibo en JSON. "
                            "Identifica el nombre de la empresa cliente (no el proveedor), "
                            "el numero de telefono/cuenta, el banco y la referencia de pago."}
                ]}
            ],
            "max_tokens": 700,
            "temperature": 0
        }).encode("utf-8")
        log.append(f"Payload: {len(payload)//1024} KB — enviando a Groq...")

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
            }
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read()
            data = json.loads(raw)
        
        content = data["choices"][0]["message"]["content"].strip()
        log.append(f"Groq respondio ({len(content)} chars): {content[:80]}...")
        
        # Limpiar markdown si viene con ```json
        content = re.sub(r"^```(?:json)?\s*|\s*```$","", content, flags=re.MULTILINE).strip()
        parsed = json.loads(content)
        log.append(f"JSON parseado: {list(parsed.keys())}")
        return _normalizar_groq(parsed), log

    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        log.append(f"✗ Groq HTTP {e.code}: {body[:200]}")
        return _vacio(), log
    except json.JSONDecodeError as e:
        log.append(f"✗ JSON invalido de Groq: {e}")
        return _vacio(), log
    except Exception as e:
        import traceback
        log.append(f"✗ Excepcion: {traceback.format_exc()[:300]}")
        return _vacio(), log


def _normalizar_groq(data: dict, texto_crudo: str = "") -> dict:
    r = {k:"" for k in ["proveedor","empresa_cliente","sucursal","no_cuenta",
                         "factura_no","monto","banco","clabe","observaciones",
                         "motivo_pago","mes_factura","anio_factura",
                         "mes_presupuesto","mes_pago","fecha_limite"]}

    prov_raw = str(data.get("proveedor") or "").upper()
    for kw, nom in PROVEEDORES_MAP.items():
        if kw in prov_raw: r["proveedor"] = nom; break
    if not r["proveedor"]: r["proveedor"] = str(data.get("proveedor") or "").strip()

    emp_raw = str(data.get("empresa_cliente") or "").upper()
    for emp in EMPRESAS_CONOCIDAS:
        if emp.upper()[:12] in emp_raw or emp_raw[:12] in emp.upper():
            r["empresa_cliente"] = emp; break
    if not r["empresa_cliente"]: r["empresa_cliente"] = str(data.get("empresa_cliente") or "").strip()

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
        # Dejar el valor crudo — la app lo buscará en el combo
        r["sucursal"] = str(data.get("sucursal") or "").strip()

    r["no_cuenta"] = re.sub(r"[\s,\-]","", str(data.get("no_cuenta") or ""))
    # Salvavidas: Groq a veces usa aliases distintos
    if not r["no_cuenta"]:
        for _alias in ["telefono","tel","numero_cuenta","numero","cuenta"]:
            _v = str(data.get(_alias) or "").strip()
            if _v and _v.isdigit() and 7 <= len(_v) <= 12:
                r["no_cuenta"] = _v; break
    # Salvavidas regex en texto crudo
    if not r["no_cuenta"] and texto_crudo:
        _pu = str(data.get("proveedor") or "").upper()
        if "TELMEX" in _pu or "TELEFONOS" in _pu:
            _m = re.search(r"\b((?:55|33|81|77)\d{8})\b", texto_crudo)
            if _m: r["no_cuenta"] = _m.group(1)
        elif "TOTALPLAY" in _pu or "TOTAL PLAY" in _pu:
            _m = re.search(r"\b(02\d{8})\b", texto_crudo)
            if _m: r["no_cuenta"] = _m.group(1)
    # Salvavidas regex en texto_crudo si Groq dejó no_cuenta vacío
    if not r["no_cuenta"] and texto_crudo:
        prov_raw_u = str(data.get("proveedor") or "").upper()
        if "TELMEX" in prov_raw_u or "TELEFONOS" in prov_raw_u:
            m_tel = re.search(r"\b((55|33|81|77)\d{8})\b", texto_crudo)
            if m_tel:
                r["no_cuenta"] = m_tel.group(1)
        elif "TOTALPLAY" in prov_raw_u or "TOTAL PLAY" in prov_raw_u:
            m_tp = re.search(r"\b(02\d{8})\b", texto_crudo)
            if m_tp:
                r["no_cuenta"] = m_tp.group(1)

    # Salvavidas folio: regex fuerte si Groq trajo basura
    folio_raw = "".join(filter(str.isdigit, str(data.get("factura_no","") or "")))
    if not folio_raw and texto_crudo:
        m_fol = re.search(r"(?i)factura\s*no\.?\s*[:\s]?(\d{10,16})", texto_crudo)
        if m_fol:
            folio_raw = m_fol.group(1)
    r["factura_no"] = folio_raw

    # Salvavidas referencia 20 dígitos en texto_crudo
    if not str(data.get("referencia_20_digitos","") or "").strip() and texto_crudo:
        m_r20 = re.search(r"\b(55\d{18})\b", texto_crudo)
        if not m_r20:
            m_r20 = re.search(r"\b(\d{20})\b", texto_crudo)
        if m_r20:
            data["referencia_20_digitos"] = m_r20.group(1)
    # factura_no ya procesada arriba con salvavidas

    monto_raw = re.sub(r"[^\d.]","", str(data.get("monto") or "").replace(",",""))
    try: r["monto"] = f"{float(monto_raw):.2f}" if monto_raw else ""
    except Exception: r["monto"] = ""

    banco_raw = str(data.get("banco") or "").upper().strip()
    # Normalizar variantes comunes
    banco_raw = banco_raw.replace("BANCOMER","BBVA").replace("BANCO BBVA","BBVA")
    banco_raw = banco_raw.replace("BANORTE","BANORTE").strip()
    r["banco"] = BANCO_MAP.get(banco_raw, banco_raw.title() if banco_raw else "")

    clabe_raw = str(data.get("clabe") or "").strip()
    # Si el prompt es de recibo, clabe DEBE quedar vacío (se autollena desde BD)
    r["clabe"] = "" if not clabe_raw else re.sub(r"[\s\-]","", clabe_raw)
    if not r["banco"] and len(r["clabe"]) >= 3:
        r["banco"] = PREFIJO_BANCO.get(r["clabe"][:3],"")

    # 1. SALVAVIDAS REGEX (Forzar campos críticos si Groq falló)
    if not r.get("no_cuenta") and texto_crudo:
        m_cta = re.search(r"\b(55\d{8})\b", texto_crudo)
        if m_cta:
            r["no_cuenta"] = m_cta.group(1)

    dv_crudo = str(data.get("dv", "")).strip()
    if not dv_crudo and texto_crudo:
        m_dv = re.search(r"DV[\s\:\-]*(\d)", texto_crudo, re.IGNORECASE)
        if m_dv:
            dv_crudo = m_dv.group(1)

    if not r.get("factura_no") and texto_crudo:
        m_fol = re.search(r"(?i)factura\s*no\.?\s*[:\s]?(\d{10,16})", texto_crudo)
        if m_fol:
            r["factura_no"] = m_fol.group(1)

    # 2. ESCUDO MATEMÁTICO TELMEX
    prov_u = r["proveedor"].upper()
    if "TELMEX" in prov_u or "TELEFONOS" in prov_u:
        ref_cruda = str(data.get("referencia_20_digitos", ""))
        ref_solo_nums = "".join(filter(str.isdigit, ref_cruda))

        # Si la IA no leyó los 20 dígitos, forzar búsqueda en texto crudo
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

        r["motivo_pago"] = f"SERV CTA {r['no_cuenta']} {r.get('mes_factura', '').upper()} {r.get('anio_factura', '')}".strip()
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
    r["anio_factura"] = anio_raw if re.match(r"20\d{2}",anio_raw) else str(date.today().year)

    # Mes presupuesto y mes pago (si Groq no los devuelve, usar mes_factura)
    r["mes_presupuesto"] = str(data.get("mes_presupuesto") or r["mes_factura"] or "").capitalize()
    r["mes_pago"]        = str(data.get("mes_pago")        or r["mes_factura"] or "").capitalize()

    # Rearmar motivo con no_cuenta ya forzado por regex
    if r["no_cuenta"] and r["mes_factura"] and r["anio_factura"]:
        r["motivo_pago"] = f"SERV CTA {r['no_cuenta']} {r['mes_factura'].upper()} {r['anio_factura']}".strip()
    elif r["no_cuenta"] and r["mes_factura"]:
        r["motivo_pago"] = f"SERV CTA {r['no_cuenta']} {r['mes_factura'].upper()}".strip()
    elif r["no_cuenta"]:
        r["motivo_pago"] = f"SERV CTA {r['no_cuenta']}"
    elif not r["motivo_pago"]:
        _pt = r.get("proveedor","").upper()
        _cta = r.get("no_cuenta","")
        if _cta:
            r["motivo_pago"] = f"SERV CTA {_cta}"
        elif "TELMEX" in _pt or "TELEFONOS" in _pt:
            r["motivo_pago"] = f"SERV CTA TELMEX {r['mes_factura'].upper()} {r['anio_factura']}".strip()
    return r


def _extraer_campos_texto(texto: str) -> dict:
    """Extracción por regex del texto nativo del PDF. Salvavidas si Groq falla."""
    import re
    r = _vacio("Extracción por texto nativo")
    t = texto

    # Proveedor
    if re.search(r"TELEFONOS DE MEXICO|TELMEX", t, re.I):
        r["proveedor"] = "TELEFONOS DE MEXICO SAB DE CV"
    elif re.search(r"TOTAL\s*PLAY", t, re.I):
        r["proveedor"] = "TOTAL PLAY TELECOMUNICACIONES SAPI DE CV"
    elif re.search(r"RADIOMOVIL|TELCEL", t, re.I):
        r["proveedor"] = "RADIOMOVIL DIPSA SA DE CV"

    # Empresa cliente (Nombre o Razón Social del cliente)
    m = re.search(r"(?:Nombre o Razon Social|RAZON SOCIAL|CLIENTE)[^\n]{0,3}\n?\s*([A-Z][A-Z &.,]+)", t, re.I)
    if m:
        r["empresa_cliente"] = m.group(1).strip()

    # Folio — SOLO de "Factura No." — patrón fuerte
    m_folio = re.search(r'(?i)factura\s*no\.?\s*[:\s]?(\d{10,16})', t)
    if m_folio:
        r["factura_no"] = m_folio.group(1).strip()

    # Teléfono / No. cuenta Telmex
    m_tel = re.search(r'((55|33|81|77)\d{8})', t)
    if m_tel:
        r["no_cuenta"] = m_tel.group(1)

    # Cuenta Totalplay
    if not r["no_cuenta"]:
        m_tp = re.search(r'(02\d{8})', t)
        if m_tp:
            r["no_cuenta"] = m_tp.group(1)

    # Monto
    m_monto = re.search(r'(?:Total a Pagar|Saldo al Corte|TOTAL A PAGAR)[:\s]*\$?\s*([\d,]+\.\d{2})', t, re.I)
    if m_monto:
        r["monto"] = m_monto.group(1).replace(",", "")

    # Mes de facturación
    for mes in ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]:
        if re.search(rf"Mes de Facturaci[oó]n[:\s]*{mes}", t, re.I):
            r["mes_factura"] = mes
            break

    # Año
    m_yr = re.search(r'20(2[3-9]|[3-9]\d)', t)
    if m_yr:
        r["anio_factura"] = m_yr.group(0)

    # Referencia 20 dígitos (código de barras Telmex)
    m_ref20 = re.search(r'(55\d{18})', t)
    if not m_ref20:
        m_ref20 = re.search(r'(\d{20})', t)
    ref20 = m_ref20.group(1) if m_ref20 else ""

    # DV
    m_dv = re.search(r'DV\s*(\d)', t)
    dv = m_dv.group(1) if m_dv else ""

    # Reconstruir observaciones
    if r["no_cuenta"] and r["monto"]:
        try:
            centavos = str(int(float(r["monto"]) * 100)).zfill(9)
            ultimo   = ref20[-1] if ref20 else "1"
            ref_perf = f"{r['no_cuenta']}{centavos}{ultimo}"
            r["observaciones"] = f"BBVA DV {dv} REFERENCIA {ref_perf}"
        except Exception:
            r["observaciones"] = f"BBVA DV {dv} REFERENCIA {ref20}"
    elif ref20:
        r["observaciones"] = f"BBVA DV {dv} REFERENCIA {ref20}"

    # Motivo de pago — nunca vacío
    if r["no_cuenta"] and r["mes_factura"]:
        r["motivo_pago"] = f"SERV CTA {r['no_cuenta']} {r['mes_factura'].upper()} {r['anio_factura']}"
    elif r["no_cuenta"]:
        r["motivo_pago"] = f"SERV CTA {r['no_cuenta']}"
    elif r["proveedor"]:
        r["motivo_pago"] = f"SERV CTA TELMEX"

    r["banco"] = "BBVA"
    r["clabe"] = ""
    return r


def _vacio(razon="", log=None) -> dict:
    r = {k:"" for k in ["proveedor","empresa_cliente","sucursal","no_cuenta",
                         "factura_no","monto","banco","clabe","observaciones",
                         "motivo_pago","mes_factura","anio_factura",
                         "mes_presupuesto","mes_pago","fecha_limite"]}
    r["error"] = razon
    r["debug_log"] = "\n".join(log or []) + (f"\n{razon}" if razon else "")
    return r


def diagnostico_ocr() -> str:
    key = _cargar_groq_key()
    groq_s = f"✓ Groq key: {key[:8]}..." if key else "✗ Sin Groq API Key"
    try:
        ps=("$null=[Windows.Media.Ocr.OcrEngine,Windows.Media.Ocr,ContentType=WindowsRuntime];"
            "$l=[Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages;"
            "Write-Host ('LANGS:'+$l.Count)")
        res=subprocess.run(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-Command",ps],
                           capture_output=True,text=True,timeout=10)
        n=res.stdout.strip().split("LANGS:")[-1].strip() if "LANGS:" in res.stdout else "?"
        win_s=f"✓ Windows.Ocr ({n} idiomas)"
    except Exception as e:
        win_s=f"✗ Error: {e}"
    return f"{groq_s} | {win_s}"
