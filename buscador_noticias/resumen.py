"""Resumen de situación de un conjunto de alertas (extractivo, sin servicios externos)."""
import re
from collections import Counter

from .processing import _PALABRAS_VACIAS, es_url_segura, normalizar_texto
from .scoring import puntuar

_RUIDO = {
    "segun", "tras", "sobre", "entre", "desde", "hasta", "nuevo", "nueva", "nuevos", "mientras",
    "dice", "afirma", "anuncia", "that", "with", "from", "have", "will", "este", "esta", "como",
    "para", "mas", "mayor", "dos", "tres", "ante", "contra", "durante",
    "rusia", "ruso", "rusos", "rusa", "russia", "russian", "ucrania", "ucraniano", "ukraine", "ukrainian",
}
UMBRAL_ALTO = 66
MAX_EJEMPLOS = 3


def _enlace(a):
    url = str(a.get("enlace") or "")
    return url if url and es_url_segura(url) else ""


def _ejemplo(a):
    return {
        "titular": a.get("titular_raw_limpio") or a.get("titular") or "",
        "canal": a.get("canal") or "",
        "enlace": _enlace(a),
    }


def _ejemplos(coleccion, clave_orden):
    """Hasta MAX_EJEMPLOS noticias con enlace válido, las más peligrosas primero."""
    vistos, salida = set(), []
    for a, p in sorted(coleccion, key=clave_orden, reverse=True):
        e = _ejemplo(a)
        if e["enlace"] and e["enlace"] not in vistos:
            vistos.add(e["enlace"])
            salida.append(e)
            if len(salida) == MAX_EJEMPLOS:
                break
    return salida


def _temas(puntuadas, maximo=8):
    cuenta = Counter()
    donde = {}
    for a, p in puntuadas:
        titular = normalizar_texto(str(a.get("titular_raw_limpio") or a.get("titular") or ""))
        if a.get("plataforma") in ("TELEGRAM", "REDES"):
            titular += " " + normalizar_texto(str(a.get("cuerpo") or "")[:400])
        palabras = {w for w in re.findall(r"[^\W\d_]{5,}", titular) if w not in _PALABRAS_VACIAS and w not in _RUIDO}
        cuenta.update(palabras)
        for w in palabras:
            donde.setdefault(w, []).append((a, p))
    orden = lambda t: (t[1]["peligro"], t[1]["fiabilidad"])
    return [[w, n, _ejemplos(donde[w], orden)] for w, n in cuenta.most_common(maximo) if n >= 2]


def resumir(alertas, nombres_categorias=None, ventana="", top=5):
    """Devuelve un dict con las cifras clave y las alertas más relevantes."""
    nombres_categorias = nombres_categorias or {}
    puntuadas = [(a, puntuar(a)) for a in alertas]
    por_categoria = Counter(a.get("categoria", "GLOBAL") for a in alertas)
    actores = Counter(n for a in alertas for n, _ in a.get("etiquetas_ner", []))
    donde_actor = {}
    for a, p in puntuadas:
        for n in {n for n, _ in a.get("etiquetas_ner", [])}:
            donde_actor.setdefault(n, []).append((a, p))
    orden = lambda t: (t[1]["peligro"], t[1]["fiabilidad"])
    lista_actores = [[n, c, _ejemplos(donde_actor[n], orden)] for n, c in actores.most_common(6)]
    altas = [(a, p) for a, p in puntuadas if p["peligro"] >= UMBRAL_ALTO]
    corroboradas = sum(1 for a in alertas if a.get("num_fuentes", 1) > 1)
    ranking = sorted(puntuadas, key=lambda t: (t[1]["peligro"], t[1]["fiabilidad"]), reverse=True)[:top]

    destacadas = [
        {
            "id": a.get("id"),
            "titular": a.get("titular_raw_limpio") or a.get("titular"),
            "canal": a.get("canal"),
            "categoria": a.get("categoria"),
            "fecha_texto": None,
            "peligro": p["peligro"],
            "fiabilidad": p["fiabilidad"],
            "num_fuentes": a.get("num_fuentes", 1),
            "enlace": _enlace(a),
        }
        for a, p in ranking
    ]
    donde_cat = {}
    for a, p in puntuadas:
        donde_cat.setdefault(a.get("categoria", "GLOBAL"), []).append((a, p))
    categorias = [
        {"codigo": c, "nombre": nombres_categorias.get(c, c), "total": n, "ejemplos": _ejemplos(donde_cat[c], orden)}
        for c, n in por_categoria.most_common()
    ]
    total = len(alertas)
    if total:
        titulo = (
            f"{total} alertas{(' · ' + ventana) if ventana else ''}: "
            f"{len(altas)} de peligro alto, {corroboradas} confirmadas por varias fuentes."
        )
    else:
        titulo = "No hay alertas que resumir con los filtros actuales."
    return {
        "titulo": titulo,
        "total": total,
        "peligro_alto": len(altas),
        "corroboradas": corroboradas,
        "categorias": categorias,
        "actores": lista_actores,
        "temas": _temas(puntuadas),
        "canales": Counter(a.get("canal") for a in alertas if a.get("canal")).most_common(5),
        "destacadas": destacadas,
        "aviso": "Resumen automático basado en estimaciones; no verifica los hechos.",
    }


def _limpiar_publicacion(texto):
    texto = re.sub(r"https?://\S+|\b(?:t|tg)\.me/\S+", " ", str(texto or ""))
    texto = re.sub(r"[#@]\w+", " ", texto)
    texto = re.sub(r"[^\w\s.,;:¿?¡!()%\"'«»\-–—/]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _extracto(texto, maximo=260):
    frases = re.split(r"(?<=[.!?])\s+", texto)
    salida = ""
    for frase in frases:
        if salida and len(salida) + len(frase) > maximo:
            break
        salida = f"{salida} {frase}".strip()
        if len(salida) >= maximo // 2:
            break
    return salida[:maximo].rstrip() + ("…" if len(salida) > maximo else "")


def resumen_redes(alertas, maximo_puntos=5):
    """Resumen en prosa de lo que dicen las publicaciones: temas dominantes y mensajes representativos."""
    publicaciones = []
    for a in alertas:
        texto = _limpiar_publicacion(a.get("cuerpo") or a.get("titular_raw_limpio") or a.get("titular"))
        if len(texto) < 40:
            continue
        palabras = {
            w for w in re.findall(r"[^\W\d_]{5,}", normalizar_texto(texto))
            if w not in _PALABRAS_VACIAS and w not in _RUIDO
        }
        publicaciones.append((a, texto, palabras))
    if not publicaciones:
        return {"intro": "No hay publicaciones con texto suficiente para resumir.", "temas": [], "puntos": []}

    frecuencia = Counter(w for _, _, palabras in publicaciones for w in palabras)
    temas = [w for w, n in frecuencia.most_common(8) if n >= 2]
    relevantes = {w for w, n in frecuencia.most_common(40) if n >= 2}

    def puntuacion(item):
        _, _, palabras = item
        return sum(frecuencia[w] for w in palabras & relevantes) / (len(palabras) ** 0.5 or 1)

    puntos, usadas = [], []
    for a, texto, palabras in sorted(publicaciones, key=puntuacion, reverse=True):
        if any(len(palabras & u) / (len(palabras | u) or 1) > 0.45 for u in usadas):
            continue
        usadas.append(palabras)
        puntos.append({"canal": a.get("canal") or "", "texto": _extracto(texto)})
        if len(puntos) == maximo_puntos:
            break

    canales = Counter(a.get("canal") for a, _, _ in publicaciones if a.get("canal"))
    intro = f"{len(publicaciones)} publicaciones de {len(canales)} canal(es)."
    if temas:
        intro += " Se habla sobre todo de: " + ", ".join(temas) + "."
    return {"intro": intro, "temas": temas, "puntos": puntos}


def _md_texto(texto):
    return re.sub(r"([\\`*_{}\[\]<>#|])", r"\\\1", str(texto or ""))


def enlace_md(texto, url):
    """Enlace Markdown seguro; sin URL válida devuelve solo el texto."""
    if not url:
        return _md_texto(texto)
    destino = url.replace(" ", "%20").replace("(", "%28").replace(")", "%29")
    return f"[{_md_texto(texto)}]({destino})"


def enlaces_numerados_md(ejemplos):
    """' 🔗 [1] [2] [3]' con el título y el canal como ayuda al pasar el ratón."""
    if not ejemplos:
        return ""
    partes = []
    for i, e in enumerate(ejemplos, 1):
        destino = e["enlace"].replace(" ", "%20").replace("(", "%28").replace(")", "%29")
        ayuda = f'{e.get("canal", "")}: {e.get("titular", "")}'.replace('"', "'")[:140]
        partes.append(f'[{i}]({destino} "{ayuda}")')
    return " 🔗 " + " ".join(partes)


def resumen_a_texto(r):
    lineas = [r["titulo"]]
    if r["categorias"]:
        lineas.append("Por área: " + ", ".join(f"{c['nombre']} ({c['total']})" for c in r["categorias"][:5]) + ".")
    if r["actores"]:
        lineas.append("Actores más citados: " + ", ".join(f"{n} ({c})" for n, c, _ in r["actores"]) + ".")
    if r["temas"]:
        lineas.append("Temas recurrentes: " + ", ".join(f"{t} ({c})" for t, c, _ in r["temas"]) + ".")
    return "\n".join(lineas)
