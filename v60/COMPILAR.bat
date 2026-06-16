@echo off
chcp 65001 > nul
echo ================================================
echo  GestorPagosMarcovich - Generando .exe
echo ================================================

echo.
echo [1/5] Desinstalando paquetes conflictivos...
pip uninstall pdfplumber pypdfium2 PyMuPDF pymupdf pytesseract -y 2>nul

echo.
echo [2/5] Instalando setuptools (fix pkg_resources)...
pip install setuptools --upgrade --quiet
if errorlevel 1 (
    echo ADVERTENCIA: setuptools no se instalo correctamente
)

echo.
echo [3/5] Reinstalando PyInstaller compatible...
pip uninstall pyinstaller -y 2>nul
pip install "pyinstaller>=6.3.0,<7.0.0" --quiet
if errorlevel 1 (
    echo ERROR: No se pudo instalar PyInstaller.
    pause
    exit /b 1
)

echo.
echo [4/5] Limpiando compilaciones anteriores...
if exist dist\GestorPagosMarcovich.exe (
    taskkill /f /im GestorPagosMarcovich.exe 2>nul
    timeout /t 2 /nobreak >nul
    del /f /q dist\GestorPagosMarcovich.exe 2>nul
)
if exist build rmdir /s /q build 2>nul
if exist GestorPagosMarcovich.spec del /q GestorPagosMarcovich.spec 2>nul

echo.
echo [5/5] Compilando...
pyinstaller --onefile --noconsole --name GestorPagosMarcovich ^
  --add-data "logos;logos" ^
  --icon "logos\selectshop.ico" ^
  --exclude-module pandas --exclude-module numpy --exclude-module scipy ^
  --exclude-module matplotlib --exclude-module pdfplumber --exclude-module pymupdf ^
  --exclude-module pytesseract ^
  app.py

echo.
if exist dist\GestorPagosMarcovich.exe (
    echo ================================================
    echo  EXITO: dist\GestorPagosMarcovich.exe generado
    echo ================================================
    echo  La base de datos (pagos.db) se crea automaticamente
    echo  al ejecutar el .exe por primera vez.
    echo  Para distribuir: comparte solo dist\GestorPagosMarcovich.exe
    echo ================================================
) else (
    echo ================================================
    echo  ERROR: No se genero el .exe. Revisa los errores arriba.
    echo ================================================
)

pause
