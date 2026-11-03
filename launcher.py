import os
import sys
from pathlib import Path


def main():
    if getattr(sys, "frozen", False):
        app_dir = Path(sys._MEIPASS)
    else:
        app_dir = Path(__file__).resolve().parent

    app_script = app_dir / "app_entry.py"
    if not app_script.is_file():
        raise FileNotFoundError(f"No se encontró el punto de entrada: {app_script}")

    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    from streamlit.web import cli as streamlit_cli

    sys.argv = [
        "streamlit",
        "run",
        str(app_script),
        "--global.developmentMode=false",
        "--server.address=127.0.0.1",
        "--server.port=8501",
        "--server.headless=false",
        "--server.showEmailPrompt=false",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    streamlit_cli.main()


if __name__ == "__main__":
    main()
