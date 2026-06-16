@echo off
chcp 65001 > nul
echo ================================================
echo  GestorPagosIT - Resetear configuracion
echo ================================================
echo Este script borra la configuracion guardada para
echo que la app arranque como si fuera primera vez.
echo (No borra tus datos de pagos, solo la configuracion)

set CONFIG_DIR=%LOCALAPPDATA%\GestorPagosIT
if exist "%CONFIG_DIR%" (
    rmdir /s /q "%CONFIG_DIR%"
    echo OK - Configuracion borrada.
) else (
    echo No habia configuracion guardada.
)
echo Ahora abre la app y configura desde cero.
pause
