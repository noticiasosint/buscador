"""Perfiles vigilados: canales propios y menciones por nombre."""

import re

from .processing import normalizar_texto

_CONTEXTO_MEDVEDEV = (
    r"\b(russia|rusia|russian|ruso|rusa|putin|kremlin|kremlim|nuclear\w*|ucrania|ukraine|"
    r"consejo de seguridad|security council|otan|nato|trump)\b|россия|путин"
)

PERFILES = {
    "SHARIJ": {
        "etiqueta": "Anatolii Sharij",
        "descripcion": "Canal de Telegram, YouTube y menciones en prensa",
        "canales_tg": ("ASupersharij",),
        "patron": r"\banatolii?\s+shar(?:iy|ij|y)\b|\bshariy\b|\bsharij\b|asupersharij|шарий|шарій",
        "consultas": ('"Anatolii Shariy"', '"Anatoly Shariy"', "Sharij", "Шарий"),
    },
    "ARIAS": {
        "etiqueta": "Enrique Arias Gil",
        "descripcion": "Presunto desinformador ruso; vinculado a @desdemoscubot y t.me/musicarusaesp",
        "canales_tg": ("desdemoscubot", "musicarusaesp"),
        "patron": r"enrique arias gil|desdemoscubot|musicarusaesp",
        "consultas": ('"Enrique Arias Gil"', "desdemoscubot", "musicarusaesp"),
    },
    "AGUILAR": {
        "etiqueta": "Juan Antonio Aguilar",
        "descripcion": "Posible director del Instituto Español de Geopolítica",
        "canales_tg": (),
        "patron": r"juan antonio aguilar|instituto espanol de geopolitica",
        "consultas": ('"Juan Antonio Aguilar" geopolítica', '"Instituto Español de Geopolítica"'),
    },
    "DORAO": {
        "etiqueta": "Eugenio Dorao",
        "descripcion": "Fundador de la Plataforma Europea de Amigos de Rusia (PEAR)",
        "canales_tg": (),
        "patron": r"eugenio dorao|plataforma europea de amigos de rusia",
        "consultas": ('"Eugenio Dorao"', '"Plataforma Europea de Amigos de Rusia"'),
    },
    "PELICANO": {
        "etiqueta": "PELICANO (@rusa_alena)",
        "descripcion": "Usuario de Telegram vinculado a t.me/rusa_alena",
        "canales_tg": ("rusa_alena",),
        "patron": r"rusa_alena|rusa alena",
        "consultas": ('"rusa_alena"',),
    },
    "MEDVEDEV": {
        "etiqueta": "Dmitri Medvedev (@MedvedevRussiaE)",
        "descripcion": "Cuenta de X de Dmitri Medvedev; se sigue su canal oficial de Telegram y la prensa",
        "canales_tg": ("medvedev_telegram",),
        "patron": r"dmitri[yj]? medvedev|dmitry medvedev|dimitri medvedev|medvedevrussiae|дмитри[ия] медведев",
        "contexto": r"medvedev|медведев",
        "consultas": ('"Dmitri Medvedev"', '"Dmitry Medvedev"', "MedvedevRussiaE", '"Дмитрий Медведев"'),
    },
}

CANALES_VIGILADOS = {
    canal.lower(): clave
    for clave, datos in PERFILES.items()
    for canal in datos["canales_tg"]
}

CANALES_TG_VIGILADOS = tuple(
    canal for datos in PERFILES.values() for canal in datos["canales_tg"]
)

_PATRONES = {
    clave: re.compile(datos["patron"])
    for clave, datos in PERFILES.items()
}
_CONTEXTOS = {
    clave: (re.compile(datos["contexto"]), re.compile(_CONTEXTO_MEDVEDEV))
    for clave, datos in PERFILES.items()
    if "contexto" in datos
}


_TENIS = re.compile(r"daniil|danil|tenis|tennis|\batp\b|roland garros|wimbledon|open de australia")


def perfil_de_canal(canal):
    return CANALES_VIGILADOS.get(str(canal or "").lstrip("@").strip().lower())


def perfiles_en(texto, canal=""):
    """Devuelve las claves de perfiles vigilados que aparecen en el texto o el canal."""
    texto_norm = normalizar_texto(f"{canal} {texto}")
    encontrados = []
    propio = perfil_de_canal(canal)
    if propio:
        encontrados.append(propio)
    for clave, patron in _PATRONES.items():
        if clave in encontrados:
            continue
        if patron.search(texto_norm):
            encontrados.append(clave)
            continue
        contexto = _CONTEXTOS.get(clave)
        if contexto and not _TENIS.search(texto_norm) and contexto[0].search(texto_norm) and contexto[1].search(texto_norm):
            encontrados.append(clave)
    return encontrados


def feeds_perfiles():
    """Búsquedas de Google News por perfil (sin límite temático)."""
    from urllib.parse import quote_plus

    feeds = []
    for clave, datos in PERFILES.items():
        consulta = f"({' OR '.join(datos['consultas'])}) when:180d"
        for hl, gl, ceid in (("es", "ES", "ES:es"), ("en-US", "US", "US:en"), ("ru", "RU", "RU:ru")):
            url = (
                "https://news.google.com/rss/search?q="
                f"{quote_plus(consulta)}&hl={hl}&gl={gl}&ceid={ceid}"
            )
            feeds.append((url, f"Perfil {datos['etiqueta']} [{hl}]"))
    return feeds
