"""Resumen de situación de un conjunto de alertas (extractivo, sin servicios externos)."""
import re
from collections import Counter
from datetime import datetime, timezone

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


_TEMAS_REDES = (
    (r"\b(informador\w*|colaborador\w*|reclut\w*|buscamos|captar|captacion|fuentes? (?:en|dentro))\b", "la búsqueda de informadores y colaboradores"),
    (r"\b(ucrania|ucraniano\w*|kiev|kyiv|zelensk\w*|donbas|frente|ucraini\w*|украин\w*)\b", "la guerra de Ucrania"),
    (r"\b(otan|nato|occidente|union europea|bruselas|europa)\b", "la OTAN, la UE y Occidente"),
    (r"\b(sancion\w*|embargo|flota fantasma)\b", "las sanciones"),
    (r"\b(espana|espanol\w*|madrid|sanchez|congreso)\b", "España"),
    (r"\b(putin|kremlin|moscu|lavrov|medvedev|peskov)\b", "el Kremlin y sus dirigentes"),
    (r"\b(china|chino\w*|pekin|xi jinping)\b", "China"),
    (r"\b(gas|petroleo|energia|economia|inflacion|comercio|negocios?|banco\w*)\b", "economía, energía y comercio"),
    (r"\b(migra\w*|inmigra\w*|refugiad\w*)\b", "la inmigración"),
    (r"\b(inteligencia|gru|fsb|svr|cia|espia\w*|espionaje|servicios secretos)\b", "los servicios de inteligencia"),
    (r"\b(desinformacion|propaganda|bulos?|fake|manipulacion)\b", "desinformación y propaganda"),
    (r"\b(dron\w*|misil\w*|bombard\w*|ofensiva|militar\w*|ejercito|armamento|uav)\b", "operaciones y material militar"),
    (r"\b(elecciones|parlamento|partido\w*|gobierno\w*|politic\w*|ministro\w*)\b", "política interna y gobiernos"),
    (r"\b(ciber\w*|hack\w*|ddos)\b", "ciberataques"),
    (r"\b(francia|italia|alemania|polonia|reino unido|marsella|paris|berlin)\b", "otros países europeos"),
    (r"\b(protesta\w*|manifestacion\w*|chalecos amarillos|huelga\w*)\b", "protestas y movilizaciones"),
)
_RUIDO_REDES = {
    "desinformador", "suscribete", "suscribirse", "canal", "telegram", "report", "check", "ahora",
    "cuatro", "internacional", "hacer", "haber", "porque", "tambien", "puede", "estan", "todos",
}


_PATRON_ESPANA = re.compile(
    r"\b(espana|spain|madrid|sanchez|moncloa|guardia civil|policia nacional|cni|barcelona|"
    r"gobierno espanol|ejercito espanol|espanoles)\b"
)


def _lista_natural(elementos):
    elementos = list(elementos)
    if len(elementos) <= 1:
        return "".join(elementos)
    return ", ".join(elementos[:-1]) + " y " + elementos[-1]


def _fecha_corta(dt):
    return dt.strftime("%d/%m") if dt else ""


def _parrafo_canal(canal, items):
    """items: lista de (alerta, texto_limpio, palabras). Devuelve el párrafo y los enlaces de apoyo."""
    fechas = [a["fecha_dt"] for a, _, _ in items if a.get("fecha_dt")]
    n = len(items)
    if fechas:
        desde, hasta = min(fechas), max(fechas)
        dias = max((hasta.date() - desde.date()).days + 1, 1)
        periodo = (
            f"el {_fecha_corta(desde)}" if dias == 1
            else f"entre el {_fecha_corta(desde)} y el {_fecha_corta(hasta)}"
        )
    else:
        periodo = "en las últimas publicaciones"
    texto_norm = [normalizar_texto(t) for _, t, _ in items]
    conteo = Counter()
    for t in texto_norm:
        for patron, etiqueta in _TEMAS_REDES:
            if re.search(patron, t):
                conteo[etiqueta] += 1
    minimo = 2 if n >= 6 else 1
    temas = [e for e, c in conteo.most_common(4) if c >= minimo]
    frase = f"{canal} publicó {n} mensaje{'s' if n != 1 else ''} {periodo}."
    if temas:
        frase += f" Habla principalmente de {_lista_natural(temas)}."
    else:
        frase += " Sus mensajes no se concentran en un tema claro."

    enlaces, usados = [], set()

    def _añadir(a, texto, motivo):
        enlace = _enlace(a)
        if enlace and enlace not in usados:
            usados.add(enlace)
            enlaces.append({"titular": _extracto(texto, 120), "canal": canal, "enlace": enlace, "motivo": motivo})

    con_vistas = [it for it in items if (it[0].get("vistas") or 0) > 0]
    if con_vistas:
        a, texto, _ = max(con_vistas, key=lambda it: it[0]["vistas"])
        _añadir(a, texto, f"Más visto ({a['vistas']:,} visualizaciones)".replace(",", "."))
    sobre_espana = [it for it, t in zip(items, texto_norm) if _PATRON_ESPANA.search(t)]
    if sobre_espana:
        a, texto, _ = max(sobre_espana, key=lambda it: (it[0].get("vistas") or 0, it[0].get("fecha_dt") or datetime.min.replace(tzinfo=timezone.utc)))
        _añadir(a, texto, "Sobre España")
    if not enlaces:
        a, texto, _ = max(items, key=lambda it: it[0].get("fecha_dt") or datetime.min.replace(tzinfo=timezone.utc))
        _añadir(a, texto, "Último mensaje")
    return frase, enlaces


def resumen_redes(alertas, maximo_canales=6):
    """Resumen escrito por canal: de qué habla, en qué fechas y mensajes representativos con enlace."""
    por_canal = {}
    for a in alertas:
        texto = _limpiar_publicacion(a.get("cuerpo") or a.get("titular_raw_limpio") or a.get("titular"))
        if len(texto) < 40:
            continue
        palabras = {
            w for w in re.findall(r"[^\W\d_]{5,}", normalizar_texto(texto))
            if w not in _PALABRAS_VACIAS and w not in _RUIDO and w not in _RUIDO_REDES
        }
        por_canal.setdefault(a.get("canal") or "Canal desconocido", []).append((a, texto, palabras))
    if not por_canal:
        return {"intro": "No hay publicaciones con texto suficiente para resumir.", "parrafos": []}
    total = sum(len(v) for v in por_canal.values())
    ordenados = sorted(por_canal.items(), key=lambda kv: len(kv[1]), reverse=True)[:maximo_canales]
    parrafos = []
    for canal, items in ordenados:
        texto, enlaces = _parrafo_canal(canal, items)
        parrafos.append({"canal": canal, "texto": texto, "enlaces": enlaces})
    intro = f"{total} publicaciones de {len(por_canal)} canal(es) analizadas."
    return {"intro": intro, "parrafos": parrafos}


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
