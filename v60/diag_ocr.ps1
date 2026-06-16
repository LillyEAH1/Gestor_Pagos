Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine,Windows.Media.Ocr,ContentType=WindowsRuntime]
$langs = [Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages
$tags = ($langs | ForEach-Object { $_.LanguageTag }) -join ', '
Write-Host "OK - $($langs.Count) idioma(s): $tags"
