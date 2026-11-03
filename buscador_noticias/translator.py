import os
import re
from functools import lru_cache

IDIOMAS_TRADUCCION = {
    "Español": "es",
    "Inglés": "en",
    "Ruso": "ru",
    "Ucraniano": "uk",
    "Árabe": "ar",
    "Chino simplificado": "zh-CN",
    "Chino tradicional": "zh-TW",
    "Francés": "fr",
    "Alemán": "de",
    "Italiano": "it",
    "Portugués": "pt",
    "Polaco": "pl",
    "Checo": "cs",
    "Eslovaco": "sk",
    "Rumano": "ro",
    "Búlgaro": "bg",
    "Lituano": "lt",
    "Letón": "lv",
    "Estonio": "et",
    "Finés": "fi",
    "Sueco": "sv",
    "Noruego": "no",
    "Danés": "da",
    "Neerlandés": "nl",
    "Turco": "tr",
    "Hebreo": "he",
    "Japonés": "ja",
    "Coreano": "ko",
    "Hindi": "hi",
    "Griego": "el",
    "Húngaro": "hu",
    "Serbio": "sr",
    "Croata": "hr",
    "Indonesio": "id",
    "Vietnamita": "vi",
    "Tailandés": "th",
    "Persa": "fa",
    "Bengalí": "bn",
    "Malayo": "ms",
    "Suajili": "sw",
}

IDIOMAS_ORIGEN = IDIOMAS_TRADUCCION

_CODIGOS_MYMEMORY = {
    "es": "es-ES",
    "en": "en-GB",
    "ru": "ru-RU",
    "uk": "uk-UA",
    "ar": "ar-SA",
    "fr": "fr-FR",
    "it": "it-IT",
    "zh-CN": "zh-CN",
    "zh-TW": "zh-TW",
    "zh": "zh-CN",
    "pl": "pl-PL",
    "de": "de-DE",
    "pt": "pt-PT",
    "cs": "cs-CZ",
    "sk": "sk-SK",
    "ro": "ro-RO",
    "bg": "bg-BG",
    "lt": "lt-LT",
    "lv": "lv-LV",
    "et": "et-EE",
    "fi": "fi-FI",
    "sv": "sv-SE",
    "no": "nb-NO",
    "da": "da-DK",
    "nl": "nl-NL",
    "tr": "tr-TR",
    "he": "he-IL",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "hi": "hi-IN",
    "el": "el-GR",
    "hu": "hu-HU",
    "sr": "sr-Cyrl-RS",
    "hr": "hr-HR",
    "id": "id-ID",
    "vi": "vi-VN",
    "th": "th-TH",
    "fa": "fa-IR",
    "bn": "bn-IN",
    "ms": "ms-MY",
    "sw": "sw-KE",
}


def detectar_idioma(texto):
    """Heurística por escritura; devuelve un código de idioma o None si ya parece español."""
    if re.search(r"[\u3040-\u30ff]", texto):
        return "ja"
    if re.search(r"[\uac00-\ud7af]", texto):
        return "ko"
    if re.search(r"[\u4e00-\u9fff]", texto):
        return "zh-CN"
    if re.search(r"[\u0600-\u06FF]", texto):
        return "ar"
    if re.search(r"[\u0590-\u05ff]", texto):
        return "he"
    if re.search(r"[\u0900-\u097f]", texto):
        return "hi"
    if re.search(r"[\u0e00-\u0e7f]", texto):
        return "th"
    if re.search(r"[\u0370-\u03ff]", texto):
        return "el"
    if re.search(r"[\u0400-\u04FF]", texto):
        if re.search(r"[іїєґІЇЄҐ]", texto):
            return "uk"
        if re.search(r"[ђјљњћџЂЈЉЊЋЏ]", texto):
            return "sr"
        return "ru"
    if re.search(r"[ąćęłńśźżĄĆĘŁŃŚŹŻ]", texto):
        return "pl"
    palabras = set(re.findall(r"[^\W\d_]+", texto.lower()))
    exclusivas_fr = palabras & (_PALABRAS_FR - _PALABRAS_ES)
    exclusivas_es = palabras & (_PALABRAS_ES - _PALABRAS_FR)
    if len(exclusivas_fr) >= 2 and len(exclusivas_fr) > len(exclusivas_es):
        return "fr"
    if len(palabras & _PALABRAS_PL) >= 2:
        return "pl"
    if len(palabras & _PALABRAS_ES) >= 2 or re.search(r"[¿¡ñ]", texto):
        return None
    if re.search(r"[äöüß]", texto.lower()) and len(palabras & _PALABRAS_DE) >= 1:
        return "de"
    return "en"


def traduccion_si_extranjero(texto, maximo=220):
    """Traducción al español si el texto no está en español ni inglés; None si no hace falta o falla."""
    texto = " ".join(str(texto or "").split())[:maximo]
    if not texto or detectar_idioma(texto) in (None, "en"):
        return None
    try:
        traducido, origen = traducir_a_espanol(texto)
    except Exception:
        return None
    traducido = " ".join(str(traducido or "").split())
    return traducido if origen and traducido and traducido != texto else None


_PALABRAS_ES = {"de", "la", "el", "en", "los", "las", "que", "por", "con", "para", "una", "del", "se", "al", "es", "su", "sus", "ante", "hola", "mundo"}
_PALABRAS_DE = {"und", "der", "die", "das", "nicht", "mit", "von", "für", "ist", "auf"}
_PALABRAS_FR = {"à", "après", "avec", "dans", "des", "du", "elle", "est", "et", "il", "la", "le", "les", "mais", "par", "pour", "sur", "un", "une", "son", "ses", "vingt", "hommage", "assassinat"}
_PALABRAS_PL = {"jest", "nie", "się", "oraz", "przez", "który", "która", "które", "będzie", "będą", "rząd", "polski", "polska", "został", "została", "są"}
_VERSION_CACHE_TRADUCCION = 3


def _trocear(texto, limite=450):
    trozos, actual = [], ""
    for frase in re.split(r"(?<=[.!?…。])\s+", texto):
        while len(frase) > limite:
            trozos.append(frase[:limite])
            frase = frase[limite:]
        if len(actual) + len(frase) + 1 > limite and actual:
            trozos.append(actual)
            actual = frase
        else:
            actual = f"{actual} {frase}".strip()
    if actual:
        trozos.append(actual)
    return trozos


def _traducir_trozo(MyMemoryTranslator, trozo, origen, email):
    """Prueba el par directo, el texto sin comillas y, por último, el pivote por inglés."""
    def traducir(texto, desde, hacia):
        try:
            salida = MyMemoryTranslator(source=desde, target=hacia, email=email).translate(texto)
        except Exception:
            return None
        salida = str(salida or "").strip()
        return salida or None

    desde = _CODIGOS_MYMEMORY.get(origen, origen)
    limpio = re.sub(r"[«»“”„\"']", " ", trozo)
    limpio = " ".join(limpio.split())
    for candidato in (trozo, limpio):
        resultado = traducir(candidato, desde, "es-ES")
        if resultado:
            return resultado
    if origen != "en":
        en = traducir(limpio, desde, "en-GB")
        if en:
            return traducir(en, "en-GB", "es-ES")
    return None


def _traducir_google(texto):
    """Endpoint web gratuito de Google (sin clave). Devuelve (texto, idioma_detectado)."""
    import requests

    ultimo_error = None
    datos = None
    intentos = (
        ("https://translate.googleapis.com/translate_a/single", "gtx"),
        ("https://translate.google.com/translate_a/single", "gtx"),
        ("https://clients5.google.com/translate_a/t", "dict-chrome-ex"),
    )
    for url, cliente in intentos:
        try:
            respuesta = requests.get(
                url,
                params={"client": cliente, "sl": "auto", "tl": "es", "dt": "t", "q": texto},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=8,
            )
            respuesta.raise_for_status()
            datos = respuesta.json()
            if isinstance(datos, list) and datos and isinstance(datos[0], list):
                break
            datos = None
        except Exception as exc:
            ultimo_error = exc
    if datos is None:
        raise RuntimeError(f"Google no disponible: {ultimo_error}")
    traducido = "".join(segmento[0] for segmento in datos[0] if segmento and segmento[0])
    if not traducido.strip():
        raise RuntimeError("Respuesta vacía")
    return traducido.strip(), datos[2]


@lru_cache(maxsize=2048)
def _traducir_a_espanol_cache(_version, texto):
    """Traduce una noticia a español. Devuelve (texto, idioma_detectado)."""
    texto = " ".join(str(texto or "").split())
    if not texto:
        return "", None

    origen_local = detectar_idioma(texto)
    try:
        traducido, origen = _traducir_google(texto[:1500])
        if origen == "es":
            if origen_local is None:
                return texto, None
            if traducido.strip().casefold() != texto.casefold():
                return traducido, origen_local
            origen = origen_local
        if traducido.strip().casefold() != texto.casefold():
            return traducido, origen_local or origen
        if origen_local is None:
            return traducido, origen
        origen = origen_local
    except Exception:
        origen = origen_local

    if origen is None:
        return texto, None

    try:
        from deep_translator import MyMemoryTranslator
    except ImportError as exc:
        raise RuntimeError(
            "Falta la dependencia deep-translator. Instálala con: pip install -r requirements.txt"
        ) from exc

    email = os.environ.get("MYMEMORY_EMAIL") or None
    partes = [_traducir_trozo(MyMemoryTranslator, trozo, origen, email) for trozo in _trocear(texto)]
    if any(p is None for p in partes):
        raise RuntimeError(
            "No se pudo traducir la noticia. Puede que el servicio gratuito esté saturado "
            "o que se haya agotado su límite diario (define MYMEMORY_EMAIL para ampliarlo)."
        )

    traducido = " ".join(partes).strip()
    if "MYMEMORY WARNING" in traducido.upper():
        raise RuntimeError(
            "Se agotó el límite diario gratuito de traducción. Inténtalo mañana "
            "o define MYMEMORY_EMAIL para ampliarlo."
        )
    return traducido, origen


def traducir_a_espanol(texto):
    return _traducir_a_espanol_cache(_VERSION_CACHE_TRADUCCION, texto)


traducir_a_espanol.cache_clear = _traducir_a_espanol_cache.cache_clear
traducir_a_espanol.cache_info = _traducir_a_espanol_cache.cache_info


def traducir_termino(termino, idiomas, codigo_origen="es"):
    termino = str(termino).strip()
    if not termino:
        raise ValueError("Escribe una palabra o expresión antes de traducirla.")
    if not idiomas:
        raise ValueError("Selecciona al menos un idioma de destino.")
    if codigo_origen not in IDIOMAS_ORIGEN.values():
        raise ValueError("Selecciona un idioma de origen admitido.")

    try:
        from deep_translator import MyMemoryTranslator
    except ImportError as exc:
        raise RuntimeError(
            "Falta la dependencia deep-translator. Instálala con: pip install -r requirements.txt"
        ) from exc

    traducciones = []
    for idioma in idiomas:
        codigo = IDIOMAS_TRADUCCION.get(idioma)
        if not codigo:
            raise ValueError(f"Idioma de traducción no admitido: {idioma}")
        if codigo == codigo_origen:
            raise ValueError(
                f"El idioma de origen ya es {idioma}; elige otro idioma de destino."
            )

        try:
            texto = MyMemoryTranslator(
                source=_CODIGOS_MYMEMORY.get(codigo_origen, codigo_origen),
                target=_CODIGOS_MYMEMORY.get(codigo, codigo),
            ).translate(termino)
        except Exception as exc:
            raise RuntimeError(
                f"No se pudo traducir a {idioma}: {exc}. Comprueba la conexión a Internet "
                "o inténtalo más tarde (límite gratuito diario)."
            ) from exc

        texto = str(texto or "").strip()
        if not texto:
            raise RuntimeError(f"El traductor no devolvió texto para {idioma}.")

        traducciones.append({"idioma": idioma, "codigo": codigo, "texto": texto})

    return traducciones
