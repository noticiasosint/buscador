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
.venv\Scripts\python.exe -m streamlit run app_entry.py --server.port 8501
pause
