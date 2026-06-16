"""
config.py v25 — config en AppData, autodetecta ruta OneDrive como sugerencia.
"""
import json, os
from pathlib import Path

_APP_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "GestorPagosIT"
_APP_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = _APP_DIR / "config.json"
CONFIG_VERSION = 25

DEFAULTS = {
    "config_version":  CONFIG_VERSION,
    "db_path":         "",
    "dias_alerta":     3,
    "analista_nombre": "",
    "gerente_nombre":  "",
    # La key NUNCA va hardcodeada en el código. Se lee de la variable de entorno
    # GROQ_API_KEY (ver .env / .env.example). Si no existe, queda vacía y la app
    # la pide en Configuración.
    "groq_api_key":    os.environ.get("GROQ_API_KEY", ""),
}

def cargar() -> dict:
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text())
            if saved.get("config_version", 0) < CONFIG_VERSION:
                fresh = dict(DEFAULTS)
                for k in ("analista_nombre", "gerente_nombre", "dias_alerta", "groq_api_key"):
                    if saved.get(k):
                        fresh[k] = saved[k]
                # Re-guardar con versión actualizada y key por default
                guardar(fresh)
                return fresh
            merged = {**DEFAULTS, **saved}
            return merged
        except Exception:
            pass
    # Primera vez: no existe config.json — crearlo en disco con los DEFAULTS (incluye la key)
    cfg_inicial = dict(DEFAULTS)
    guardar(cfg_inicial)
    return cfg_inicial

def guardar(cfg: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

def configurado() -> bool:
    return bool(cargar().get("db_path"))

def sugerir_ruta_db() -> str:
    """Sugiere ruta de pagos.db en OneDrive, retorna string vacío si no encuentra."""
    try:
        from onedrive_path import ruta_db_onedrive
        ruta = ruta_db_onedrive()
        return str(ruta) if ruta else ""
    except Exception:
        return ""
