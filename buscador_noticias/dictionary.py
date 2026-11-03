import json
import os
import re
import tempfile
from pathlib import Path

from .config import SECCIONES_INFORME
from .processing import normalizar_texto
from .translator import IDIOMAS_TRADUCCION


CATEGORIAS_VALIDAS = {codigo for codigo, _, _ in SECCIONES_INFORME}
IDIOMAS_TRADUCCION_VALIDOS = set(IDIOMAS_TRADUCCION.values()) | {"zh"}


def ruta_diccionario_personalizado(usuario=None):
    from .almacen import carpeta_usuario
    return carpeta_usuario(usuario) / "diccionario_personalizado.json"


def validar_entrada(termino, categoria, traducciones=None):
    termino = str(termino).strip()
    if not termino:
        raise ValueError("Escribe una palabra o expresión.")
    if len(termino) > 100:
        raise ValueError("La palabra o expresión no puede superar los 100 caracteres.")
    if not normalizar_texto(termino).strip():
        raise ValueError("La palabra o expresión no es válida.")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValueError("Selecciona una categoría válida.")
    traducciones_limpias = []
    codigos_vistos = set()
    for traduccion in traducciones or []:
        if not isinstance(traduccion, dict):
            raise ValueError("El diccionario contiene una traducción inválida.")
        idioma = str(traduccion.get("idioma", "")).strip()
        codigo = str(traduccion.get("codigo", "")).strip()
        texto = str(traduccion.get("texto", "")).strip()
        if codigo not in IDIOMAS_TRADUCCION_VALIDOS or not idioma or not texto:
            raise ValueError("El diccionario contiene una traducción incompleta o no admitida.")
        if codigo in codigos_vistos:
            raise ValueError("El diccionario contiene idiomas de traducción duplicados.")
        codigos_vistos.add(codigo)
        traducciones_limpias.append({"idioma": idioma, "codigo": codigo, "texto": texto})
    return {
        "termino": termino,
        "categoria": categoria,
        "traducciones": traducciones_limpias,
    }


def cargar_diccionario_personalizado(usuario=None):
    path = ruta_diccionario_personalizado(usuario)
    try:
        contenido = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise OSError(f"No se pudo leer el diccionario personalizado: {exc}") from exc

    try:
        datos = json.loads(contenido)
    except json.JSONDecodeError as exc:
        raise ValueError(f"El archivo del diccionario no contiene JSON válido: {path}") from exc

    if not isinstance(datos, list):
        raise ValueError(f"El formato del diccionario debe ser una lista: {path}")

    entradas = []
    vistos = set()
    for entrada in datos:
        if not isinstance(entrada, dict):
            raise ValueError(f"El diccionario contiene una entrada inválida: {path}")
        limpia = validar_entrada(
            entrada.get("termino", ""),
            entrada.get("categoria"),
            entrada.get("traducciones", []),
        )
        clave = normalizar_texto(limpia["termino"]).strip()
        if clave in vistos:
            raise ValueError(f"El diccionario contiene términos duplicados: {path}")
        vistos.add(clave)
        entradas.append(limpia)
    return entradas


def cargar_diccionario_efectivo(usuario=None):
    """Diccionario compartido del grupo del usuario (si lo hay) más el propio; el propio gana en duplicados."""
    from . import usuarios
    propias = cargar_diccionario_personalizado(usuario)
    grupo = usuarios.grupo_de(usuario) if usuario else ""
    if not grupo:
        return propias
    vistas = {normalizar_texto(e["termino"]).strip() for e in propias}
    comunes = [
        e for e in cargar_diccionario_personalizado(f"grupo:{grupo}")
        if normalizar_texto(e["termino"]).strip() not in vistas
    ]
    return propias + comunes


def agregar_termino_personalizado(termino, categoria, traducciones=None, usuario=None):
    entrada_nueva = validar_entrada(termino, categoria, traducciones)
    entradas = cargar_diccionario_personalizado(usuario)
    clave_nueva = normalizar_texto(entrada_nueva["termino"]).strip()
    if any(normalizar_texto(entrada["termino"]).strip() == clave_nueva for entrada in entradas):
        raise ValueError("Esa palabra o expresión ya está en el diccionario.")

    entradas.append(entrada_nueva)
    path = ruta_diccionario_personalizado(usuario)
    path.parent.mkdir(parents=True, exist_ok=True)
    archivo_temporal = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            delete=False
        ) as temporal:
            json.dump(entradas, temporal, ensure_ascii=False, indent=2)
            temporal.write("\n")
            temporal.flush()
            os.fsync(temporal.fileno())
            archivo_temporal = Path(temporal.name)
        archivo_temporal.replace(path)
    except OSError:
        if archivo_temporal and archivo_temporal.exists():
            archivo_temporal.unlink()
        raise
    return entradas


def coincidencia_personalizada(titular, cuerpo, entradas):
    corpus = normalizar_texto(f"{titular} {cuerpo}")
    coincidencias = []
    for posicion, entrada in enumerate(entradas):
        variantes = [(entrada["termino"], "original")]
        variantes.extend(
            (traduccion["texto"], traduccion["idioma"])
            for traduccion in entrada.get("traducciones", [])
        )
        for variante, idioma in variantes:
            termino = normalizar_texto(variante).strip()
            patron = re.compile(r"(?<!\w)" + re.escape(termino) + r"(?!\w)")
            if termino and patron.search(corpus):
                coincidencias.append((len(termino), -posicion, entrada, variante, idioma))
    if not coincidencias:
        return None
    _, _, seleccionada, variante, idioma = max(
        coincidencias,
        key=lambda coincidencia: coincidencia[:2],
    )
    return {
        "termino": seleccionada["termino"],
        "categoria": seleccionada["categoria"],
        "coincidencia": variante,
        "idioma": idioma,
    }
