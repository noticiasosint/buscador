$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$venv = Join-Path $root ".build-venv"
$python = Join-Path $venv "Scripts\python.exe"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "No se encontró el lanzador de Python 'py'. Instala Python 3.11 de 64 bits."
}

if (-not (Test-Path -LiteralPath $python)) {
    & py -3.11 -m venv $venv
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo crear el entorno virtual de compilación."
    }
}

& $python -m pip install -r (Join-Path $root "requirements-build.txt")
if ($LASTEXITCODE -ne 0) {
    throw "No se pudieron instalar las dependencias de compilación."
}

& $python -m PyInstaller --clean --noconfirm `
    --distpath (Join-Path $root "dist") `
    --workpath (Join-Path $root "build\pyinstaller") `
    (Join-Path $root "BuscadorAmenazas.spec")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller no pudo generar el ejecutable."
}

Write-Host "Ejecutable creado: $(Join-Path $root 'dist\BuscadorAmenazas.exe')"
