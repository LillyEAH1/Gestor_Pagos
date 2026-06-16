GestorPagosIT — Instrucciones
══════════════════════════════

DISTRIBUCIÓN PARA USUARIOS (zip final):
  GestorPagosIT.exe   ← doble clic para abrir
  pagos.db            ← BD con todos los proveedores precargados
                         → copiar a tu carpeta de OneDrive

PARA GENERAR EL .EXE (solo una vez en tu PC):
  1. INSTALAR.bat     ← instala dependencias
  2. COMPILAR.bat     ← genera dist\GestorPagosIT.exe

QUÉ INCLUYE LA BD (pagos.db):
  ✓ 378 proveedores con CLABE y banco
  ✓ 93 combinaciones de Sucursal + Centro de Costos  
  ✓ 38 servicios recurrentes de TI (Telmex, Totalplay, IZZI, etc.)
  ✓ Tabla de pagos vacía (historial)

PRIMERA VEZ:
  La app detecta OneDrive automáticamente.
  Solo escribe tu nombre y confirma la ruta del pagos.db.

MÓDULOS:
  app.py             Interfaz (4 pestañas)
  database.py        BD SQLite — CRUD completo
  config.py          Configuración de la app
  exportar.py        PDF solicitud + Excel estado de cuenta
  ocr_scanner.py     Lee PDF/imagen del recibo → autorrellena
  outlook_alertas.py Recordatorios en Outlook
  numero_letra.py    Importe en letra automático
  onedrive_path.py   Detecta OneDrive automáticamente
