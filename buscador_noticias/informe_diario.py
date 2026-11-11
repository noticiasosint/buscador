"""Informe diario: genera el HTML con lo de peligro alto de las últimas 24 h.

Uso:  python -m buscador_noticias.informe_diario [--salida CARPETA]
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

from . import almacen
from .analisis import detectar_picos, puntuar_con_aprendizaje, reputacion_canales
from .config import SECCIONES_INFORME
from .processing import ZONA_MADRID, cumple_ventana_temporal
from .reports import generar_html_ejecutivo
from .resumen import resumen_a_texto, resumir

UMBRAL_ALTO = 66


def seleccionar(alertas, valoraciones):
    rep = reputacion_canales(alertas, valoraciones)
    elegidas = []
    for a in alertas:
        if not cumple_ventana_temporal(a.get("fecha_dt"), 24) or valoraciones.get(a["id"]) in ("falsa", "irrelevante"):
            continue
        if puntuar_con_aprendizaje(a, valoraciones, rep)["peligro"] >= UMBRAL_ALTO:
            elegidas.append(a)
    return elegidas


def construir_informe(alertas):
    """Devuelve (asunto, texto, html) del informe diario."""
    valoraciones = almacen.cargar()["valoraciones"]
    altas = seleccionar(alertas, valoraciones)
    recientes = [a for a in alertas if cumple_ventana_temporal(a.get("fecha_dt"), 24)]
    resumen = resumir(recientes, {c: n for c, n, _ in SECCIONES_INFORME}, "Últimas 24 Horas")
    picos = detectar_picos(alertas)
    texto = resumen_a_texto(resumen)
    if picos:
        texto += "\n\nPicos detectados:\n" + "\n".join(
            f"- {p['termino']} ({p['tipo']}): {p['hoy']} hoy vs {p['media']}/día (×{p['ratio']})" for p in picos
        )
    fecha = datetime.now(ZONA_MADRID).strftime("%d/%m/%Y")
    asunto = f"Informe diario de amenazas {fecha}: {len(altas)} de peligro alto"
    return asunto, texto, generar_html_ejecutivo(altas, ventana_str="ÚLTIMAS 24 H · PELIGRO ALTO")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salida", default=".", help="Carpeta donde guardar el HTML")
    args = ap.parse_args(argv)

    from .dictionary import cargar_diccionario_personalizado
    from .sources import cargar_todas_las_fuentes

    alertas, _ = cargar_todas_las_fuentes(cargar_diccionario_personalizado())
    _, _, html = construir_informe(alertas)
    carpeta = Path(args.salida)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"Informe_diario_{datetime.now(ZONA_MADRID).strftime('%Y%m%d')}.html"
    contenido = html if isinstance(html, bytes) else html.encode("utf-8")
    ruta.write_bytes(contenido)
    print(f"Informe guardado en {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
