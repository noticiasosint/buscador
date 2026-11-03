import os
import threading
import time

import requests
import streamlit as st

INTERVALO_PRECARGA = int(os.environ.get("PRECARGA_MINUTOS", "30")) * 60
INTERVALO_PING = 600


def _diccionarios_a_precargar():
    from . import usuarios
    from .dictionary import cargar_diccionario_efectivo

    vistos, resultado = set(), []
    for u in usuarios.listar():
        try:
            diccionario = cargar_diccionario_efectivo(u["usuario"])
        except Exception:
            continue
        clave = repr(diccionario)
        if clave not in vistos:
            vistos.add(clave)
            resultado.append(diccionario)
    return resultado or [()]


def _bucle_precarga():
    from .sources import cargar_todas_las_fuentes

    while True:
        try:
            for diccionario in _diccionarios_a_precargar():
                cargar_todas_las_fuentes(diccionario)
        except Exception:
            pass
        time.sleep(INTERVALO_PRECARGA)


def _bucle_ping(url):
    while True:
        time.sleep(INTERVALO_PING)
        try:
            requests.get(url, timeout=20)
        except requests.RequestException:
            pass


@st.cache_resource
def iniciar_keepalive():
    """Precarga las noticias al arrancar y las refresca cada cierto tiempo, para que al entrar ya estén listas."""
    threading.Thread(target=_bucle_precarga, daemon=True).start()
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if url:
        threading.Thread(target=_bucle_ping, args=(url,), daemon=True).start()
    return True
