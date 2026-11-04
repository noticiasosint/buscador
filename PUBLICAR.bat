@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Instala Python 3.10 o superior desde https://www.python.org/downloads/ ^(marca "Add Python to PATH"^) y vuelve a abrir este archivo.
  pause
  exit /b 1
)
if not exist .venv (
  echo Primera vez: instalando dependencias, tarda un par de minutos...
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install -q -r requirements.txt
)
where cloudflared >nul 2>nul
if errorlevel 1 (
  echo Instalando cloudflared ^(tunel gratuito de Cloudflare, sin cuenta^)...
  winget install --id Cloudflare.cloudflared -e --accept-package-agreements --accept-source-agreements
  echo Cierra esta ventana y vuelve a abrir PUBLICAR.bat para continuar.
  pause
  exit /b 0
)
echo Arrancando la aplicacion en este PC...
start "Buscador (no cerrar)" /min .venv\Scripts\python.exe -m streamlit run app_entry.py --server.port 8501 --server.headless true --browser.gatherUsageStats false
echo.
echo Espera unos segundos: abajo aparecera una direccion https://....trycloudflare.com
echo Compartela con quien deba entrar. Cambia cada vez que ejecutes este archivo.
echo Mientras esta ventana y este PC esten encendidos, la app sera accesible.
echo.
timeout /t 8 /nobreak >nul
cloudflared tunnel --url http://localhost:8501
pause
