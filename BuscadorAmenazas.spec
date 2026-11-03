# -*- mode: python ; coding: utf-8 -*-

import sys

from pathlib import Path

from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import collect_submodules


sys.path.insert(0, SPECPATH)

streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all("streamlit")
app_hiddenimports = collect_submodules("buscador_noticias")
translator_datas, translator_binaries, translator_hiddenimports = collect_all("deep_translator")

a = Analysis(
    ["launcher.py"],
    pathex=[SPECPATH],
    binaries=streamlit_binaries + translator_binaries,
    datas=streamlit_datas + translator_datas + [("app_entry.py", ".")],
    hiddenimports=streamlit_hiddenimports + translator_hiddenimports + app_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BuscadorAmenazas",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
)
