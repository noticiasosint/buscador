import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from buscador_noticias.persistencia import iniciar as restaurar_datos
from buscador_noticias.ui import run_app

# Importar aquí evita que un rerun de Streamlit interrumpa la primera importación
import buscador_noticias.sources  # noqa: E402,F401


restaurar_datos()
run_app()
