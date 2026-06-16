@echo off
chcp 65001 > nul
echo ================================================
echo  GestorPagosMarcovich - Instalando dependencias
echo ================================================

echo.
echo [1/3] Instalando setuptools (requerido por PyInstaller)...
pip install setuptools --upgrade
if errorlevel 1 (
    echo ERROR instalando setuptools
    pause
    exit /b 1
)

echo.
echo [2/3] Instalando dependencias de la app...
pip install ^
  "customtkinter>=5.2.2" ^
  "openpyxl>=3.1.2" ^
  "reportlab>=4.1.0" ^
  "Pillow>=10.4.0" ^
  "pypdf>=3.0.0" ^
  "pywin32>=306" ^
  "requests>=2.31.0"
if errorlevel 1 (
    echo ERROR instalando dependencias
    pause
    exit /b 1
)

echo.
echo [3/3] Instalando PyInstaller (version compatible)...
pip uninstall pyinstaller -y 2>nul
pip install "pyinstaller>=6.3.0,<7.0.0"
if errorlevel 1 (
    echo ERROR instalando PyInstaller
    pause
    exit /b 1
)

echo.
echo ================================================
echo  Listo. Ejecuta: python app.py
echo  O para compilar el .exe: COMPILAR.bat
echo.
echo  OPCIONAL - OCR con IA (Groq Vision):
echo  1. Entra a https://console.groq.com
echo  2. Crea una cuenta gratuita
echo  3. Ve a "API Keys" y genera una key
echo  4. En la app, pega la key en Configuracion
echo     en el campo "Groq API Key"
echo  Sin la key el OCR usa texto nativo del PDF.
echo ================================================
pause
