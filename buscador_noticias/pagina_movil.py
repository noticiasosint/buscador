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

from .config import SECCIONES_INFORME
from .processing import ZONA_MADRID, es_url_segura, obtener_fecha_madrid_str

MAX_ALERTAS = 400

PLANTILLA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0f172a">
<title>Amenazas híbridas</title>
<style>
*{box-sizing:border-box}body{margin:0;font:16px/1.4 system-ui,sans-serif;background:#f1f5f9;color:#0f172a}
header{position:sticky;top:0;background:#0f172a;color:#fff;padding:10px 12px;z-index:5}
header h1{margin:0 0 6px;font-size:17px}header small{color:#94a3b8}
#q{width:100%;padding:10px;border:0;border-radius:8px;font-size:16px;margin-top:6px}
#chips{display:flex;gap:6px;overflow-x:auto;padding:8px 12px;background:#e2e8f0;position:sticky;top:96px;z-index:4}
.chip{flex:none;border:0;border-radius:16px;padding:7px 12px;background:#fff;font-size:14px;cursor:pointer}
.chip.on{background:#dc2626;color:#fff}
main{padding:10px 12px 40px}
article{background:#fff;border-left:5px solid #38bdf8;border-radius:8px;padding:10px 12px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.12)}
article h2{font-size:16px;margin:4px 0}article .m{font-size:12px;color:#64748b}
article a{display:inline-block;margin-top:6px;color:#fff;background:#0f172a;padding:7px 12px;border-radius:6px;text-decoration:none;font-size:14px}
#mas{display:block;margin:12px auto;padding:10px 20px;border:0;border-radius:8px;background:#0f172a;color:#fff;font-size:15px}
</style></head><body>
<header><h1>🛡️ Amenazas híbridas</h1><small>Actualizado: __ACTUALIZADO__ · <span id="n"></span></small>
<input id="q" type="search" placeholder="Buscar…" autocomplete="off"></header>
<div id="chips"></div><main id="lista"></main><button id="mas" hidden>Ver más</button>
<script>
const D=__DATOS__;const SEC=__SECCIONES__;
let sec="",txt="",tope=30;
const $=i=>document.getElementById(i);
const norm=s=>(s||"").toLowerCase().normalize("NFD").replace(/[\\u0300-\\u036f]/g,"");
function chips(){const c=$("chips");c.innerHTML="";
 [["","Todo"],...SEC].forEach(([k,n])=>{const b=document.createElement("button");b.className="chip"+(k===sec?" on":"");b.textContent=n;
  b.onclick=()=>{sec=k;tope=30;chips();pinta()};c.appendChild(b)})}
function pinta(){
 const t=norm(txt);const L=D.filter(a=>(!sec||a.s===sec)&&(!t||norm(a.t+" "+a.c).includes(t)));
 $("n").textContent=L.length+" noticias";const m=$("lista");m.innerHTML="";
 L.slice(0,tope).forEach(a=>{const e=document.createElement("article");
  const mt=document.createElement("div");mt.className="m";mt.textContent=a.f+" · "+a.c;
  const h=document.createElement("h2");h.textContent=a.t;e.append(mt,h);
  if(a.u){const l=document.createElement("a");l.href=a.u;l.target="_blank";l.rel="noopener noreferrer";l.textContent="Abrir fuente";e.append(l)}
  m.append(e)});
 $("mas").hidden=L.length<=tope}
$("q").oninput=e=>{txt=e.target.value;tope=30;pinta()};
$("mas").onclick=()=>{tope+=30;pinta()};
chips();pinta();
</script></body></html>"""


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
        datos.append({
            "t": (a.get("titular") or "")[:300],
            "c": a.get("canal") or "",
            "f": a["fecha_dt"].astimezone(ZONA_MADRID).strftime("%d/%m %H:%M"),
            "s": _seccion(a),
            "u": enlace if es_url_segura(enlace) else "",
        })
    usadas = {d["s"] for d in datos}
    secciones = [[c, _nombre_corto(n)] for c, n, _ in SECCIONES_INFORME if c in usadas]
    if "TELEGRAM" in usadas and not any(c == "TELEGRAM" for c, _ in secciones):
        secciones.append(["TELEGRAM", "Telegram"])
    if "REDES" in usadas and not any(c == "REDES" for c, _ in secciones):
        secciones.append(["REDES", "Redes"])
    return (
        PLANTILLA.replace("__ACTUALIZADO__", html.escape(actualizado or obtener_fecha_madrid_str()))
        .replace("__SECCIONES__", _json_seguro(secciones))
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
