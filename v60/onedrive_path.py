"""
onedrive_path.py
Detecta automáticamente la carpeta de OneDrive del usuario actual.
Funciona con OneDrive personal y OneDrive for Business (Microsoft 365).
"""
import os
import re
from pathlib import Path


def detectar_onedrive() -> Path | None:
    """
    Devuelve la ruta a la carpeta raíz de OneDrive sincronizada.
    Prioriza OneDrive for Business (corporativo) sobre el personal.
    """
    # 1. Variable de entorno — la más confiable
    for var in ["OneDriveCommercial", "OneDrive"]:
        val = os.environ.get(var)
        if val and Path(val).exists():
            return Path(val)

    # 2. Leer del registro de Windows (más robusto)
    try:
        import winreg
        rutas_candidatas = []

        # OneDrive for Business
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\OneDrive\Accounts")
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)
                    try:
                        val, _ = winreg.QueryValueEx(subkey, "UserFolder")
                        if Path(val).exists():
                            rutas_candidatas.append(("business", Path(val)))
                    except FileNotFoundError:
                        pass
                    i += 1
                except OSError:
                    break
        except FileNotFoundError:
            pass

        # Preferir corporativo
        for tipo, ruta in rutas_candidatas:
            if tipo == "business":
                return ruta
        for tipo, ruta in rutas_candidatas:
            return ruta

    except ImportError:
        pass  # No estamos en Windows

    # 3. Rutas típicas como fallback
    home = Path.home()
    candidatas = [
        home / "OneDrive - SelectShop",
        home / "OneDrive - selectshop",
    ]
    # Buscar cualquier carpeta que empiece con "OneDrive"
    for item in home.iterdir():
        if item.is_dir() and item.name.lower().startswith("onedrive"):
            candidatas.insert(0, item)

    for ruta in candidatas:
        if ruta.exists():
            return ruta

    return None


def ruta_db_onedrive(nombre_carpeta: str = "GestorPagosIT",
                     nombre_db: str = "pagos.db") -> Path | None:
    """
    Devuelve la ruta completa al archivo .db dentro de OneDrive.
    Crea la subcarpeta si no existe.
    Devuelve None si no se encuentra OneDrive.
    """
    od = detectar_onedrive()
    if not od:
        return None
    carpeta = od / nombre_carpeta
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta / nombre_db
