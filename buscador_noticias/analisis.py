"""Análisis sobre el conjunto de alertas: picos, novedades, línea de tiempo, hilos y aprendizaje."""
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from .processing import _PALABRAS_VACIAS, normalizar_texto
from .resumen import _RUIDO
from .scoring import puntuar

ZONA_UTC = timezone.utc

ETIQUETAS_AREA = {
    "ESPANA": "🇪🇸 ESPAÑA", "AGENCIAS": "🕵️‍♂️ AGENCIAS", "EMPRESA": "🏢 EMPRESAS", "GLOBAL": "📰 GLOBAL",
    "CRIPTO": "🟣 CRIPTO", "SANCIONES": "📦 SANCIONES", "DETENCION": "🛑 DETENCIONES", "CHINA": "🇨🇳 CHINA",
    "CRIMENES": "⚖️ CRÍMENES", "DRONES": "🛸 DRONES", "INJERENCIA": "🗳️ INJERENCIA", "OTAN": "🛡️ OTAN",
    "ASESINATOS": "🔎 ASESINATOS", "TELEGRAM": "✈️ TELEGRAM", "REDES": "🌐 REDES",
}


def _utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZONA_UTC)
    return dt.astimezone(ZONA_UTC)


def _palabras(titular):
    t = normalizar_texto(str(titular or ""))
    return {w for w in re.findall(r"[^\W\d_]{5,}", t) if w not in _PALABRAS_VACIAS and w not in _RUIDO}


def _terminos(a):
    t = {f"actor:{n}" for n, _ in a.get("etiquetas_ner", [])}
    t.add(f"área:{a.get('categoria', 'GLOBAL')}")
    t |= {f"tema:{w}" for w in _palabras(a.get("titular_raw_limpio") or a.get("titular"))}
    return t


# 1. Picos ---------------------------------------------------------------

def detectar_picos(alertas, ahora=None, minimo=3, factor=2.0, maximo=8):
    """Términos que hoy (últimas 24 h) superan `factor` veces su media diaria de los 6 días previos."""
    ahora = _utc(ahora) or datetime.now(ZONA_UTC)
    hoy, previos = Counter(), Counter()
    areas = defaultdict(Counter)
    for a in alertas:
        if a.get("fecha_estimada"):
            continue
        f = _utc(a.get("fecha_dt"))
        if not f:
            continue
        h = (ahora - f).total_seconds() / 3600
        if 0 <= h <= 24:
            terminos = _terminos(a)
            hoy.update(terminos)
            zonas = {a.get("categoria")} | ({a.get("plataforma")} & {"TELEGRAM", "REDES"})
            for t in terminos:
                areas[t].update(z for z in zonas if z in ETIQUETAS_AREA)
        elif 24 < h <= 168:
            previos.update(_terminos(a))
    picos = []
    for t, n in hoy.items():
        media = previos[t] / 6
        ratio = n / max(media, 1.0)
        if n >= minimo and ratio >= factor:
            tipo, nombre = t.split(":", 1)
            zonas = [{"codigo": c, "etiqueta": ETIQUETAS_AREA[c], "n": k} for c, k in areas[t].most_common(3)]
            picos.append({"tipo": tipo, "termino": nombre, "hoy": n, "media": round(media, 1), "ratio": round(ratio, 1), "areas": zonas})
    picos.sort(key=lambda p: (p["ratio"], p["hoy"]), reverse=True)
    return picos[:maximo]


# 2. Novedades ----------------------------------------------------------- -----------------------------------------------------------

def ids_nuevos(alertas, previos, visitado):
    """Ids no vistos en visitas anteriores. En la primera visita nada se marca como nuevo."""
    if not visitado:
        return set()
    return {a["id"] for a in alertas if a["id"] not in previos}


# 4. Línea de tiempo -----------------------------------------------------

def linea_tiempo(alertas, horas=48, ahora=None, umbral_alto=66):
    """Alertas por hora (hasta 48 h) o por día, con las de peligro alto aparte."""
    ahora = _utc(ahora) or datetime.now(ZONA_UTC)
    por_hora = horas <= 48
    paso = timedelta(hours=1) if por_hora else timedelta(days=1)
    n = horas if por_hora else max(1, horas // 24)
    fin = ahora.replace(minute=0, second=0, microsecond=0) if por_hora else ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    cubos = [fin - paso * i for i in range(n - 1, -1, -1)]
    cuenta = {c: [0, 0] for c in cubos}
    for a in alertas:
        if a.get("fecha_estimada"):
            continue
        f = _utc(a.get("fecha_dt"))
        if not f or f > ahora:
            continue
        c = f.replace(minute=0, second=0, microsecond=0) if por_hora else f.replace(hour=0, minute=0, second=0, microsecond=0)
        if c in cuenta:
            cuenta[c][0] += 1
            if puntuar(a)["peligro"] >= umbral_alto:
                cuenta[c][1] += 1
    formato = "%d/%m %H:00" if por_hora else "%d/%m"
    return [
        {"etiqueta": c.astimezone(_zona()).strftime(formato), "total": v[0], "peligro_alto": v[1]}
        for c, v in cuenta.items()
    ]


def _zona():
    from .processing import ZONA_MADRID
    return ZONA_MADRID


# 5. Hilos de una historia ----------------------------------------------

def agrupar_hilos(alertas, umbral=0.4, minimo_comunes=3, maximo=15):
    """Agrupa noticias sobre el mismo hecho y ordena quién lo contó primero y cómo se propagó."""
    pals = [_palabras(a.get("titular_raw_limpio") or a.get("titular")) for a in alertas]
    padre = list(range(len(alertas)))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    invertido = defaultdict(list)
    for i, p in enumerate(pals):
        for w in p:
            invertido[w].append(i)
    candidatos = defaultdict(Counter)
    for w, idx in invertido.items():
        if 1 < len(idx) <= 60:
            for x in range(len(idx)):
                for y in range(x + 1, len(idx)):
                    candidatos[idx[x]][idx[y]] += 1
    for i, otros in candidatos.items():
        for j, comunes in otros.items():
            if comunes >= minimo_comunes and comunes / len(pals[i] | pals[j]) >= umbral:
                padre[raiz(i)] = raiz(j)

    grupos = defaultdict(list)
    for i in range(len(alertas)):
        grupos[raiz(i)].append(alertas[i])

    hilos = []
    for miembros in grupos.values():
        if len(miembros) < 2:
            continue
        con_fecha = [m for m in miembros if m.get("fecha_dt") and not m.get("fecha_estimada")]
        ordenados = sorted(con_fecha, key=lambda m: _utc(m["fecha_dt"])) + [m for m in miembros if m not in con_fecha]
        recorrido = [
            {
                "canal": m.get("canal"),
                "plataforma": m.get("plataforma"),
                "fecha": _utc(m["fecha_dt"]).isoformat() if m in con_fecha else None,
                "titular": m.get("titular_raw_limpio") or m.get("titular"),
                "enlace": m.get("enlace", ""),
                "id": m.get("id"),
            }
            for m in ordenados
        ]
        sociales = len({r["canal"] for r in recorrido if r["plataforma"] in ("TELEGRAM", "REDES")})
        hilos.append({
            "titular": recorrido[0]["titular"],
            "n": len(recorrido),
            "primero": recorrido[0],
            "sociales": sociales,
            "peligro": max(puntuar(m)["peligro"] for m in miembros),
            "recorrido": recorrido,
        })
    hilos.sort(key=lambda h: (h["peligro"], h["n"]), reverse=True)
    return hilos[:maximo]


# 6. Valoraciones y aprendizaje -----------------------------------------

def reputacion_canales(alertas, valoraciones, tope=15):
    """Ajuste de fiabilidad por canal según cuántas de sus noticias el analista marcó como falsas o confirmadas."""
    cuenta = defaultdict(lambda: [0, 0])
    for a in alertas:
        v = valoraciones.get(a["id"])
        if v == "confirmada":
            cuenta[a.get("canal")][0] += 1
        elif v == "falsa":
            cuenta[a.get("canal")][1] += 1
    return {c: max(-tope, min(tope, 5 * (ok - mal))) for c, (ok, mal) in cuenta.items() if ok != mal}


def puntuar_con_aprendizaje(item, valoraciones, reputacion):
    """Indicadores corregidos por la valoración directa del analista o por la reputación de su canal."""
    p = puntuar(item)
    p = {**p, "motivos_fiabilidad": list(p["motivos_fiabilidad"]), "motivos_peligro": list(p["motivos_peligro"])}
    v = valoraciones.get(item.get("id"))
    if v == "confirmada":
        p["fiabilidad"] = max(p["fiabilidad"], 90)
        p["motivos_fiabilidad"].append("confirmada por el analista")
    elif v == "falsa":
        p["fiabilidad"] = 5
        p["motivos_fiabilidad"].append("marcada como falsa por el analista")
    elif v == "irrelevante":
        p["peligro"] = 5
        p["motivos_peligro"].append("marcada como no relevante por el analista")
    else:
        delta = reputacion.get(item.get("canal"), 0)
        if delta:
            p["fiabilidad"] = max(5, min(95, p["fiabilidad"] + delta))
            p["motivos_fiabilidad"].append(f"historial del canal según tus valoraciones ({delta:+d})")
    return p


# 7. Alertas guardadas ---------------------------------------------------

def contar_nuevas_busqueda(alertas, busqueda, cumple):
    """Cuántas noticias coinciden con una búsqueda guardada y no estaban vistas."""
    coinciden = [a for a in alertas if cumple(a, busqueda["consulta"], busqueda["modo"])]
    vistos = set(busqueda.get("vistos", []))
    return [a for a in coinciden if a["id"] not in vistos], coinciden
