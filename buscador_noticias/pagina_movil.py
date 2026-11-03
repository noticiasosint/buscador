"""Página estática ligera (un solo HTML) con las últimas noticias, pensada para el móvil.

Uso:  python -m buscador_noticias.pagina_movil [--salida CARPETA]
Después se cifra con contraseña (StatiCrypt) y se publica en GitHub Pages; ver .github/workflows/pagina_movil.yml
"""
import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from .analisis import puntuar_con_aprendizaje
from .config import SECCIONES_INFORME
from .pagina_plantilla import PLANTILLA
from .config import SINONIMOS_MULTILINGUES
from .processing import ZONA_MADRID, es_url_segura, normalizar_texto, obtener_fecha_madrid_str

MAX_ALERTAS = 1200

def _seccion(a):
    return "TELEGRAM" if a.get("plataforma") == "TELEGRAM" else "REDES" if a.get("plataforma") == "REDES" else a.get("categoria", "")


def _nombre_corto(nombre):
    nombre = re.sub(r"^SECCIÓN \d+:\s*", "", nombre)
    return re.sub(r"\s*\(.*", "", nombre).strip().capitalize()


def _json_seguro(obj):
    # Evita cerrar el <script> desde dentro de los datos.
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")


def construir_pagina(alertas, actualizado=None):
    ordenadas = sorted(
        (a for a in alertas if a.get("fecha_dt")),
        key=lambda a: a["fecha_dt"],
        reverse=True,
    )[:MAX_ALERTAS]
    datos = []
    for a in ordenadas:
        enlace = a.get("enlace") or ""
        d = {
            "t": (a.get("titular") or "")[:300],
            "c": a.get("canal") or "",
            "f": a["fecha_dt"].astimezone(ZONA_MADRID).strftime("%d/%m %H:%M"),
            "e": int(a["fecha_dt"].timestamp()),
            "s": _seccion(a),
            "k": a.get("categoria", ""),
            "b": (a.get("cuerpo") or "")[:350] if len(a.get("cuerpo") or "") > 15 else "",
            "h": normalizar_texto(f"{a.get('titular') or ''} {a.get('cuerpo') or ''}")[:2500],
            "x": (a.get("evaluacion_contexto") or "")[:300],
            "n": int(a.get("num_fuentes") or 1),
            "u": enlace if es_url_segura(enlace) else "",
        }
        try:
            pun = puntuar_con_aprendizaje(a, {}, {})
            d["fi"], d["pe"] = int(pun["fiabilidad"]), int(pun["peligro"])
        except Exception:
            pass
        datos.append(d)
    usadas = {d["s"] for d in datos}
    secciones = [[c, _nombre_corto(n)] for c, n, _ in SECCIONES_INFORME if c in usadas]
    if "TELEGRAM" in usadas and not any(c == "TELEGRAM" for c, _ in secciones):
        secciones.append(["TELEGRAM", "Telegram"])
    if "REDES" in usadas and not any(c == "REDES" for c, _ in secciones):
        secciones.append(["REDES", "Redes"])
    sinonimos = {
        normalizar_texto(k).strip(): [normalizar_texto(x) for x in v]
        for k, v in SINONIMOS_MULTILINGUES.items()
    }
    return (
        PLANTILLA.replace("__ACTUALIZADO__", html.escape(actualizado or obtener_fecha_madrid_str()))
        .replace("__SECCIONES__", _json_seguro(secciones))
        .replace("__SINONIMOS__", _json_seguro(sinonimos))
        .replace("__DATOS__", _json_seguro(datos))
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--salida", default="pagina", help="Carpeta donde guardar index.html")
    args = ap.parse_args(argv)

    from .dictionary import cargar_diccionario_personalizado
    from .sources import cargar_todas_las_fuentes

    alertas, _ = cargar_todas_las_fuentes(cargar_diccionario_personalizado())
    carpeta = Path(args.salida)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "index.html"
    ruta.write_text(construir_pagina(alertas), encoding="utf-8")
    print(f"Página guardada en {ruta} ({len(alertas)} alertas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
