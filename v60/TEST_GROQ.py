"""
TEST_GROQ.py - Corre este script desde la carpeta de la app para diagnosticar Groq.
Uso: python TEST_GROQ.py
"""
import sys, os, json, urllib.request, urllib.error, base64, traceback
from pathlib import Path

print("=" * 60)
print(" TEST DE GROQ OCR - GestorPagosIT v30")
print("=" * 60)

# PASO 1: Leer la API Key del config
print("\n[1] Buscando API Key en config...")
cfg_file = Path(os.environ.get("LOCALAPPDATA","")) / "GestorPagosIT" / "config.json"
print(f"    Ruta config: {cfg_file}")
print(f"    Existe: {cfg_file.exists()}")

if not cfg_file.exists():
    # Intentar cargar desde config.py directamente
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        import config
        cfg = config.cargar()
        key = cfg.get("groq_api_key", "")
        if key:
            print(f"    Key encontrada en config.py DEFAULTS: {key[:12]}...{key[-4:]}")
        else:
            print("    ✗ No hay config.json y DEFAULTS no tiene key")
            sys.exit(1)
    except Exception as e:
        print(f"    ✗ Error cargando config: {e}")
        sys.exit(1)
else:
    cfg = json.loads(cfg_file.read_text())
    key = cfg.get("groq_api_key","")
    if key:
        print(f"    ✓ Key encontrada: {key[:12]}...{key[-4:]}")
    else:
        print("    ✗ El config.json existe pero groq_api_key está vacío")
        print("      Abre la app -> Configuración -> ingresa la key y guarda")
        sys.exit(1)

# PASO 2: Test de conexión básica (texto)
print("\n[2] Probando conexión a Groq (sin imagen)...")
try:
    payload = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role":"user","content":"Responde solo: OK"}],
        "max_tokens": 5
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    resp = data["choices"][0]["message"]["content"].strip()
    print(f"    ✓ Groq responde: '{resp}'")
except urllib.error.HTTPError as e:
    body = e.read().decode(errors="ignore")
    print(f"    ✗ HTTP Error {e.code}: {body[:200]}")
    sys.exit(1)
except Exception as e:
    print(f"    ✗ Error de red: {e}")
    print("    Verifica tu conexión a internet")
    sys.exit(1)

# PASO 3: Test de visión con imagen mínima
print("\n[3] Probando Groq Vision (imagen de prueba)...")
try:
    import struct, zlib
    def tiny_png():
        def chunk(n, d):
            c = struct.pack('>I',len(d))+n+d
            return c+struct.pack('>I',zlib.crc32(n+d)&0xffffffff)
        return (b'\x89PNG\r\n\x1a\n'
                + chunk(b'IHDR', struct.pack('>IIBBBBB',10,10,8,2,0,0,0))
                + chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff'*10*10))
                + chunk(b'IEND', b''))
    
    img_b64 = base64.b64encode(tiny_png()).decode()
    payload = json.dumps({
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [{
            "role":"user",
            "content":[
                {"type":"image_url","image_url":{"url":f"data:image/png;base64,{img_b64}"}},
                {"type":"text","text":"Que color ves? Una palabra."}
            ]
        }],
        "max_tokens": 10
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    resp = data["choices"][0]["message"]["content"].strip()
    print(f"    ✓ Vision funciona: '{resp}'")
    print(f"    Modelo: meta-llama/llama-4-scout-17b-16e-instruct")
except urllib.error.HTTPError as e:
    body = e.read().decode(errors="ignore")
    print(f"    ✗ HTTP {e.code} en visión: {body[:300]}")
    if e.code == 400:
        print("    Posible causa: modelo no disponible o imagen inválida")
except Exception as e:
    print(f"    ✗ Error en visión: {traceback.format_exc()}")

# PASO 4: Verificar Windows.Data.Pdf
print("\n[4] Verificando Windows.Data.Pdf (PDF->imagen)...")
import subprocess
ps = "$null=[Windows.Data.Pdf.PdfDocument,Windows.Data.Pdf,ContentType=WindowsRuntime]; Write-Host 'PDF_OK'"
r = subprocess.run(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-Command",ps],
                   capture_output=True, text=True, timeout=10)
if "PDF_OK" in r.stdout:
    print("    ✓ Windows.Data.Pdf disponible")
else:
    print(f"    ✗ Windows.Data.Pdf no disponible: {r.stderr[:100]}")

# PASO 5: Verificar Windows.Media.Ocr
print("\n[5] Verificando Windows.Media.Ocr (fallback)...")
ps = ("$null=[Windows.Media.Ocr.OcrEngine,Windows.Media.Ocr,ContentType=WindowsRuntime];"
      "$l=[Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages;"
      "Write-Host ('OCR_OK:'+$l.Count+':'+($l|ForEach-Object{$_.LanguageTag})-join',')")
r = subprocess.run(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-Command",ps],
                   capture_output=True, text=True, timeout=10)
if "OCR_OK" in r.stdout:
    partes = r.stdout.strip().split(":")
    print(f"    ✓ Windows.Media.Ocr: {partes[1] if len(partes)>1 else '?'} idioma(s): {partes[2] if len(partes)>2 else ''}")
else:
    print(f"    ✗ Windows.Media.Ocr no disponible")

print("\n" + "=" * 60)
print(" DIAGNOSTICO COMPLETADO")
print("=" * 60)
input("\nPresiona Enter para cerrar...")
