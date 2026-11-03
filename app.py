import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from buscador_noticias.ui import run_app

run_app()
