@echo off
rem Genera el informe diario (peligro alto, ultimas 24 h) y, si hay correo configurado, lo envia.
rem Los datos del correo van en "correo.local.bat" (no se sube a git). Ejemplo de contenido:
rem    set GAD_SMTP_HOST=smtp.midominio.es
rem    set GAD_SMTP_PORT=587
rem    set GAD_SMTP_USER=usuario
rem    set GAD_SMTP_PASS=clave
rem    set GAD_MAIL_FROM=remitente@midominio.es
rem    set GAD_MAIL_TO=destino1@midominio.es,destino2@midominio.es
rem Para programarlo cada dia a las 08:00:
rem    schtasks /create /tn "InformeAmenazas" /tr "\"%~f0\"" /sc daily /st 08:00
cd /d "%~dp0"
if exist "correo.local.bat" call "correo.local.bat"
if not exist ".venv\Scripts\python.exe" (
  echo Ejecuta antes INICIAR.bat para crear el entorno.
  exit /b 1
)
set PYTHONPATH=%~dp0
if "%GAD_SMTP_HOST%"=="" (
  ".venv\Scripts\python.exe" -m buscador_noticias.informe_diario --salida informes
) else (
  ".venv\Scripts\python.exe" -m buscador_noticias.informe_diario --enviar --salida informes
)
