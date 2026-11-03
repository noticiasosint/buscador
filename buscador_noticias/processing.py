import hashlib
import html as html_module
import math
import re
import unicodedata
from datetime import datetime, timezone
from functools import lru_cache
from urllib.parse import urlparse, urlunparse
from zoneinfo import ZoneInfo

from .config import (
    EMPRESAS_ESTRATEGICAS_ESP, PATRON_AGENCIAS, PATRON_CHINA, RAICES_CHINO,
    PATRON_RUSIA_UCRANIA, PATRON_PAISES_AJENOS, PATRON_DETENCION_MULTI,
    PATRON_CRIMENES_MULTI, PATRON_DRONES_MULTI, PATRON_DESINFORMACION_MULTI,
    PATRON_SABOTAJE_MULTI, PATRON_TERRORISMO_MULTI, PATRON_IMPACTO_MULTILINGUE,
    SINONIMOS_MULTILINGUES
)

ZONA_MADRID = ZoneInfo("Europe/Madrid")
PATRON_INJERENCIA = re.compile(
    r"\b(injerencia\w*|desinformaci\w*|operaci\w* de influenci\w*|"
    r"election interference|influence operation|foreign influence|"
    r"disinformation|fimi|doppelganger|spamouflage|"
    r"вмешательств\w*|дезинформац\w*|втручанн\w*|"
    r"تضليل|تدخل أجنبي)\b",
    re.IGNORECASE,
)
PATRON_OTAN = re.compile(r"\b(otan|nato|north atlantic treaty organization)\b", re.IGNORECASE)
PATRON_ASESINATO = re.compile(
    r"\b(asesinato selectivo|intento de asesinato|asesinato|envenenamiento|"
    r"assassination|attempted assassination|poisoning|targeted killing|"
    r"убийств\w*|покушени\w*|отравлени\w*|"
    r"вбивств\w*|замах\w*|отруєн\w*|"
    r"اغتيال|تسميم)\b",
    re.IGNORECASE,
)
PATRON_ESPANA_FUERTE = re.compile(
    r"\b(espa[nñ]a|spain|espagne|spanien|spagna|hiszpani\w*|іспані\w*|"
    r"испани\w*|西班牙|スペイン|스페인|إسبانيا|اسبانيا|ספרד|स्पेन|"
    r"ισπανια|ispanij\w*|tây ban nha|"
    r"guardia civil|audiencia nacional|cni|ccn-cert|incibe|dsn|moncloa|"
    r"margarita robles|albares|pedro sanchez|felipe vi|congreso de los diputados|"
    r"cortes generales|mossos|ertzaintza|armada espanola|ejercito de tierra|"
    r"estado mayor de la defensa|guardia real)\b",
    re.IGNORECASE,
)
PATRON_ESPANA_DEBIL = re.compile(
    r"\b(madrid|barcelona|cartagena|rota|torrejon|mallorca|canarias|ceuta|melilla|"
    r"marbella|malaga|alicante|valencia|sevilla|torrevieja|benidorm|tenerife|"
    r"bilbao|zaragoza|costa del sol|costa blanca|moron)\b",
    re.IGNORECASE,
)
PATRON_PAIS_EXTRANJERO_TITULAR = re.compile(
    r"\b(dinamarca|danish|danes\w*|denmark|rumania|roman\w*|romania|"
    r"polonia|polish|poland|alemania|german\w*|germany|francia|french|france|"
    r"italia|italian|italy|moldavia|moldova|georgia|georgian|"
    r"argentina|argentine|argentinian|argentino\w*|buenos aires|"
    r"eeuu|estados unidos|united states|usa|american|estadounidense\w*)\b",
    re.IGNORECASE,
)
PATRON_HABLANTES_HISPANOS = re.compile(
    r"\b(spanish(?:[-\s]+and[-\s]+portuguese)?[-\s]+speaking|"
    r"spanish[-\s]+(?:language|edition|version|translation)|in\s+spanish|"
    r"lengua\s+espa[nñ]ola|idioma\s+espa[nñ]ol|en\s+espa[nñ]ol|"
    r"portuguese[-\s]+speaking|"
    r"paises?\s+de\s+habla\s+hispana|habla\s+hispana|"
    r"paises?\s+hispanohablantes?|hispanohablantes?)\b",
    re.IGNORECASE,
)

def obtener_fecha_madrid_str(dt=None):
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZONA_MADRID).strftime("%d/%m/%Y %H:%M:%S")

def limpiar_html_texto(texto):
    if not texto: return ""
    t = re.sub(r'<[^<]+?>', ' ', str(texto))
    t = html_module.unescape(t)
    t = re.sub(r'&[a-zA-Z0-9#]+;', ' ', t)
    t = re.sub(r'(?i)(suscr[ií]bete a nuestro bolet[ií]n|lee m[aá]s en|copyright|todos los derechos reservados|pincha aqu[ií]|sigue leyendo).*', '', t)
    return re.sub(r'\s+', ' ', t).strip()

def normalizar_texto(texto):
    if not texto: return ""
    return "".join([c for c in unicodedata.normalize('NFKD', str(texto)) if not unicodedata.combining(c)]).lower()

def desparasitar_nombres_medios(texto):
    t = str(texto)
    patrones_medios = [
        r'la\s*nueva\s*espa[nñ]a', r'\b(?:www\.)?moncloa\.com\b',
        r'el\s*espa[nñ]ol', r'elespanol', r'marketscreener\s*espa[nñ]a', r'libertad\s*digital', 
        r'el\s*confidencial', r'el\s*periodico', r'el\s*pais', r'el\s*mundo', r'la\s*razon', 
        r'the\s*objective', r'vozpopuli', r'europa\s*press', r'agencia\s*efe', r'rtve'
    ]
    for p in patrones_medios:
        t = re.sub(p, ' ', t, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', t).strip()

def limpiar_firma_medio(texto):
    return re.sub(r'\s*[-–|·]\s*[^-–|·]{2,60}$', '', str(texto)).strip() if texto else ""

def limpiar_url(url):
    try:
        p = urlparse(url)
        return urlunparse((p.scheme, p.netloc, p.path, '', '', ''))
    except Exception: return url

def es_url_segura(url):
    try:
        p = urlparse(str(url).strip())
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False

def url_sanitizada(url):
    return html_module.escape(str(url).strip()) if es_url_segura(url) else "about:blank"

def id_determinista(cadena):
    return hashlib.md5(str(cadena).encode('utf-8')).hexdigest()[:16]

def cumple_ventana_temporal(fecha_dt, horas):
    if not fecha_dt: return False
    if fecha_dt.tzinfo is None: fecha_dt = fecha_dt.replace(tzinfo=timezone.utc)
    dif_segundos = (datetime.now(timezone.utc) - fecha_dt.astimezone(timezone.utc)).total_seconds()
    return 0 <= dif_segundos <= (horas * 3600)

def clave_actualidad_cobertura(item):
    fecha = item.get("fecha_dt")
    if fecha is None:
        return (-10**9, item.get("num_fuentes", 1), 0)
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    fecha_utc = fecha.astimezone(timezone.utc)
    horas_transcurridas = max(0, (datetime.now(timezone.utc) - fecha_utc).total_seconds()) / 3600
    banda_actualidad = -int(horas_transcurridas // 6)
    return (banda_actualidad, item.get("num_fuentes", 1), fecha_utc.timestamp())

def es_publicidad_o_spam(texto):
    t = normalizar_texto(texto)
    
    # Inmunidad directa para Vor v Zakone y tramas criminales del Kremlin
    if any(k in t for k in ["yuzuk", "vor v zakone", "вор в законе", "ladron en ley", "ladrones en ley", "thief in law", "thieves in law"]):
        return False

    # Bloqueo de Marruecos/Oriente Medio sin relación con el conflicto
    if PATRON_PAISES_AJENOS.search(t):
        if not re.search(r'\b(rusia|ruso|moscu|kremlin|putin|ucrania|shahed|geran|drones a rusia|misiles a rusia|china|pekin|روسيا|بوتين)\b', t):
            return True

    spam = [
        "horario de invierno", "master profesional", "oferta de empleo", "horoscopo", "loteria",
        "quiniela", "liga de futbol", "champions league", "apuestas", "receta de cocina", "supermercado", "rebajas",
        "estafas en linea", "fraude bancario", "trashumancia", "comprar pellets", "estafa al comprar",
        "pellets", "salvador illa", "disturbios en barcelona", "liga endesa", "pensionistas se manifiestan",
        "arancha gonzalez laya", "huelga de transportes", "ayuso", "feijoo", "sanchez", "inmobiliario", "hipotecas", 
        "demanda de nuevas viviendas", "accidente de coche", "persecucion policial",
        "incendio forestal", "violencia de genero", "irs planea", "divulgacion fiscal", "meidas"
    ]
    if any(s in t for s in spam):
        if not re.search(r'\b(ciberataque|sabotaje|espionaje|apt28|apt29|noname057|garantex|fsb|gru|svr|tether|shadow fleet|flota fantasma|yuzuk|vor v zakone|mafia rusa|ladrones en ley)\b', t):
            return True

    return False

def es_relevante_en_origen(texto, canal):
    if not texto: return False
    texto_normalizado = normalizar_texto(texto)
    es_canal_espana = normalizar_texto(canal).startswith("espana")
    texto_sin_referencia_linguistica = PATRON_HABLANTES_HISPANOS.sub(
        " ", texto_normalizado
    )
    hay_referencia_espana = bool(
        PATRON_ESPANA_FUERTE.search(texto_sin_referencia_linguistica)
        or PATRON_ESPANA_DEBIL.search(texto_sin_referencia_linguistica)
    )
    if es_canal_espana and not hay_referencia_espana:
        return False
    if es_publicidad_o_spam(texto): return False
    return True


def es_tematico_redes(texto):
    texto_normalizado = normalizar_texto(texto)
    if PATRON_AGENCIAS.search(texto_normalizado) and re.search(
        r"\b(alerta|warning|advisory|investig\w*|investigation|informe|report|"
        r"publish\w*|publica\w*|operation|operacion|espion\w*|cyber\w*|"
        r"sabotage|sabotaj\w*|amenaza\w*|threat\w*)\b",
        texto_normalizado,
    ):
        return True
    if re.search(
        r"\b(sharij|shariy|anatolii|anatoly|vor v zakone|ladron(?:es)? en ley|"
        r"thieves? in law|mafia rusa|yuzuk)\b",
        texto_normalizado,
    ):
        return True
    eje = bool(
        PATRON_RUSIA_UCRANIA.search(texto_normalizado)
        or PATRON_CHINA.search(texto_normalizado)
        or PATRON_OTAN.search(texto_normalizado)
    )
    tema = bool(
        PATRON_SABOTAJE_MULTI.search(texto_normalizado)
        or PATRON_DESINFORMACION_MULTI.search(texto_normalizado)
        or PATRON_DRONES_MULTI.search(texto_normalizado)
        or PATRON_CRIMENES_MULTI.search(texto_normalizado)
        or PATRON_TERRORISMO_MULTI.search(texto_normalizado)
        or PATRON_DETENCION_MULTI.search(texto_normalizado)
        or PATRON_ASESINATO.search(texto_normalizado)
        or re.search(
            r"\b(espionaj\w*|espionage|spy|spies|ciberataque\w*|cyberattack|"
            r"cyber espionage|sancion\w*|sanction\w*|flota fantasma|shadow fleet)\b",
            texto_normalizado,
        )
    )
    return eje and tema


MODOS_BUSQUEDA = {
    "Exacto": "Palabras completas y todas presentes, sin sinónimos.",
    "Equilibrado": "Todas las palabras, con plurales y sinónimos conocidos.",
    "Amplio": "Basta con la mayoría de las palabras; admite derivados y sinónimos.",
}
MODO_BUSQUEDA_DEFECTO = "Equilibrado"

_PALABRAS_VACIAS = {
    "de", "del", "la", "las", "el", "los", "en", "y", "a", "un", "una", "por",
    "con", "para", "al", "the", "of", "and", "in", "to", "on", "for",
}
_ESCRITURA_SIN_ESPACIOS = re.compile(r'[\u0600-\u06FF\u3040-\u30ff\u4e00-\u9fff]')
_CIRILICO = re.compile(r'[\u0400-\u04FF]')
_NEGACION = re.compile(r'(?:NOT\s+|(?:^|(?<=\s))-)(?:"([^"]+)"|(\w+))', flags=re.IGNORECASE)
_REFERENCIA_ESPANA = re.compile(
    r"\b(espana|espanol\w*|spain|spanish|madrid|barcelona|valencia|"
    r"marbella|alicante|cartagena|rota|torrejon|guardia civil|"
    r"policia nacional|national police|audiencia nacional|cni|incibe|"
    r"ccn-cert|dsn|ministerio de defensa|margarita robles)\b",
    re.IGNORECASE,
)


def menciona_espana(texto):
    return bool(_REFERENCIA_ESPANA.search(normalizar_texto(texto)))


def aplicar_categoria_personalizada(categoria_base, coincidencia, texto):
    if not coincidencia:
        return categoria_base
    categoria_personalizada = coincidencia["categoria"]
    if categoria_personalizada == "ESPANA" and not menciona_espana(texto):
        return categoria_base
    return categoria_personalizada


def _modo_valido(modo):
    return modo if modo in MODOS_BUSQUEDA else MODO_BUSQUEDA_DEFECTO


def expandir_terminos_rapido(palabra, modo=MODO_BUSQUEDA_DEFECTO):
    modo = _modo_valido(modo)
    p = normalizar_texto(palabra).strip()
    if not p: return []
    res = {p}
    if modo == "Exacto":
        return list(res)
    for clave, sinonimos in SINONIMOS_MULTILINGUES.items():
        normalizados = {normalizar_texto(x) for x in sinonimos}
        if p == clave or p in normalizados or (
            modo == "Amplio" and len(p) >= 5 and len(clave) >= 5 and p.startswith(clave[:5])
        ):
            res.update(normalizados)
    return list(res)


@lru_cache(maxsize=4096)
def _patron_termino(termino, modo):
    t = re.escape(termino)
    if _ESCRITURA_SIN_ESPACIOS.search(termino):
        return re.compile(t)
    if _CIRILICO.search(termino) and len(termino) >= 5:
        return re.compile(rf'(?<!\w){re.escape(termino[:-1])}')
    if modo == "Exacto":
        return re.compile(rf'(?<!\w){t}(?!\w)')
    if modo == "Amplio" and len(termino) >= 5:
        return re.compile(rf'(?<!\w){t}')
    if len(termino) >= 4:
        return re.compile(rf'(?<!\w){t}(?:s|es)?(?!\w)')
    return re.compile(rf'(?<!\w){t}(?!\w)')


def coincide_palabra_optimizada(token, corpus, modo=MODO_BUSQUEDA_DEFECTO):
    if not token: return True
    modo = _modo_valido(modo)
    return any(
        _patron_termino(v, modo).search(corpus)
        for v in expandir_terminos_rapido(token, modo)
    )


def _frase_en_corpus(frase, corpus):
    frase = normalizar_texto(frase).strip()
    if not frase: return True
    if _ESCRITURA_SIN_ESPACIOS.search(frase):
        return frase in corpus
    return re.search(rf'(?<!\w){re.escape(frase)}(?!\w)', corpus) is not None


def _analizar_rama(rama):
    rama = rama.strip("()")
    negativos = [frase or palabra for frase, palabra in _NEGACION.findall(rama)]
    positiva = _NEGACION.sub(' ', rama)
    frases = re.findall(r'"([^"]+)"', positiva)
    sueltas = re.sub(r'"[^"]+"', ' ', positiva)
    palabras = [
        w.strip() for w in re.split(r'\bAND\b|\s+', sueltas, flags=re.IGNORECASE)
        if w.strip() and normalizar_texto(w) not in _PALABRAS_VACIAS
    ]
    return negativos, frases, palabras


def _ramas_consulta(query_str):
    return [b.strip() for b in re.split(r'\bOR\b', str(query_str), flags=re.IGNORECASE) if b.strip()]


def cumple_busqueda_booleana_avanzada(item, query_str, modo=MODO_BUSQUEDA_DEFECTO):
    if not query_str or not str(query_str).strip():
        return True
    modo = _modo_valido(modo)

    corpus = normalizar_texto(f"{item.get('titular', '')} {item.get('cuerpo', '')}")
    ramas = _ramas_consulta(query_str)
    if not ramas: return True

    for rama in ramas:
        negativos, frases, palabras = _analizar_rama(rama)
        if any(coincide_palabra_optimizada(n, corpus, modo) for n in negativos):
            continue
        if any(not _frase_en_corpus(f, corpus) for f in frases):
            continue
        if not palabras:
            return True
        aciertos = sum(coincide_palabra_optimizada(w, corpus, modo) for w in palabras)
        necesarios = math.ceil(len(palabras) * 0.6) if modo == "Amplio" else len(palabras)
        if aciertos >= necesarios:
            return True
    return False


def resaltar_coincidencias(texto_original, query_str, modo=MODO_BUSQUEDA_DEFECTO):
    texto = str(texto_original or "")
    if not query_str or not texto:
        return html_module.escape(texto)
    modo = _modo_valido(modo)

    patrones = []
    for rama in _ramas_consulta(query_str):
        _, frases, palabras = _analizar_rama(rama)
        for frase in frases:
            frase = normalizar_texto(frase).strip()
            if len(frase) >= 3:
                patrones.append(re.compile(rf'(?<!\w){re.escape(frase)}(?!\w)'))
        for palabra in palabras:
            for variante in expandir_terminos_rapido(palabra, modo):
                if len(variante) >= 3:
                    patrones.append(_patron_termino(variante, modo))

    normalizado = normalizar_texto(texto)
    if not patrones or len(normalizado) != len(texto):
        return html_module.escape(texto)

    rangos = sorted(
        (m.start(), m.end())
        for patron in patrones
        for m in patron.finditer(normalizado)
        if m.end() > m.start()
    )
    fusionados = []
    for inicio, fin in rangos:
        if fusionados and inicio <= fusionados[-1][1]:
            fusionados[-1][1] = max(fusionados[-1][1], fin)
        else:
            fusionados.append([inicio, fin])

    salida, cursor = [], 0
    for inicio, fin in fusionados:
        salida.append(html_module.escape(texto[cursor:inicio]))
        salida.append(f'<mark class="osint-hit">{html_module.escape(texto[inicio:fin])}</mark>')
        cursor = fin
    salida.append(html_module.escape(texto[cursor:]))
    return "".join(salida)

def extraer_entidades_clave(texto_completo):
    t_norm = normalizar_texto(texto_completo)
    etiquetas = []
    actores = {"CIA": r'\bcia\b', "CNI": r'\bcni\b', "MI5 / MI6": r'\b(mi5|mi6|mccallum|gchq)\b', "GRU": r'\bgru\b', "FSB": r'\bfsb\b', "UCO / GC": r'\b(uco|guardia civil)\b', "Vor v Zakone": r'\b(vor v zakone|вор в законе|ladron en ley|ladrones en ley)\b', "APT28": r'\bapt28\b', "Wagner": r'\bwagner\b', "MSS": r'\bmss\b', "SBU": r'\bsbu\b'}
    vectores = {"Drones / UAV": r'\b(dron\w*|uav\w*|shahed\w*|бпла|طائرة مسيرة)\b', "Sabotaje": r'\b(sabotaj|dywersja|диверси|تخريب)\b', "Ciberataque": r'\bciberataque\b', "Flota Fantasma": r'\bflota fantasma\b', "Sanciones / FININT": r'\b(elusion|ofac|blanqueo|yuzuk)\b', "Crímenes": r'\b(corte penal|lesa humanidad|masacre|deportacion|grano|зерно)\b'}
    empresas = {"Destinus / Kokorich": r'\b(destinus|kokorich)\b', "Indra": r'\bindra\b', "Oesía": r'\b(oesia|odesia|tecnobit)\b', "Navantia": r'\bnavantia\b'}

    if PATRON_DESINFORMACION_MULTI.search(t_norm):
        etiquetas.append(("Desinformación / Injerencia", "#7c3aed"))
    if PATRON_TERRORISMO_MULTI.search(t_norm):
        etiquetas.append(("Terrorismo / atentado", "#b91c1c"))
    for n, p in actores.items():
        if re.search(p, t_norm): etiquetas.append((n, "#2563eb"))
    for n, p in vectores.items():
        if re.search(p, t_norm): etiquetas.append((n, "#dc2626"))
    for n, p in empresas.items():
        if re.search(p, t_norm): etiquetas.append((n, "#059669"))
    return etiquetas[:4]

def categorizar_noticia(titular, cuerpo, plat, canal):
    canal_l = canal.lower()
    es_red = plat in ("TELEGRAM", "REDES") or "youtube" in canal_l or canal_l.startswith("mastodon")
    cuerpo = str(cuerpo or "")
    texto_puro = desparasitar_nombres_medios(
        f"{titular} {cuerpo[:1500 if es_red else 500]}"
    )
    t_all = normalizar_texto(texto_puro)
    t_tit = normalizar_texto(desparasitar_nombres_medios(titular))
    propio_sharij = (
        plat == "TELEGRAM" and "asupersharij" in canal_l
    ) or (
        (plat == "REDES" or "youtube" in canal_l)
        and "anatolii" in canal_l
        and "sharij" in canal_l
    )
    menciona_sharij = bool(re.search(
        r"\b(anatolii?|anatoly|anatoli)\s+shar(?:iy|ij|y)\b|\b(shariy|sharij|шарий|шарій)\b",
        t_all,
    ))
    if propio_sharij:
        return "REDES"
    if menciona_sharij:
        return "GLOBAL"

    cripto = bool(re.search(r"\b(cripto\w*|crypto\w*|bitcoin|btc|usdt|tether|garantex|blockchain|monero|binance)\b", t_all))
    vector_cripto = bool(re.search(
        r"\b(sancion\w*|sanction\w*|elusion|evasion|blanqueo|lavado|ilicit\w*|illicit|finint|ransomware|"
        r"heist|theft|stolen|hacked|hack|breach|exploit|robbery|robbed|funds? frozen|robo|robado|pirateado)\b",
        t_all,
    ))
    if cripto and vector_cripto:
        return "CRIPTO"
    if PATRON_AGENCIAS.search(t_tit):
        return "AGENCIAS"
    if any(re.search(r'\b' + re.escape(emp) + r'\b', t_tit) for emp in EMPRESAS_ESTRATEGICAS_ESP):
        return "EMPRESA"

    # 1. BLINDAJE DIRECTO DE REDES (Propaganda como Irinamar_Z nunca va a agencias)
    if "irinamar" in canal_l or "musicarusaesp" in canal_l or "desinformador" in canal_l or "rybar" in canal_l or "ophiucu" in canal_l or "elojoen" in canal_l:
        return "REDES"
    if plat == "REDES" or "youtube" in canal_l:
        return "REDES"
    if plat == "TELEGRAM" or "telegram" in canal_l or "@" in canal:
        return "TELEGRAM"

    # 2. CANAL VIP PARA VOR V ZAKONE (Evita el descarte genérico de geopolítica)
    es_vor = bool(re.search(r'\b(vor v zakone|вор в законе|ladron en ley|ladrones en ley|thief in law|thieves in law|mafia rusa|crimen organizado ruso)\b', t_all))
    if es_vor:
        if re.search(r'\b(espana|espanola|madrid|barcelona|marbella|alicante|guardia civil|policia nacional|audiencia nacional)\b', t_all):
            return "ESPANA"
        if PATRON_DETENCION_MULTI.search(t_all):
            return "DETENCION"
        return "GLOBAL"

    # 3. OPERACIÓN YUZUK
    if "yuzuk" in t_all:
        if re.search(r'\b(cripto\w*|crypto\w*|bitcoin|usdt|monedero)\b', t_all):
            return "CRIPTO"
        return "ESPANA"

    # REGLA MAESTRA DE FILTRADO MULTILINGÜE: Debe pertenecer al eje hostil
    tiene_eje_hostil = bool(
        PATRON_RUSIA_UCRANIA.search(t_all) or PATRON_CHINA.search(t_all) or 
        "garantex" in t_all or re.search(r'\b(abw|sbu|cni|bnd|bfv|dgsi|mi6|mi5)\b', t_all)
    )
    titular_norm = normalizar_texto(desparasitar_nombres_medios(titular))
    texto_corto = normalizar_texto(
        desparasitar_nombres_medios(f"{titular} {(cuerpo or '')[:700]}")
    )
    titular_geografico = PATRON_HABLANTES_HISPANOS.sub(" ", titular_norm)
    texto_geografico = PATRON_HABLANTES_HISPANOS.sub(" ", t_all)
    texto_corto_geografico = PATRON_HABLANTES_HISPANOS.sub(" ", texto_corto)
    hay_espana_titular = bool(PATRON_ESPANA_FUERTE.search(titular_geografico))
    es_pais_extranjero_titular = bool(
        PATRON_PAIS_EXTRANJERO_TITULAR.search(titular_geografico)
    )
    es_espana = hay_espana_titular
    tema_ciber_o_espionaje = bool(re.search(
        r"\b(ciberataque\w*|ciberespion\w*|cyberattack\w*|cyber attack\w*|"
        r"cyberespion\w*|cyber espionage|hack\w*|ransomware|ddos|"
        r"espion\w*|espionage|spy|spies|spying|infiltr\w*|"
        r"sabota\w*|sabotage|injerencia\w*|disinformation|"
        r"desinformaci\w*|influence operation|amenaza\w*|threat\w*|"
        r"arson|sancion\w*|sanction\w*)\b",
        t_all,
    ))
    amenaza_detencion = bool(
        PATRON_DETENCION_MULTI.search(t_all)
        and re.search(
            r"\b(espia\w*|espion\w*|spy|spies|hack\w*|cyber\w*|"
            r"sabota\w*|sabotage|terror\w*|fsb|gru|svr|abw|sbu)\b",
            t_all,
        )
    )
    tiene_amenaza_hibrida = bool(
        PATRON_SABOTAJE_MULTI.search(t_all)
        or PATRON_DESINFORMACION_MULTI.search(t_all)
        or PATRON_TERRORISMO_MULTI.search(t_all)
        or PATRON_DRONES_MULTI.search(t_all)
        or tema_ciber_o_espionaje
        or amenaza_detencion
        or re.search(
            r"\b(garantex|cables? submarinos?|infraestructura critica|hybrid warfare)\b",
            t_all,
        )
    )
    despliegue_defensivo_espanol = bool(
        hay_espana_titular
        and tiene_eje_hostil
        and PATRON_OTAN.search(t_all)
        and re.search(
            r"\b(bateria|antiaere\w*|disuasion|defens\w*|desplieg\w*|"
            r"intercept\w*|flanco|misio\w*|caza\w*|fighter\w*)\b",
            t_all,
        )
    )

    if not tiene_eje_hostil and not (
        es_espana
        and tiene_amenaza_hibrida
        and hay_espana_titular
        and not (es_pais_extranjero_titular and not hay_espana_titular)
    ):
        return "DESCARTE"

    menciona_china = PATRON_CHINA.search(t_all) or any(
        c in str(f"{titular} {cuerpo[:500]}").lower() for c in RAICES_CHINO
    )
    if menciona_china and tiene_amenaza_hibrida:
        return "CHINA"

    # 4. AGENCIAS DE INTELIGENCIA (Alertas formales de inteligencia)
    # 6. ESPAÑA (Sabotajes, Ciberseguridad, FCSE, CNI, Audiencia Nacional)
    if es_espana and not (
        es_pais_extranjero_titular and not hay_espana_titular
    ):
        if (
            tiene_amenaza_hibrida
            and (tiene_eje_hostil or hay_espana_titular)
        ) or despliegue_defensivo_espanol:
            return "ESPANA"

    # 7. DETENCIONES INTERNACIONALES MULTILINGÜE
    if PATRON_DETENCION_MULTI.search(t_all): 
        if re.search(r'\b(espia\w*|espion\w*|spy|spies|spying|sabotaj\w*|sabotage|hack\w*|cyber\w*|infiltracion|fsb|gru|svr|abw|sbu|topo ruso|szpieg|шпион|диверси)\b', t_all):
            return "DETENCION"

    # 8. CRÍMENES DE GUERRA MULTILINGÜE
    if PATRON_CRIMENES_MULTI.search(t_all): 
        return "CRIMENES"

    # 9. DRONES Y GUERRA AÉREA / MARÍTIMA MULTILINGÜE
    amenaza_dron = bool(
        PATRON_RUSIA_UCRANIA.search(t_all)
        or PATRON_CHINA.search(t_all)
        or PATRON_OTAN.search(t_all)
        or PATRON_SABOTAJE_MULTI.search(t_all)
        or PATRON_TERRORISMO_MULTI.search(t_all)
        or re.search(r"\b(ataque|attack|strike|militar|military|base|airspace|espacio aereo)\b", t_all)
    )
    if PATRON_DRONES_MULTI.search(t_all) and amenaza_dron:
        return "DRONES"
    
    # 10. CRIPTO Y FININT
    es_cripto_term = bool(re.search(r'\b(cripto\w*|crypto\w*|bitcoin|btc|usdt|tether|garantex|blockchain|monero)\b', t_all))
    if es_cripto_term:
        tiene_vector_cripto = bool(re.search(r'\b(sancion\w*|sanction\w*|elusion|evasion|blanqueo|lavado|ilicit\w*|illicit|finint|ransomware)\b', t_all))
        if tiene_vector_cripto:
            return "CRIPTO"

    # 11. SANCIONES Y FLOTA FANTASMA
    if re.search(r'\b(sancion\w*|sanction\w*|elusion|flota fantasma|shadow fleet|dark fleet|petrolero clandestino|tope al crudo|price cap|ofac)\b', t_all): 
        return "SANCIONES"
    
    # 12. CHINA
    if PATRON_OTAN.search(t_all) and (
        PATRON_RUSIA_UCRANIA.search(t_all)
        or PATRON_CHINA.search(t_all)
        or PATRON_SABOTAJE_MULTI.search(t_all)
        or PATRON_DESINFORMACION_MULTI.search(t_all)
        or PATRON_TERRORISMO_MULTI.search(t_all)
    ):
        return "OTAN"

    if PATRON_INJERENCIA.search(t_all) and (
        PATRON_RUSIA_UCRANIA.search(t_all) or PATRON_CHINA.search(t_all)
    ):
        return "INJERENCIA"

    if PATRON_ASESINATO.search(t_all) and (
        PATRON_RUSIA_UCRANIA.search(t_all) or PATRON_CHINA.search(t_all)
    ):
        return "ASESINATOS"
    
    # 13. GLOBAL (Eventos confirmados de guerra híbrida y crimen estatal)
    tiene_tema_hibrido = bool(
        PATRON_SABOTAJE_MULTI.search(t_all)
        or PATRON_DESINFORMACION_MULTI.search(t_all)
        or PATRON_TERRORISMO_MULTI.search(t_all)
        or re.search(
        r'\b(guerra hibrida|hybrid warfare|sabotaj\w*|sabotage|ciberataque\w*|espionaje|espia\w*|injerencia\w*|fimi|doppelganger|'
        r'desinformacion|sancion\w*|flota fantasma|shadow fleet|cables? submarinos?|uav|crimen de guerra|war crime|cpi|icc|yuzuk|'
        r'asesinato selectivo|sicario\w*|envenenamiento|arson|incendio provocado|otan|nato)\b', t_all
        )
    )
    if tiene_tema_hibrido or tiene_amenaza_hibrida:
        return "GLOBAL"
        
    return "DESCARTE"

def generar_contexto_trazabilidad(categoria, canal=""):
    c = canal.lower()
    prefijo = "📌 Contexto de seguimiento: "
    if categoria == "AGENCIAS": return prefijo + "Inteligencia internacional (CIA, CNI, MI5/MI6, etc.): alertas tácticas y operaciones de seguridad."
    if categoria == "INJERENCIA": return prefijo + "Operaciones de influencia y desinformación atribuidas en fuentes abiertas; verificar atribución y contexto."
    if categoria == "OTAN": return prefijo + "Incidentes y amenazas híbridas relacionados con la OTAN; la clasificación no implica confirmación del hecho."
    if categoria == "ASESINATOS": return prefijo + "Seguimiento de noticias sobre asesinatos o envenenamientos; verificar hechos y atribución con fuentes independientes."
    if "irinamar" in c or "musicarusa" in c: return prefijo + "Canal identificado en el ecosistema de propaganda y desinformación pro-Kremlin (FIMI)."
    if "vor" in c or "ladron" in c: return prefijo + "Redes transnacionales de Vor v Zakone y su utilización en la estructura de poder rusa."
    if "euromaidan" in c: return prefijo + "Monitor ucraniano sobre operaciones de defensa, frentes y guerra de resistencia."
    if "rumafia" in c: return prefijo + "Investigación web sobre crimen organizado ruso."
    if "antikor" in c: return prefijo + "Portal ucraniano de investigaciones y seguridad."
    if "rybar" in c: return prefijo + "Canal militar prorruso. Narrativa oficial sujeta a contraste."
    if "sharij" in c or "saharij" in c: return prefijo + "Cobertura táctica y seguimiento del frente en redes."
    if "bellingcat" in c or "insider" in c: return prefijo + "Investigación independiente."
    if "mi5" in c or "uk intelligence" in c or "cia" in c: return prefijo + "Alerta de servicios de inteligencia internacionales."
    if "yuzuk" in c: return prefijo + "Operación policial (UCO / Guardia Civil) contra estructuras internacionales de blanqueo y criptoactivos."
    return prefijo + "Monitoreo preventivo en fuentes abiertas sobre guerra híbrida."
