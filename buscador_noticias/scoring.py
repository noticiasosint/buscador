"""Indicadores heurísticos de fiabilidad y peligro. Son estimaciones, no verificaciones."""
from datetime import datetime, timezone

from .config import PATRON_SABOTAJE_MULTI, PATRON_TERRORISMO_MULTI
from .processing import normalizar_texto

AVISO = (
    "Estimación automática a partir de la fuente, la cobertura y el texto. "
    "No verifica los hechos: contrástalo antes de actuar."
)

_BASE_PLATAFORMA = {"PRENSA": 55, "INVESTIGACIÓN": 50, "TELEGRAM": 30, "REDES": 30}
_CANALES_REPUTADOS = (
    "reuters", "associated press", "ap news", "afp", "efe", "europa press", "bbc",
    "financial times", "the guardian", "el pais", "france 24", "dw", "politico",
    "bellingcat", "nato", "otan", "europol", "interpol", "ministerio", "guardia civil",
)
_BASE_PELIGRO = {
    "DETENCION": 45, "CRIMENES": 45, "DRONES": 45, "AGENCIAS": 40, "ESPANA": 40,
    "SANCIONES": 35, "CHINA": 35, "EMPRESA": 35, "CRIPTO": 30, "GLOBAL": 30,
    "TELEGRAM": 30, "REDES": 30,
}
_SENSACIONALISTA = ("urgente", "bombazo", "no te lo vas a creer", "increible", "shock", "exclusiva")


def _limitar(valor, minimo=5, maximo=95):
    return int(max(minimo, min(maximo, round(valor))))


def _horas(fecha):
    if not fecha:
        return None
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - fecha.astimezone(timezone.utc)).total_seconds() / 3600)


def puntuar(item):
    """Devuelve {'fiabilidad': 0-100, 'peligro': 0-100, 'motivos_fiabilidad': [...], 'motivos_peligro': [...]}."""
    titular = str(item.get("titular_raw_limpio") or item.get("titular") or "")
    texto = normalizar_texto(f"{titular} {item.get('cuerpo', '')}")
    plataforma = item.get("plataforma", "PRENSA")
    canal = normalizar_texto(str(item.get("canal", "")))

    fiab = _BASE_PLATAFORMA.get(plataforma, 45)
    m_f = [f"Tipo de fuente: {plataforma.lower()}"]
    if any(c in canal for c in _CANALES_REPUTADOS):
        fiab += 20
        m_f.append("medio u organismo de referencia (+20)")
    n = int(item.get("num_fuentes", 1) or 1)
    if n > 1:
        extra = min(18, (n - 1) * 6)
        fiab += extra
        m_f.append(f"{n} fuentes distintas lo recogen (+{extra})")
    else:
        m_f.append("una sola fuente, sin corroborar")
    sociales = int(item.get("num_canales_sociales", 0) or 0)
    if sociales > 1:
        extra = min(9, (sociales - 1) * 3)
        fiab += extra
        m_f.append(f"{sociales} canales de Telegram/redes coinciden (+{extra})")
    if item.get("fecha_estimada") or not item.get("fecha_dt"):
        fiab -= 8
        m_f.append("fecha estimada (-8)")
    if titular.isupper() and len(titular) > 15 or titular.count("!") >= 2 or any(
        p in normalizar_texto(titular) for p in _SENSACIONALISTA
    ):
        fiab -= 8
        m_f.append("tono sensacionalista (-8)")

    peli = _BASE_PELIGRO.get(item.get("categoria", "GLOBAL"), 30)
    m_p = [f"Categoría: {item.get('categoria', 'GLOBAL')}"]
    if PATRON_TERRORISMO_MULTI.search(texto):
        peli += 25
        m_p.append("terrorismo o atentado (+25)")
    if PATRON_SABOTAJE_MULTI.search(texto):
        peli += 20
        m_p.append("sabotaje (+20)")
    if item.get("impacto_potencial"):
        peli += 15
        m_p.append("indicio de impacto amplio (+15)")
    if sociales > 1:
        extra = min(30, (sociales - 1) * 10)
        peli += extra
        m_p.append(f"difusión: {sociales} canales de Telegram/redes lo replican (+{extra})")
    ents = len(item.get("etiquetas_ner") or [])
    if ents:
        extra = min(12, ents * 4)
        peli += extra
        m_p.append(f"{ents} actores o vectores detectados (+{extra})")
    h = _horas(item.get("fecha_dt"))
    if h is not None and h <= 6:
        peli += 8
        m_p.append("muy reciente (+8)")
    elif h is not None and h <= 24:
        peli += 4
        m_p.append("de las últimas 24 h (+4)")

    return {
        "fiabilidad": _limitar(fiab),
        "peligro": _limitar(peli, 5, 98),
        "motivos_fiabilidad": m_f,
        "motivos_peligro": m_p,
    }
