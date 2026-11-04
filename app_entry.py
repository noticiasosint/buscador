import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from buscador_noticias.ui import run_app

# Importar aquí evita que un rerun de Streamlit interrumpa la primera importación
import buscador_noticias.sources  # noqa: E402,F401


run_app()
