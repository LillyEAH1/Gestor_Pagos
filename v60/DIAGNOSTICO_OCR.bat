@echo off
echo ================================================
echo  SelectShop - Diagnóstico OCR (Windows.Media.Ocr)
echo ================================================
echo.
echo [1] Verificando Windows.Data.Pdf...
powershell -NoProfile -NonInteractive -Command "$null=[Windows.Data.Pdf.PdfDocument,Windows.Data.Pdf,ContentType=WindowsRuntime];Write-Host 'OK - Windows.Data.Pdf disponible'" 2>&1
echo.
echo [2] Verificando Windows.Media.Ocr e idiomas disponibles...
powershell -NoProfile -NonInteractive -Command "$null=[Windows.Media.Ocr.OcrEngine,Windows.Media.Ocr,ContentType=WindowsRuntime];$langs=[Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages;Write-Host ('Idiomas OCR: ' + $langs.Count);foreach($l in $langs){Write-Host ('  - ' + $l.LanguageTag + ' ' + $l.DisplayName)}" 2>&1
echo.
echo [3] Verificando PowerShell...
powershell -NoProfile -Command "$PSVersionTable.PSVersion"
echo.
pause
