@echo off
rem Genera el informe diario (peligro alto, ultimas 24 h) en la carpeta informes.
rem Para programarlo cada dia a las 08:00:
rem    schtasks /create /tn "InformeAmenazas" /tr "\"%~f0\"" /sc daily /st 08:00
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ejecuta antes INICIAR.bat para crear el entorno.
  exit /b 1
)
set PYTHONPATH=%~dp0
".venv\Scripts\python.exe" -m buscador_noticias.informe_diario --salida informes
