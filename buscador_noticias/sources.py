import re
import xml.etree.ElementTree as ET
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse
from zoneinfo import ZoneInfo

import requests
import streamlit as st
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import PATRON_IMPACTO_MULTILINGUE
from .dictionary import coincidencia_personalizada
from .language_catalog import IDIOMAS_BUSQUEDA
from .perfiles import CANALES_VIGILADOS, feeds_perfiles, perfil_de_canal, perfiles_en
from .processing import (
    aplicar_categoria_personalizada,
    categorizar_noticia,
    es_relevante_en_origen,
    es_tematico_redes,
    extraer_entidades_clave,
    generar_contexto_trazabilidad,
    id_determinista,
    limpiar_firma_medio,
    limpiar_html_texto,
    limpiar_url,
    normalizar_texto,
)


@st.cache_resource
def obtener_sesion_http():
    sesion = requests.Session()
    reintentos = Retry(
        total=1,
        connect=1,
        read=1,
        status=1,
        backoff_factor=0.25,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    adapter = HTTPAdapter(
        pool_connections=120,
        pool_maxsize=120,
        max_retries=reintentos,
    )
    sesion.mount("https://", adapter)
    sesion.mount("http://", adapter)
    sesion.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept-Encoding": "gzip, deflate",
        # Incluido el idioma árabe en las cabeceras
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8,ru;q=0.7,uk;q=0.7,pl;q=0.6,ar;q=0.5"
    })
    return sesion

SESION_HTTP = obtener_sesion_http()
TIMEOUT_HTTP = (2, 4)
_STOP_TITULARES = {
    "para", "como", "este", "esta", "sobre", "rusia", "ucrania",
    "with", "that", "from", "have", "russia", "ukraine",
}


@st.cache_resource
def obtener_ejecutor_fuentes():
    return ThreadPoolExecutor(max_workers=1)


def raspar_euromaidanpress():
    items = []
    try:
        r = SESION_HTTP.get("https://euromaidanpress.com/feed/", timeout=TIMEOUT_HTTP)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            for item in root.findall(".//item")[:25]:
                tit = limpiar_html_texto(item.findtext("title", ""))
                desc = item.findtext("description", "")
                link = item.findtext("link", "")
                pub = item.findtext("pubDate", "")
                cuerpo = limpiar_html_texto(desc)[:1200]
                try: dt_obj = parsedate_to_datetime(pub).astimezone(timezone.utc)
                except Exception: dt_obj = None

                items.append({
                    "id": f"EMP-{id_determinista(link + tit)}", "plataforma": "PRENSA", "canal": "Euromaidan Press",
                    "fecha_dt": dt_obj, "fecha_estimada": False,
                    "titular_raw": tit, "cuerpo_raw": cuerpo if cuerpo else tit,
                    "multimedia": None, "tiene_video": False, "enlace": link
                })
    except Exception: pass
    return items, None

def raspar_rumafia():
    items = []
    try:
        r = SESION_HTTP.get("https://www.rumafia.net/en", timeout=TIMEOUT_HTTP)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                texto = a.get_text(strip=True)
                if len(texto) > 25 and any(ruta in href for ruta in ["/en/article/", "/en/dosje/", "/en/material/"]):
                    url_full = f"https://www.rumafia.net{href}" if href.startswith("/") else href
                    parent = a.find_parent(["div", "li", "tr"])
                    dt_obj = None
                    if parent:
                        m_date = re.search(r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b', parent.get_text())
                        if m_date:
                            try:
                                d, m, y = m_date.groups()
                                dt_obj = datetime(int(y), int(m), int(d), tzinfo=timezone.utc)
                            except Exception: pass

                    items.append({
                        "id": f"RUM-{id_determinista(url_full)}", "plataforma": "INVESTIGACIÓN", "canal": "RuMafia (EN)",
                        "fecha_dt": dt_obj, "fecha_estimada": (dt_obj is None),
                        "titular_raw": texto,
                        "cuerpo_raw": "Investigación documental sobre crimen organizado ruso, redes de poder y operaciones económicas del Kremlin.",
                        "multimedia": None, "tiene_video": False, "enlace": url_full
                    })
    except Exception: pass
    return items[:15], None

def raspar_antikor():
    items = []
    try:
        r = SESION_HTTP.get("https://antikor.info/en/articles", timeout=TIMEOUT_HTTP)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for div in soup.find_all(["div", "li"], class_=re.compile(r"item|article|news", re.I))[:20]:
                a_tag = div.find("a", href=True)
                if a_tag and len(a_tag.get_text(strip=True)) > 20:
                    href = a_tag["href"]
                    tit = limpiar_html_texto(a_tag.get_text(strip=True))
                    url_full = f"https://antikor.info{href}" if href.startswith("/") else href
                    dt_obj = None
                    time_elem = div.find(["time", "span"], class_=re.compile(r"date|time", re.I))
                    if time_elem:
                        m_date = re.search(r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b', time_elem.get_text())
                        if m_date:
                            try:
                                d, m, y = m_date.groups()
                                dt_obj = datetime(int(y), int(m), int(d), tzinfo=timezone.utc)
                            except Exception: pass
                    
                    desc_tag = div.find(["p", "span"])
                    desc = limpiar_html_texto(desc_tag.get_text(strip=True)) if desc_tag else "Reporte de seguridad, investigaciones judiciales y operaciones en Ucrania."
                    items.append({
                        "id": f"ANT-{id_determinista(url_full)}", "plataforma": "INVESTIGACIÓN", "canal": "Antikor (EN)",
                        "fecha_dt": dt_obj, "fecha_estimada": (dt_obj is None),
                        "titular_raw": tit, "cuerpo_raw": desc[:1000],
                        "multimedia": None, "tiene_video": False, "enlace": url_full
                    })
    except Exception: pass
    return items[:15], None

def raspar_youtube_canal(canal_id, etiqueta):
    items = []
    try:
        r = SESION_HTTP.get(f"https://www.youtube.com/feeds/videos.xml?channel_id={canal_id}", timeout=TIMEOUT_HTTP)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry")[:18]:
                tit = limpiar_html_texto(entry.findtext("{http://www.w3.org/2005/Atom}title", ""))
                link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                link = link_el.get("href", "") if link_el is not None else ""
                pub = entry.findtext("{http://www.w3.org/2005/Atom}published", "")
                desc = limpiar_html_texto(entry.findtext(".//{http://search.yahoo.com/mrss/}description", ""))

                try: dt_obj = datetime.fromisoformat(pub.replace("Z", "+00:00")).astimezone(timezone.utc)
                except Exception: dt_obj = None

                texto_yt = normalizar_texto(f"{tit} {desc}")
                if not es_tematico_redes(texto_yt):
                    continue

                items.append({
                    "id": f"YT-{id_determinista(link + tit)}", "plataforma": "REDES", "canal": etiqueta, "fecha_dt": dt_obj,
                    "fecha_estimada": False,
                    "titular_raw": tit, "cuerpo_raw": desc if desc else "Publicación audiovisual en canal oficial.",
                    "multimedia": None, "tiene_video": True, "enlace": link
                })
    except Exception: pass
    return items, None

def raspar_youtube_handle(handle, etiqueta):
    try:
        response = SESION_HTTP.get(
            f"https://www.youtube.com/@{handle}",
            timeout=TIMEOUT_HTTP,
            headers={"Cookie": "CONSENT=YES+1; SOCS=CAI"},
        )
        if response.status_code != 200:
            return [], f"YouTube @{handle} (HTTP {response.status_code})"
        match = (
            re.search(r'channel_id=(UC[\w-]{20,})', response.text)
            or re.search(r'"channelId":"(UC[\w-]{20,})"', response.text)
            or re.search(r'/channel/(UC[\w-]{20,})', response.text)
        )
        if not match:
            return [], f"YouTube @{handle} (no se pudo resolver el canal)"
        return raspar_youtube_canal(match.group(1), etiqueta)
    except requests.RequestException as exc:
        return [], f"YouTube @{handle} ({type(exc).__name__})"


def raspar_mastodon_tag(instancia, tag):
    items = []
    try:
        response = SESION_HTTP.get(f"https://{instancia}/tags/{tag}.rss", timeout=TIMEOUT_HTTP)
        if response.status_code != 200:
            return items, f"Mastodon #{tag} ({instancia}, HTTP {response.status_code})"
        root = ET.fromstring(response.content)
        for entry in root.findall(".//item")[:40]:
            titulo = limpiar_html_texto(entry.findtext("title", ""))
            descripcion = limpiar_html_texto(entry.findtext("description", ""))
            texto = descripcion if len(descripcion) >= len(titulo) else titulo
            if len(texto) < 25 or not es_tematico_redes(texto):
                continue
            enlace = entry.findtext("link", "")
            try:
                fecha = parsedate_to_datetime(entry.findtext("pubDate", "")).astimezone(timezone.utc)
            except (TypeError, ValueError, OverflowError):
                fecha = None
            items.append({
                "id": f"MST-{id_determinista(enlace + texto[:40])}",
                "plataforma": "REDES",
                "canal": f"Mastodon #{tag} ({instancia})",
                "fecha_dt": fecha,
                "fecha_estimada": fecha is None,
                "titular_raw": texto[:140],
                "cuerpo_raw": texto[:1200],
                "multimedia": None,
                "tiene_video": False,
                "enlace": enlace,
            })
    except (requests.RequestException, ET.ParseError) as exc:
        return items, f"Mastodon #{tag} ({type(exc).__name__})"
    return items, None


RUNEWS24_PAGINAS = (
    "", "politics", "world", "society", "incidents", "articles",
    "specoperaciya-na-ukraine", "rossiya-i-kitaj", "sankczionnoe-protivostoyanie",
    "ssha-i-kitaj", "rossiya-i-belorussiya", "obostrenie-vokrug-tajvanya",
    "technology", "vladimir-zelenskij",
)
_RE_RUN_URL = re.compile(r"/([\w-]+)/(\d{2})/(\d{2})/(\d{4})/[\w-]+")
ZONA_MOSCU = ZoneInfo("Europe/Moscow")


def _partir_texto_runews(texto):
    texto = re.sub(r"\s+", " ", texto).strip()
    texto = re.sub(r"^\d{1,2}:\d{2}\s+", "", texto)
    fecha = re.search(r"\s(\d{2})\.(\d{2})\.(\d{4})\s(\d{2}):(\d{2})\s", texto)
    if not fecha:
        return texto, "", None
    titular = texto[:fecha.start()].strip()
    cuerpo = texto[fecha.end():].strip()
    if cuerpo.startswith(titular):
        cuerpo = cuerpo[len(titular):].strip()
    return titular, cuerpo, fecha.groups()


def _raspar_pagina_runews24(pagina):
    url = f"https://runews24.ru/{pagina}"
    respuesta = SESION_HTTP.get(url, timeout=TIMEOUT_HTTP)
    if respuesta.status_code != 200:
        raise RuntimeError(f"HTTP {respuesta.status_code}")

    resultados = []
    soup = BeautifulSoup(respuesta.text, "html.parser")
    for enlace in soup.find_all("a", href=True):
        href = enlace["href"]
        if href.startswith("/"):
            href = f"https://runews24.ru{href}"
        if urlparse(href).netloc.lower() not in {"runews24.ru", "www.runews24.ru"}:
            continue
        coincidencia = _RE_RUN_URL.search(urlparse(href).path)
        if not coincidencia:
            continue

        titular, cuerpo, fecha_texto = _partir_texto_runews(
            enlace.get_text(" ", strip=True)
        )
        if len(titular) < 25:
            continue
        dia, mes, anio = map(int, coincidencia.groups()[1:])
        hora, minuto = (12, 0)
        if fecha_texto:
            hora, minuto = map(int, fecha_texto[3:])
        try:
            fecha = datetime(
                anio, mes, dia, hora, minuto, tzinfo=ZONA_MOSCU
            ).astimezone(timezone.utc)
        except ValueError:
            fecha = None
        resultados.append((limpiar_url(href), titular, cuerpo, fecha))
    return resultados


def raspar_runews24():
    resultados = {}
    errores = 0
    with ThreadPoolExecutor(max_workers=6) as ejecutor:
        futuros = [
            ejecutor.submit(_raspar_pagina_runews24, pagina)
            for pagina in RUNEWS24_PAGINAS
        ]
        for futuro in futuros:
            try:
                for url, titular, cuerpo, fecha in futuro.result():
                    anterior = resultados.get(url)
                    if anterior is None or len(cuerpo) > len(anterior[1]):
                        resultados[url] = (titular, cuerpo, fecha)
            except Exception:
                errores += 1

    items = [
        {
            "id": f"RUN-{id_determinista(url)}",
            "plataforma": "PRENSA",
            "canal": "RuNews24 (RU)",
            "fecha_dt": fecha,
            "fecha_estimada": fecha is None,
            "titular_raw": limpiar_html_texto(titular),
            "cuerpo_raw": limpiar_html_texto(cuerpo[:1200]) or limpiar_html_texto(titular),
            "multimedia": None,
            "tiene_video": False,
            "enlace": url,
        }
        for url, (titular, cuerpo, fecha) in list(resultados.items())[:250]
    ]
    if not items:
        return [], "sin resultados (¿bloqueo del servidor?)"
    if errores >= len(RUNEWS24_PAGINAS) // 2:
        return items, f"{errores} páginas fallaron"
    return items, None


def raspar_un_canal_tg(canal):
    mensajes = []
    try:
        r = SESION_HTTP.get(f"https://t.me/s/{canal}", timeout=TIMEOUT_HTTP)
        if r.status_code != 200:
            return [], f"Telegram @{canal} (HTTP {r.status_code})"
        soup = BeautifulSoup(r.text, "html.parser")

        for p in soup.find_all("div", class_="tgme_widget_message_wrap")[-40:]:
            time_tag = p.find("time")
            try: dt_obj = datetime.fromisoformat(time_tag.get("datetime").replace("Z", "+00:00")).astimezone(timezone.utc) if time_tag else None
            except Exception: dt_obj = None

            t_div = p.find("div", class_="tgme_widget_message_text")
            texto_raw = t_div.get_text(separator=" ", strip=True) if t_div else ""
            if len(texto_raw) < 15: continue

            texto_sin_urls = limpiar_html_texto(re.sub(r'http\S+', '', texto_raw))
            if not es_tematico_redes(texto_sin_urls) and not perfil_de_canal(canal):
                continue

            foto_url = None
            tiene_video = False
            for tag_foto in p.find_all("a", class_="tgme_widget_message_photo_wrap"):
                estilo = tag_foto.get("style", "")
                m = re.search(r"url\(['\"]?(https?://[^'\")]+)['\"]?\)", estilo)
                if m:
                    foto_url = m.group(1)
                    break

            for elem in p.find_all(["i", "div", "a", "video"]):
                clases = " ".join(elem.get("class", [])) if elem.get("class") else ""
                if elem.name == "video" or any(v in clases for v in ["video", "roundvideo"]):
                    tiene_video = True
                    estilo = elem.get("style", "")
                    if estilo and not foto_url:
                        m = re.search(r"url\(['\"]?(https?://[^'\")]+)['\"]?\)", estilo)
                        if m:
                            foto_url = m.group(1)

            a_link = p.find("a", class_="tgme_widget_message_date")
            link = a_link["href"] if a_link else f"https://t.me/s/{canal}"
            tit_corto = re.split(r'(?<=[.!?])\s+', texto_sin_urls)[0][:140]

            mensajes.append({
                "id": f"TG-{id_determinista(link + tit_corto)}", 
                "plataforma": "TELEGRAM", 
                "canal": f"@{canal}",
                "fecha_dt": dt_obj, "fecha_estimada": False,
                "titular_raw": tit_corto, "cuerpo_raw": texto_sin_urls,
                "multimedia": foto_url, "tiene_video": tiene_video, "enlace": link
            })
    except Exception:
        return [], f"Telegram @{canal} (Omitido)"
    return mensajes, None

def decodificar_url_google_news_offline(url_rss):
    if not url_rss or "news.google.com" not in url_rss:
        return url_rss
    try:
        import base64
        m = re.search(r'articles/([A-Za-z0-9_-]+)', url_rss)
        if m:
            token = m.group(1)
            pad = token + "=" * ((4 - len(token) % 4) % 4)
            decoded_bytes = base64.urlsafe_b64decode(pad)
            for u in re.findall(rb'https?://[^\s"\'<>\\\x00-\x1f\x7f-\xff]+', decoded_bytes):
                u_str = u.decode('utf-8', errors='ignore')
                if "google.com" not in u_str and len(u_str) > 16:
                    return u_str
    except Exception: pass
    return url_rss


def _tokens_titular(titular):
    return {
        palabra
        for palabra in re.findall(r"\w{4,}", normalizar_texto(titular))
        if palabra not in _STOP_TITULARES
    }


def procesar_un_feed_rss(datos_feed):
    url, etiqueta = datos_feed
    items = []
    try:
        r = SESION_HTTP.get(url, timeout=TIMEOUT_HTTP)
        if r.status_code != 200 or not r.content:
            return [], f"{etiqueta} (HTTP {r.status_code})"
        
        try:
            root = ET.fromstring(r.content)
        except Exception:
            return [], f"{etiqueta} (Error de parseo XML)"

        plataforma_feed = "PRENSA"

        entradas = []
        for item in root.findall(".//item")[:80]:
            entradas.append((
                item.findtext("title", ""),
                item.findtext("description", ""),
                item.findtext("link", ""),
                item.findtext("pubDate", ""),
                item.findtext("source", ""),
            ))
        if not entradas:
            ns = "{http://www.w3.org/2005/Atom}"
            for entry in root.findall(f".//{ns}entry")[:80]:
                link_element = entry.find(f"{ns}link")
                entradas.append((
                    entry.findtext(f"{ns}title", ""),
                    entry.findtext(f"{ns}summary", "") or entry.findtext(f"{ns}content", ""),
                    link_element.get("href", "") if link_element is not None else "",
                    entry.findtext(f"{ns}updated", "") or entry.findtext(f"{ns}published", ""),
                    "",
                ))

        for tit_raw, desc, link, pub, fuente_raw in entradas:
            tit = limpiar_html_texto(tit_raw)
            fuente_nombre = limpiar_html_texto(fuente_raw).strip() or etiqueta

            cuerpo_crudo = limpiar_html_texto(desc)[:1200]
            texto_eval = f"{tit} {cuerpo_crudo}"

            if not es_relevante_en_origen(texto_eval, etiqueta):
                continue

            try:
                dt_obj = parsedate_to_datetime(pub).astimezone(timezone.utc)
            except (TypeError, ValueError, OverflowError):
                try:
                    dt_obj = datetime.fromisoformat(pub.replace("Z", "+00:00")).astimezone(timezone.utc)
                except (TypeError, ValueError, OverflowError):
                    dt_obj = None

            url_destino = decodificar_url_google_news_offline(link) if "news.google.com" in link else link

            items.append({
                "id": f"RSS-{id_determinista(url_destino + tit)}", "plataforma": plataforma_feed, "canal": etiqueta,
                "fuente_nombre": fuente_nombre,
                "fecha_dt": dt_obj, "fecha_estimada": False,
                "titular_raw": limpiar_firma_medio(tit), "cuerpo_raw": cuerpo_crudo,
                "multimedia": None, "tiene_video": False, "enlace": url_destino
            })
    except Exception as e:
        return [], f"{etiqueta} ({type(e).__name__})"
    return items, None


def feeds_multilingues():
    feeds = []
    for hl, gl, ceid, actor_ru, actor_cn, temas_ru, temas_cn, temas_ru_extra in IDIOMAS_BUSQUEDA:
        consultas = (
            (actor_ru, temas_ru, "Rusia: sabotaje, espionaje y detenciones"),
            (actor_cn, temas_cn, "China: espionaje e injerencia"),
            (actor_ru, temas_ru_extra, "Rusia: drones, crímenes y sanciones"),
        )
        for actor, temas, etiqueta in consultas:
            consulta = f'"{actor}" ({temas}) when:14d'
            url = (
                "https://news.google.com/rss/search?q="
                f"{quote_plus(consulta)}&hl={hl}&gl={gl}&ceid={ceid}"
            )
            feeds.append((url, f"[{hl}] {etiqueta}"))
    return feeds


def _feed_google_news(consulta, hl, gl, ceid, etiqueta):
    url = (
        "https://news.google.com/rss/search?q="
        f"{quote_plus(consulta)}&hl={hl}&gl={gl}&ceid={ceid}"
    )
    return url, etiqueta


def feeds_espana():
    idiomas = {
        "es": ("es", "ES", "ES:es"),
        "en": ("en-US", "US", "US:en"),
        "fr": ("fr", "FR", "FR:fr"),
        "de": ("de", "DE", "DE:de"),
        "ru": ("ru", "RU", "RU:ru"),
        "uk": ("uk", "UA", "UA:uk"),
    }
    consultas = (
        ('("ladrón en ley" OR "ladrones en ley" OR "vor v zakone" OR "mafia rusa" OR "mafia georgiana" OR "mafia chechena" OR "mafia ucraniana") (detenido OR detenidos OR "Guardia Civil" OR "Policía Nacional" OR España OR Marbella OR Alicante OR Málaga OR Valencia)', "es", "España: mafias rusófonas"),
        ('("organización criminal" OR "red criminal") (rusa OR georgiana OR chechena OR ucraniana OR "del este") (España OR "Guardia Civil" OR "Policía Nacional" OR "Audiencia Nacional") (desarticulada OR detenidos OR operación)', "es", "España: redes criminales"),
        ('("thief in law" OR "thieves in law" OR "Russian mafia" OR "Georgian mafia") Spain (arrested OR police OR "Guardia Civil")', "en", "España: mafia (EN)"),
        ('("вор в законе" OR "воры в законе") (Испания OR Барселона OR Марбелья OR Аликанте OR Малага OR Валенсия)', "ru", "España: mafia (RU)"),
        ('España (elecciones OR electoral OR comicios OR Cataluña OR referéndum) ("injerencia rusa" OR desinformación OR "campaña de desinformación" OR "Voice of Europe") (Rusia OR Kremlin OR Putin)', "es", "España: injerencia electoral"),
        ('España (China OR chino OR Pekín) (injerencia OR influencia OR "comisarías secretas" OR TikTok OR espionaje OR "Safeguard Defenders")', "es", "España: injerencia china"),
        ('(Maldita OR Newtral OR Verificat OR EFE Verifica) (Rusia OR Kremlin OR Putin OR prorrusa OR China) (desinformación OR bulo OR propaganda) España', "es", "España: verificadores"),
        ('Spain (Russia OR Russian OR China OR Chinese) ("election interference" OR disinformation OR "influence operation" OR Doppelgänger OR "Pravda network")', "en", "España: injerencia (EN)"),
        ('España OTAN (Rusia OR Putin OR Kremlin OR China) (amenaza OR sabotaje OR drones OR ciberataque OR "guerra híbrida" OR Rota OR Torrejón OR Cartagena)', "es", "España: OTAN"),
        ('Spain NATO (Russia OR China) (sabotage OR cyberattack OR drones OR hybrid OR espionage)', "en", "España: OTAN (EN)"),
        ('(ciberataque OR "ataque informático" OR hackers OR hacktivistas OR DDoS OR NoName057) España (ruso OR Rusia OR prorrusos)', "es", "España: ciberataques rusos"),
        ('(ciberataque OR ciberespionaje OR hackers OR APT OR "Salt Typhoon" OR "Volt Typhoon") España (China OR chino OR Pekín)', "es", "España: ciberataques chinos"),
        ('(INCIBE OR "CCN-CERT" OR CNI OR "Departamento de Seguridad Nacional" OR "Mando Conjunto del Ciberespacio") (Rusia OR China) (ciberataque OR ciberespionaje OR amenaza)', "es", "España: ciberdefensa"),
        ('Spain (Russia OR Russian OR China OR Chinese) (cyberattack OR hackers OR "cyber espionage" OR DDoS OR ransomware)', "en", "España: ciberataques (EN)"),
        ('España (sabotaje OR "cables submarinos" OR ferrocarril OR "infraestructuras críticas" OR "incendios provocados") (Rusia OR GRU OR China)', "es", "España: sabotajes"),
        ('(CNI OR "Guardia Civil" OR "Policía Nacional" OR "Audiencia Nacional") (espía OR espionaje OR "agente ruso" OR "agente chino" OR "diplomático ruso") España', "es", "España: espionaje y diplomáticos"),
        ('Spain (Russian OR Russia OR China) (sabotage OR spy OR spies OR espionage OR arrested)', "en", "España: espionaje (EN)"),
        ('Espagne (Russie OR Chine) (sabotage OR espionnage OR cyberattaque OR ingérence OR désinformation)', "fr", "España: seguimiento (FR)"),
        ('Spanien (Russland OR China) (Sabotage OR Spionage OR Cyberangriff OR Einflussnahme OR Desinformation)', "de", "España: seguimiento (DE)"),
        ('Испания (ФСБ OR ГРУ OR шпионаж OR диверсия OR кибератака OR Кремль OR российский) -футбол', "ru", "España: seguimiento (RU)"),
        ('("Storm-1516" OR Doppelgänger OR Matryoshka OR "Portal Kombat" OR "Pravda network" OR "Voice of Europe" OR Spamouflage)', "en", "Operaciones de influencia"),
        ('("election interference" OR "electoral interference") (Russia OR China OR Kremlin)', "en", "Injerencia electoral (EN)"),
        ('injerencia electoral (Rusia OR China OR Kremlin) (elecciones OR comicios)', "es", "Injerencia electoral (ES)"),
        ('ingérence russe élections (Russie OR Kremlin)', "fr", "Injerencia electoral (FR)"),
        ('russische Einflussnahme Wahl (Russland OR Kreml)', "de", "Injerencia electoral (DE)"),
        ('NATO (sabotage OR hybrid OR drones OR airspace OR cyberattack) Russia', "en", "OTAN: amenazas híbridas (EN)"),
        ('OTAN (Rusia OR Kremlin) ("guerra híbrida" OR sabotaje OR drones OR "espacio aéreo" OR "artículo 5")', "es", "OTAN: amenazas híbridas (ES)"),
    )
    return [
        _feed_google_news(consulta, *idiomas[codigo], f"{etiqueta} [{codigo.upper()}]")
        for consulta, codigo, etiqueta in consultas
    ]


def feeds_empresas():
    es = ("es", "ES", "ES:es")
    en = ("en-US", "US", "US:en")
    ru = ("ru", "RU", "RU:ru")
    uk = ("uk", "UA", "UA:uk")
    amen_es = "(Rusia OR ruso OR China OR Ucrania OR espionaje OR ciberataque OR sabotaje OR drones OR sanciones OR FSB OR GRU OR Huawei)"
    amen_en = "(Russia OR Russian OR China OR Ukraine OR espionage OR cyberattack OR sabotage OR drones OR sanctions OR FSB OR GRU)"
    consultas = (
        ('(Destinus OR Kokorich OR "Mikhail Kokorich")', es, "Destinus / Kokorich (ES)"),
        ('(Destinus OR Kokorich OR "Mikhail Kokorich")', en, "Destinus / Kokorich (EN)"),
        ('(Кокорич OR "Михаил Кокорич" OR Destinus)', ru, "Destinus / Kokorich (RU)"),
        ('(Кокорич OR "Михайло Кокорич" OR Destinus)', uk, "Destinus / Kokorich (UK)"),
        (f'("Grupo Oesía" OR Oesía OR Oesia OR Odesia OR "UAV Navigation" OR Tecnobit) {amen_es}', es, "Oesía / UAV Navigation / Tecnobit"),
        (f'(Oesia OR "UAV Navigation" OR Tecnobit) {amen_en}', en, "Oesía (EN)"),
        (f'("Indra Sistemas" OR "Indra Defensa" OR "Indra Group" OR Indra) {amen_es}', es, "Indra (ES)"),
        (f'("Indra Sistemas" OR "Indra Group") {amen_en}', en, "Indra (EN)"),
        (f'(Navantia OR "Santa Bárbara Sistemas" OR Expal OR Instalaza OR Urovesa OR "ITP Aero" OR "Airbus Defence") {amen_es}', es, "Navantia / Santa Bárbara / Expal"),
        (f'(Escribano OR "EM&E" OR Sener OR Arquimea OR Isdefe OR GMV OR Maxam OR Aernnova OR Aciturri) {amen_es}', es, "Empresas de defensa"),
        (f'(Hisdesat OR Hispasat OR Sateliot OR "PLD Space" OR Talgo) {amen_es}', es, "Empresas de espacio e infraestructuras"),
        ('(Telefónica OR Iberdrola OR Endesa OR Naturgy OR "Red Eléctrica" OR Enagás OR Enaire OR Aena) (ciberataque OR hackers OR espionaje OR sabotaje OR drones) (Rusia OR China)', es, "Infraestructuras críticas"),
        (f'(Spanish OR Spain) (defense OR defence OR arms OR drone) (company OR firm OR maker) {amen_en}', en, "Empresas españolas de defensa (EN)"),
        ('site:infodefensa.com (Indra OR Oesía OR Destinus OR Navantia OR Escribano OR Tecnobit) (Rusia OR China OR ciberataque OR espionaje OR Ucrania)', es, "Infodefensa"),
        ('site:defensa.com (Indra OR Oesía OR Destinus OR Navantia OR Tecnobit) (Rusia OR China OR ciberataque OR espionaje OR Ucrania)', es, "Revista Defensa"),
        ('(Kokorich OR Destinus) ("Guardia Civil" OR "Audiencia Nacional" OR CNI OR FSB OR espionaje OR sanciones OR Roscosmos)', es, "Kokorich: investigación"),
    )
    return [
        _feed_google_news(consulta, *locale, f"Empresas: {etiqueta}")
        for consulta, locale, etiqueta in consultas
    ]


def feeds_sharij():
    variantes_locales = {
        "fr": ('"Anatoli Chariy"', '"Anatoly Chariy"'),
        "de": ('"Anatolij Scharij"', '"Anatoli Scharij"', "Scharij"),
        "it": ('"Anatolij Sharij"',),
        "pl": ('"Anatolij Szarij"', '"Anatolij Szary"', "Szarij"),
        "uk": ('"Анатолій Шарій"', "Шарій"),
        "ru": ('"Анатолий Шарий"', "Шарий"),
        "bg": ('"Анатолий Шарий"', "Шарий"),
        "sr": ('"Анатолий Шарий"', "Шарий"),
        "cs": ('"Anatolij Šarij"', "Šarij"),
        "sk": ('"Anatolij Šarij"',),
        "ro": ('"Anatolii Șarii"', "Șarii"),
        "hu": ('"Anatolij Sarij"',),
        "hr": ('"Anatolij Šarij"',),
        "lt": ('"Anatolijus Šarijus"', "Šarijus"),
        "lv": ('"Anatolijs Šarijs"', "Šarijs"),
        "et": ('"Anatoli Šari"',),
        "nl": ('"Anatoli Sjarij"',),
        "tr": ('"Anatoli Şarii"',),
        "ar": ('"أناتولي شاري"',),
        "he": ('"אנטולי שרי"',),
        "zh-CN": ('"阿纳托利·沙里"',),
        "zh-TW": ('"阿納托利·沙里"',),
        "ja": ('"アナトリー・シャリー"',),
        "ko": ('"아나톨리 샤리"',),
        "el": ('"Ανατόλι Σαρί"', '"Ανατόλι Σάρι"'),
        "ka": ('"ანატოლი შარი"',),
    }
    variantes_base = (
        '"Anatolii Shariy"', '"Anatoly Shariy"', '"Anatolii Sharij"',
        '"Anatoli Sharij"', '"Anatoliy Shariy"', "Shariy", "Sharij",
        '"Анатолий Шарий"', '"Анатолій Шарій"', "Шарий", "Шарій",
    )
    feeds = []
    for hl, gl, ceid, *_ in IDIOMAS_BUSQUEDA:
        variantes = tuple(dict.fromkeys(
            variantes_base + variantes_locales.get(hl, ())
        ))
        consulta = f"({' OR '.join(variantes)}) when:180d"
        feeds.append(
            _feed_google_news(consulta, hl, gl, ceid, f"Sharij: noticias [{hl}]")
        )
    feeds.append(("https://sharij.net/feed/", "Sharij.net (RSS)"))
    return feeds


def feeds_runews24():
    consultas = (
        ('site:runews24.ru (Испания OR испанский OR Мадрид)', "RuNews24: España"),
        ('site:runews24.ru (Китай OR китайский) (шпионаж OR кибератака OR диверсия OR санкции OR Тайвань)', "RuNews24: China"),
        ('site:runews24.ru (диверсия OR шпионаж OR кибератака OR дроны OR БПЛА OR НАТО OR санкции OR "военные преступления")', "RuNews24: amenazas"),
        ('site:runews24.ru (зерно OR "украденное зерно" OR "вывоз зерна") Украина', "RuNews24: grano ucraniano"),
        ('site:runews24.ru Шарий', "RuNews24: Sharij"),
    )
    return [
        _feed_google_news(consulta, "ru", "RU", "RU:ru", etiqueta)
        for consulta, etiqueta in consultas
    ]


@st.cache_data(ttl=1800, show_spinner=False)
def cargar_todas_las_fuentes(diccionario_personalizado=()):
    telemetria_fuentes = []
    
    canales_yt = [
        ("UCVPYbobPRzz0SjinWekjUBw", "YouTube: Anatolii Sharij"),
        ("UCwd8Byi93KbnsYmCcKLExvQ", "YouTube: Descifrando la Guerra")
    ]

    canales_tg = list(dict.fromkeys([
        "musicarusaesp", "ASupersharij", "desinformador", "rybar", "DIUkraine", "SBUkr", 
        "informnapalm", "cyberresistanceua", "GeneralStaffZSU", "kpszsu", "operativnoZSU", 
        "CenterCounteringDisinformation", "meduzalive", "astrapress", "istories_media", 
        "vchkogpu", "mediazzzona", "bbcrussian", "novayagazeta_europe", "theinsider_ru", 
        "kyivindependent_official", "pravda_com_ua", "ukrainenowenglish", "Irinamar_Z", 
        "eurekapress", "elOJOen", "ophiucu", "DeepStateUA", "exilenova_plus",
        "wargonzo", "RVvoenkor", "nexta_tv", "UkraineNow", "ssternenko",
        "SolovievLive", "bazabazon", "grey_zone", "sashakots", "boris_rozhin",
        "intelslava", "militarysummary", "AuroraIntel", "rbc_news", "tass_agency",
        "ria_novosti", "rt_russian", "readovkanews", "breakingmash",
        *CANALES_VIGILADOS,
    ]))

    canales_yt_handles = [
        ("DWNews", "YouTube: DW News"),
        ("kyivindependent", "YouTube: Kyiv Independent"),
        ("Bellingcat", "YouTube: Bellingcat"),
        ("meduzaio", "YouTube: Meduza"),
        ("RFERL", "YouTube: RFE/RL"),
        ("TheMoscowTimes", "YouTube: Moscow Times"),
        ("WarTranslated", "YouTube: War Translated"),
        ("euronews", "YouTube: Euronews"),
        ("DWEspanol", "YouTube: DW Español"),
        ("rtve", "YouTube: RTVE"),
        ("FRANCE24Espanol", "YouTube: France 24 Español"),
    ]
    mastodon_tags = [
        ("mastodon.social", tag)
        for tag in (
            "sabotage", "espionage", "disinformation", "hybridwar", "cyberattack",
            "russia", "china", "osint", "ukraine", "warcrimes", "sanctions",
            "spamouflage", "apt28", "apt29", "volttyphoon", "shadowfleet",
            "fimi", "kremlin", "nato", "drones", "ciberseguridad",
            "desinformacion", "espionaje", "rusia",
        )
    ] + [
        ("infosec.exchange", tag)
        for tag in ("russia", "china", "apt", "ransomware", "cyberespionage", "ddos", "threatintel")
    ]

    fuentes_rss = [
        # ESPAÑA: PRENSA, SEGURIDAD, CIBERDEFENSA Y TRAMAS VINCULADAS AL EJE HOSTIL
        ("https://news.google.com/rss/search?q=(site:larazon.es+OR+site:elmundo.es+OR+site:elpais.com+OR+site:abc.es+OR+site:elconfidencial.com+OR+site:elespanol.com+OR+site:theobjective.com+OR+site:vozpopuli.com)+(Rusia+OR+Ucrania+OR+Putin+OR+Kremlin+OR+China)+(drones+OR+sabotaje+OR+espionaje+OR+injerencia+OR+\"Audiencia+Nacional\")&hl=es&gl=ES&ceid=ES:es", "Prensa Nacional Seguridad"),
        ("https://news.google.com/rss/search?q=(INCIBE+OR+\"CCN-CERT\"+OR+DSN+OR+\"Seguridad+Nacional\")+España+(Rusia+OR+China+OR+Kremlin)+(ciberataque+OR+sabotaje+OR+amenaza)&hl=es&gl=ES&ceid=ES:es", "España: Ciberseguridad / DSN"),
        ("https://news.google.com/rss/search?q=(\"Guardia+Civil\"+OR+\"Policia+Nacional\"+OR+\"Audiencia+Nacional\")+(espionaje+OR+sabotaje+OR+\"trama+rusa\"+OR+\"Vor+v+zakone\"+OR+blanqueo)+España+(Rusia+OR+Kremlin)&hl=es&gl=ES&ceid=ES:es", "España: FCSE / Causa Judicial"),
        ("https://news.google.com/rss/search?q=España+(\"injerencia+rusa\"+OR+\"ciberataque+ruso\"+OR+\"espionaje+ruso\"+OR+\"sabotaje+ruso\"+OR+\"cables+submarinos\")+(Rusia+OR+Putin)&hl=es&gl=ES&ceid=ES:es", "España: Injerencia y Sabotaje"),

        # AGENCIAS DE INTELIGENCIA
        ("https://news.google.com/rss/search?q=(\"CIA\"+OR+\"CNI\"+OR+\"MI6\"+OR+\"MI5\"+OR+\"BND\"+OR+\"DGSI\")+alerta+(\"Rusia\"+OR+\"China\"+OR+\"drones\"+OR+\"sabotaje\"+OR+\"ataque+ruso\"+OR+\"espionaje\")&hl=es&gl=ES&ceid=ES:es", "Agencias Inteligencia (ES)"),
        ("https://news.google.com/rss/search?q=(CIA+OR+\"MI6\"+OR+\"MI5\"+OR+BND)+warning+(Russia+OR+China+OR+sabotage+OR+drones+OR+espionage)&hl=en-US&gl=US&ceid=US:en", "Intel Agencies Warnings (EN)"),
        
        # VOR V ZAKONE / LADRONES EN LEY / MAFIA RUSA
        ("https://news.google.com/rss/search?q=%22Vor+v+zakone%22+OR+%22ladrones+en+ley%22+OR+%22ladr%C3%B3n+en+ley%22+OR+%22mafia+rusa%22&hl=es&gl=ES&ceid=ES:es", "Vor v Zakone / Ladrones en Ley"),
        ("https://news.google.com/rss/search?q=%22thief+in+law%22+OR+%22thieves+in+law%22+OR+%22Vor+v+zakone%22+OR+%22Russian+mafia%22&hl=en-US&gl=US&ceid=US:en", "Thieves in Law / Mafia (EN)"),
        ("https://news.google.com/rss/search?q=(%22Vor+v+zakone%22+OR+%22mafia+rusa%22+OR+%22ladrones+en+ley%22)+(detenido+OR+arrestado+OR+Polic%C3%ADa+OR+%22Guardia+Civil%22)&hl=es&gl=ES&ceid=ES:es", "Operaciones Policiales Vor"),
        ("https://news.google.com/rss/search?q=%22%D0%B2%D0%BE%D1%80+%D0%B2+%D0%B7%D0%B0%D0%BA%D0%BE%D0%BD%D0%B5%22+OR+%22%D1%80%D1%83%D1%81%D1%81%D0%BA%D0%B0%D1%8F+%D0%BC%D0%B0%D1%84%D0%B8%D1%8F%22&hl=ru&gl=RU&ceid=RU:ru", "Vor v Zakone (RU)"),

        # DETENCIONES INTERNACIONALES (POLONIA, UCRANIA, RUSIA)
        ("https://news.google.com/rss/search?q=(ABW+OR+Polska)+(zatrzymany+OR+aresztowany)+(szpieg+OR+dywersja+OR+Rosja)&hl=pl&gl=PL&ceid=PL:pl", "Polonia: Detenciones ABW"),
        ("https://news.google.com/rss/search?q=(СБУ+OR+Україна)+(затримано+OR+арештовано)+(агент+OR+шпигун+OR+диверсант)&hl=uk&gl=UA&ceid=UA:uk", "Ucrania: Detenciones SBU"),
        ("https://news.google.com/rss/search?q=(ФСБ+OR+Россия)+(задержан+OR+арестован)+(шпионаж+OR+диверсия+OR+госизмена)&hl=ru&gl=RU&ceid=RU:ru", "Rusia: Detenciones FSB"),

        # CRÍMENES DE GUERRA (GRANO, SILOS, GASODUCTOS, ECOCIDIO)
        ("https://news.google.com/rss/search?q=(\"war+crimes\"+OR+\"crímenes+de+guerra\"+OR+ICC+OR+CPI+OR+\"robo+de+grano\"+OR+\"silos+de+grano\"+OR+ecocidio+OR+\"gasoducto\")+(Russia+OR+Rusia+OR+Putin+OR+Ucrania)&hl=es&gl=ES&ceid=ES:es", "Crímenes / Grano / CPI"),
        ("https://news.google.com/rss/search?q=(Russia+OR+Rusia)+(\"targeted+killing\"+OR+\"asesinato+selectivo\"+OR+sicario+OR+envenenamiento+OR+arson+OR+sabotaje)&hl=es&gl=ES&ceid=ES:es", "Operaciones Encubiertas"),

        # EMPRESAS ESPAÑOLAS DE DEFENSA Y AMENAZAS (OESÍA/ODESIA, DESTINUS, INDRA, ETC.)
        ("https://news.google.com/rss/search?q=(\"Grupo+Oesia\"+OR+\"Oesia\"+OR+\"Odesia\"+OR+\"UAV+Navigation\"+OR+\"Tecnobit\"+OR+\"Destinus\"+OR+\"Kokorich\"+OR+\"Indra\"+OR+\"Navantia\")+(Rusia+OR+China+OR+amenaza+OR+drones+OR+ciberataque+OR+defensa)&hl=es&gl=ES&ceid=ES:es", "Empresas Defensa ES"),
        ("https://news.google.com/rss/search?q=site:infodefensa.com+(Rusia+OR+China+OR+amenaza+OR+ciberataque+OR+sabotaje+OR+espionaje+OR+Moscú)&hl=es&gl=ES&ceid=ES:es", "Infodefensa Amenazas"),
        ("https://news.google.com/rss/search?q=(\"Mikhail+Kokorich\"+OR+\"Kokorich\"+OR+\"Destinus\")+(drones+OR+Rusia+OR+Ucrania+OR+defensa+OR+amenaza)&hl=es&gl=ES&ceid=ES:es", "Destinus / Kokorich"),

        # SABOTAJES E HÍBRIDAS EN EUROPA Y OTAN
        ("https://news.google.com/rss/search?q=(sabotage+OR+arson+OR+\"undersea+cable\"+OR+espionage+OR+\"hybrid+threat\")+(Russia+OR+GRU+OR+FSB)+(Europe+OR+Poland+OR+Germany+OR+Baltics+OR+France+OR+UK)&hl=en-US&gl=US&ceid=US:en", "Sabotaje e Híbridas Europa (EN)"),
        ("https://news.google.com/rss/search?q=(BfV+OR+BND+OR+DGSI+OR+ABW+OR+KAPO)+(Russia+OR+spies+OR+sabotage+OR+espionage)&hl=en-US&gl=US&ceid=US:en", "Servicios Inteligencia UE (EN)"),
        ("https://news.google.com/rss/search?q=(sabotaje+OR+\"infraestructura+crítica\"+OR+\"cables+submarinos\")+(Rusia+OR+China)+(Europa+OR+OTAN)&hl=es&gl=ES&ceid=ES:es", "Sabotajes e Infraestructuras (Global)"),

        # CHINA E INJERENCIA ESTRATÉGICA
        ("https://news.google.com/rss/search?q=(China+OR+Pekín+OR+Beijing)+(espionaje+OR+espías+OR+\"guerra+híbrida\"+OR+sabotaje+OR+\"comisarías+secretas\"+OR+MSS+OR+injerencia)&hl=es&gl=ES&ceid=ES:es", "China Espionaje / Híbrida (ES)"),
        ("https://news.google.com/rss/search?q=(China+OR+Beijing)+(espionage+OR+spies+OR+\"hybrid+warfare\"+OR+sabotage+OR+MSS)&hl=en-US&gl=US&ceid=US:en", "China Intel / Hybrid (EN)"),

        # SANCIONES, FLOTA FANTASMA Y FININT
        ("https://news.google.com/rss/search?q=(\"shadow+fleet\"+OR+\"flota+fantasma\"+OR+\"dark+fleet\"+OR+\"petrolero+clandestino\")+(Russia+OR+Rusia)&hl=es&gl=ES&ceid=ES:es", "Sanciones / Flota Fantasma"),
        ("https://news.google.com/rss/search?q=(criptomonedas+OR+bitcoin+OR+USDT+OR+Tether+OR+Garantex)+(Rusia+OR+Kremlin+OR+OFAC+OR+Garantex+OR+Yuzuk)+(sanciones+OR+blanqueo+OR+evasion+OR+ilicitos)&hl=es&gl=ES&ceid=ES:es", "Cripto Sanciones y Evasión (ES)"),
        ("https://news.google.com/rss/search?q=(crypto+OR+Tether+OR+USDT+OR+Bitcoin+OR+Garantex)+(Russia+OR+Kremlin+OR+OFAC+OR+Garantex)+(sanctions+OR+illicit+OR+evasion)&hl=en-US&gl=US&ceid=US:en", "Crypto Sanctions FININT (EN)"),

        # DRONES Y GUERRA AÉREA
        ("https://news.google.com/rss/search?q=(Shahed+OR+Geran+OR+\"drones+kamikaze\"+OR+\"FPV+drones\"+OR+\"drones+pirata\"+OR+\"bloqueo+del+mar+negro\")+(Ucrania+OR+Rusia+OR+OTAN)&hl=es&gl=ES&ceid=ES:es", "Drones Conflicto (ES)"),
        ("https://news.google.com/rss/search?q=(drone+strike+OR Shahed+OR Lancet+OR \"pirate+drones\"+OR \"black+sea+blockade\")+(Ukraine+OR Russia+OR NATO)&hl=en-US&gl=US&ceid=US:en", "Drone Warfare (EN)"),

        # ALERTA MUNDO ÁRABE (FUENTES EN ÁRABE DE SABOTAJES Y ESPIONAJE DEL EJE)
        ("https://news.google.com/rss/search?q=(%D8%B1%D9%88%D8%B3%D9%8A%D8%A7+OR+%D8%A8%D9%88%D8%AA%D9%8A%D9%86)+(%D8%AA%D8%AC%D8%B3%D8%B3+OR+%D8%AA%D8%AE%D8%B1%D9%8A%D8%A8+OR+%D8%B7%D8%A7%D8%A6%D8%B1%D8%A9+%D9%85%D8%B3%D9%8A%D8%B1%D8%A9)&hl=ar&gl=AE&ceid=AE:ar", "Prensa Árabe (AR)"),
        ("https://news.google.com/rss/search?q=(%D8%B1%D9%88%D8%B3%D9%8A%D8%A7)+%D8%A7%D9%84%D9%86%D8%A7%D8%AA%D9%88&hl=ar&gl=AE&ceid=AE:ar", "OTAN vs Rusia (AR)"),

        # FUENTES Y THINK TANKS VERIFICADOS
        ("https://theins.ru/feed", "The Insider (RU/EN)"),
        ("https://news.google.com/rss/search?q=(\"Institute+for+the+Study+of+War\"+OR+\"ISW\")+Russian+offensive&hl=en-US&gl=US&ceid=US:en", "ISW War Studies (EN)"),
        ("https://news.google.com/rss/search?q=(\"Anatolii+Sharij\"+OR+\"Anatoli+Sharij\"+OR+\"Anatoly+Shariy\"+OR+\"Saharij\"+OR+\"Анатолий+Шарий\"+OR+\"Анатолій+Шарій\")&hl=es&gl=ES&ceid=ES:es", "Global: Anatolii Sharij (Multilingüe)"),
        ("https://news.google.com/rss/search?q=(\"Operacion+Yuzuk\"+OR+\"Operación+Yuzuk\"+OR+\"caso+Yuzuk\")&hl=es&gl=ES&ceid=ES:es", "Guardia Civil: Operación Yuzuk")
    ]

    fuentes_rss.extend(feeds_multilingues())
    fuentes_rss.extend(feeds_espana())
    fuentes_rss.extend(feeds_empresas())
    fuentes_rss.extend(feeds_sharij())
    fuentes_rss.extend(feeds_runews24())
    fuentes_rss.extend(feeds_perfiles())

    todos_brutos = []
    with ThreadPoolExecutor(max_workers=24) as ex, ThreadPoolExecutor(
        max_workers=6
    ) as tg_ex:
        f_emp = ex.submit(raspar_euromaidanpress)
        f_rum = ex.submit(raspar_rumafia)
        f_ant = ex.submit(raspar_antikor)
        f_runews = ex.submit(raspar_runews24)
        f_yt = [ex.submit(raspar_youtube_canal, cid, tag) for cid, tag in canales_yt]
        f_yt_handles = [ex.submit(raspar_youtube_handle, handle, tag) for handle, tag in canales_yt_handles]
        f_mastodon = [ex.submit(raspar_mastodon_tag, instancia, tag) for instancia, tag in mastodon_tags]
        f_tg = [tg_ex.submit(raspar_un_canal_tg, c) for c in canales_tg]
        f_rss = [ex.submit(procesar_un_feed_rss, url_tag) for url_tag in fuentes_rss]

        tareas = [
            (f_emp, "Euromaidan Press"),
            (f_rum, "RuMafia (Web)"),
            (f_ant, "Antikor (Web)"),
            (f_runews, "RuNews24 (RU)"),
        ]
        tareas.extend(zip(f_yt, [t for _, t in canales_yt]))
        tareas.extend(zip(f_yt_handles, [t for _, t in canales_yt_handles]))
        tareas.extend(
            (future, f"Mastodon #{tag} ({instancia})")
            for future, (instancia, tag) in zip(f_mastodon, mastodon_tags)
        )
        tareas.extend(zip(f_tg, [f"Telegram @{c}" for c in canales_tg]))
        tareas.extend(zip(f_rss, [t for _, t in fuentes_rss]))

        for fut, nom in tareas:
            try:
                res_items, err_msg = fut.result()
                todos_brutos.extend(res_items)
                telemetria_fuentes.append({
                    "Fuente": nom,
                    "Estado": "⚠️ Demora / Sin datos" if err_msg else "✅ Conectado",
                    "Alertas": len(res_items),
                    "Fechado": "Fecha del artículo" if any(not i.get("fecha_estimada") for i in res_items) else "Estimada / Reciente"
                })
            except Exception:
                telemetria_fuentes.append({
                    "Fuente": nom,
                    "Estado": "❌ Fallo de respuesta",
                    "Alertas": 0,
                    "Fechado": "No disponible"
                })

    noticias_relevantes = []
    for item in todos_brutos:
        titular = item["titular_raw"]
        cuerpo = item["cuerpo_raw"]
        categoria = categorizar_noticia(
            titular, cuerpo, item["plataforma"], item["canal"]
        )
        coincidencia = coincidencia_personalizada(
            titular, cuerpo, diccionario_personalizado
        )
        perfiles = perfiles_en(f"{titular} {cuerpo[:600]}", item["canal"])
        if perfiles and item["plataforma"] == "TELEGRAM" and perfil_de_canal(item["canal"]):
            categoria = "REDES"
        elif perfiles and item["plataforma"] == "PRENSA":
            categoria = "GLOBAL"
        item["_perfiles"] = perfiles
        if categoria in ("TELEGRAM", "REDES"):
            coincidencia = None
        else:
            categoria = aplicar_categoria_personalizada(
                categoria, coincidencia, f"{titular} {cuerpo}"
            )
        if not categoria or categoria == "DESCARTE":
            continue
        item["_categoria_clasificada"] = categoria
        item["_coincidencia_clasificada"] = coincidencia
        noticias_relevantes.append(item)

    todos_brutos = sorted(
        noticias_relevantes,
        key=lambda x: x["fecha_dt"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    del todos_brutos[5000:]

    # AGRUPACIÓN DE NOTICIAS SIMILARES EN DESPLEGABLE
    pre_unicos, urls_vistas, indice_titulares = [], set(), {}

    for b in todos_brutos:
        u = limpiar_url(b["enlace"])
        if u and u in urls_vistas: continue

        tit_norm = normalizar_texto(b["titular_raw"])
        tokens = sorted(_tokens_titular(tit_norm), key=len, reverse=True)[:6]
        cuentas = {}
        for token in tokens:
            posiciones = indice_titulares.get(token, ())
            if len(posiciones) > 250:
                continue
            for posicion in posiciones:
                cuentas[posicion] = cuentas.get(posicion, 0) + 1

        coincidente = None
        candidatos = sorted(cuentas.items(), key=lambda par: par[1], reverse=True)[:8]
        for posicion, coincidencias in candidatos:
            if coincidencias >= 3 and len(tokens) >= 3:
                coincidente = pre_unicos[posicion]
                break
            if coincidencias >= 2:
                existente = pre_unicos[posicion]
                ex_norm = normalizar_texto(existente["titular_raw"])
                if SequenceMatcher(None, tit_norm[:75], ex_norm[:75]).ratio() >= 0.65:
                    coincidente = existente
                    break

        if coincidente:
            sec = coincidente.setdefault("fuentes_coincidentes", [])
            if not any(f["enlace"] == b["enlace"] for f in sec) and b["enlace"] != coincidente["enlace"]:
                sec.append({
                    "canal": b.get("fuente_nombre", b["canal"]),
                    "plataforma": b["plataforma"],
                    "enlace": b["enlace"], 
                    "titular": b["titular_raw"],
                    "fecha_dt": b["fecha_dt"]
                })
            continue

        if u: urls_vistas.add(u)
        b.setdefault("fuentes_coincidentes", [])
        b.setdefault("fuente_nombre", b["canal"])
        posicion_nueva = len(pre_unicos)
        pre_unicos.append(b)
        for token in tokens:
            indice_titulares.setdefault(token, []).append(posicion_nueva)

    alertas_finales = []
    for idx, item in enumerate(pre_unicos):
        plat = item["plataforma"]
        tit_raw = item["titular_raw"]
        cuerpo_raw = item["cuerpo_raw"]
        canal_clean = item["canal"].replace("@", "").upper()

        cat_final = item["_categoria_clasificada"]
        coincidencia = item["_coincidencia_clasificada"]

        unique_id = f"{plat[:3]}_{idx}_{id_determinista(item['enlace'] + tit_raw)}"
        nombres_fuentes = [item.get("fuente_nombre", item["canal"])]
        nombres_fuentes.extend(f.get("canal", "") for f in item.get("fuentes_coincidentes", []))
        fuentes_detectadas = []
        fuentes_norm = set()
        for nombre_fuente in nombres_fuentes:
            nombre_limpio = str(nombre_fuente).strip()
            clave_fuente = normalizar_texto(nombre_limpio)
            if nombre_limpio and clave_fuente not in fuentes_norm:
                fuentes_norm.add(clave_fuente)
                fuentes_detectadas.append(nombre_limpio)

        contexto = generar_contexto_trazabilidad(cat_final, canal=item["canal"])
        if coincidencia:
            contexto += (
                f" Clasificación por término personalizado ({coincidencia['idioma']}): "
                f"{coincidencia['coincidencia']}."
            )

        canales_sociales = {
            normalizar_texto(str(f.get("canal", ""))) for f in item.get("fuentes_coincidentes", [])
            if f.get("plataforma") in ("TELEGRAM", "REDES")
        }
        if plat in ("TELEGRAM", "REDES"):
            canales_sociales.add(normalizar_texto(str(item.get("fuente_nombre", item["canal"]))))

        alertas_finales.append({
            "id": unique_id, "plataforma": plat, "canal": item["canal"],
            "num_canales_sociales": len(canales_sociales),
            "fuentes_coincidentes": item.get("fuentes_coincidentes", []),
            "fuentes_detectadas": fuentes_detectadas,
            "num_fuentes": len(fuentes_detectadas),
            "impacto_potencial": bool(PATRON_IMPACTO_MULTILINGUE.search(normalizar_texto(f"{tit_raw} {cuerpo_raw}"))),
            "fecha_dt": item["fecha_dt"],
            "fecha_estimada": item.get("fecha_estimada", False),
            "titular_raw_limpio": tit_raw,
            "titular": f"[{canal_clean}] {tit_raw}" if plat == "TELEGRAM" else tit_raw,
            "cuerpo": cuerpo_raw,
            "categoria": cat_final,
            "perfiles": item.get("_perfiles", []),
            "coincidencia_personalizada": coincidencia["coincidencia"] if coincidencia else None,
            "etiquetas_ner": extraer_entidades_clave(f"{tit_raw} {cuerpo_raw}"),
            "evaluacion_contexto": contexto,
            "multimedia": item.get("multimedia"), "tiene_video": item.get("tiene_video", False), "enlace": item["enlace"]
        })

    return sorted(alertas_finales, key=lambda x: x["fecha_dt"] if x["fecha_dt"] else datetime.min.replace(tzinfo=timezone.utc), reverse=True), telemetria_fuentes
