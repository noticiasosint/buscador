"""Usuarios con clave propia, rol y preferencias (secciones visibles y temas propios).

El usuario «admin» siempre existe: su clave es GAD_PASSWORD (o la que fije desde la app) y conserva
los ficheros de datos de siempre. El resto de usuarios los crea y borra el administrador.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
import threading

from .almacen import carpeta_base

ADMIN = "admin"
ROLES = ("admin", "usuario")
ITERACIONES = 200_000
MAX_USUARIOS = 100
MAX_TEMAS = 20
MAX_PALABRAS = 30
_BLOQUEO = threading.RLock()
_NOMBRE = re.compile(r"[a-z0-9_.-]{2,30}")


def ruta_usuarios():
    if os.environ.get("GAD_USUARIOS"):
        from pathlib import Path
        return Path(os.environ["GAD_USUARIOS"])
    return carpeta_base() / "usuarios.json"


def _vacio():
    return {"usuarios": {}, "prefs": {}, "perfiles": {}, "grupos": {}}


def _cargar():
    try:
        datos = json.loads(ruta_usuarios().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _vacio()
    if not isinstance(datos, dict):
        return _vacio()
    return {
        "usuarios": datos["usuarios"] if isinstance(datos.get("usuarios"), dict) else {},
        "prefs": datos["prefs"] if isinstance(datos.get("prefs"), dict) else {},
        "perfiles": datos["perfiles"] if isinstance(datos.get("perfiles"), dict) else {},
        "grupos": datos["grupos"] if isinstance(datos.get("grupos"), dict) else {},
    }


def _guardar(datos):
    ruta = ruta_usuarios()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
        os.replace(tmp, ruta)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _hash(clave, sal):
    return hashlib.pbkdf2_hmac("sha256", str(clave).encode(), bytes.fromhex(sal), ITERACIONES).hex()


def _registro(clave):
    sal = secrets.token_hex(16)
    return {"sal": sal, "hash": _hash(clave, sal)}


def normalizar_nombre(nombre):
    nombre = str(nombre).strip().lower()
    if not _NOMBRE.fullmatch(nombre):
        raise ValueError("El usuario debe tener 2-30 caracteres: letras, números, punto, guion o guion bajo.")
    return nombre


def _validar_clave(clave):
    if len(str(clave)) < 6:
        raise ValueError("La clave debe tener al menos 6 caracteres.")
    if len(str(clave)) > 200:
        raise ValueError("La clave es demasiado larga.")


def clave_admin_por_defecto():
    clave = os.environ.get("GAD_PASSWORD")
    if not clave:
        raise ValueError("Configura GAD_PASSWORD antes de autenticar al administrador.")
    return clave


def autenticar(nombre, clave, clave_admin=None):
    """Devuelve {'usuario', 'rol'} si las credenciales son válidas; si no, None."""
    try:
        nombre = normalizar_nombre(nombre)
    except ValueError:
        return None
    registro = _cargar()["usuarios"].get(nombre)
    if registro is None:
        if nombre != ADMIN:
            return None
        esperado = clave_admin if clave_admin is not None else clave_admin_por_defecto()
        ok = hmac.compare_digest(str(clave).encode(), str(esperado).encode())
        return {"usuario": ADMIN, "rol": "admin"} if ok else None
    try:
        ok = hmac.compare_digest(_hash(clave, registro["sal"]), registro["hash"])
    except (KeyError, ValueError, TypeError):
        return None
    if not ok:
        return None
    rol = "admin" if nombre == ADMIN or registro.get("rol") == "admin" else "usuario"
    return {"usuario": nombre, "rol": rol}


def existe(nombre):
    return nombre == ADMIN or nombre in _cargar()["usuarios"]


def rol_de(nombre):
    if nombre == ADMIN:
        return "admin"
    registro = _cargar()["usuarios"].get(nombre)
    return "admin" if registro and registro.get("rol") == "admin" else "usuario"


def listar():
    datos = _cargar()["usuarios"]
    lista = [{"usuario": ADMIN, "rol": "admin"}]
    lista += [
        {"usuario": n, "rol": "admin" if r.get("rol") == "admin" else "usuario"}
        for n, r in sorted(datos.items()) if n != ADMIN
    ]
    perfiles = _cargar()["perfiles"]
    for u in lista:
        p = perfiles.get(u["usuario"]) or {}
        u["grupo"] = p.get("grupo") or ""
        u["correo"] = p.get("correo") or ""
    return lista


def crear(nombre, clave, rol="usuario"):
    nombre = normalizar_nombre(nombre)
    _validar_clave(clave)
    if rol not in ROLES:
        raise ValueError("Rol no válido.")
    with _BLOQUEO:
        datos = _cargar()
        if nombre == ADMIN or nombre in datos["usuarios"]:
            raise ValueError("Ese usuario ya existe.")
        if len(datos["usuarios"]) >= MAX_USUARIOS:
            raise ValueError(f"Máximo {MAX_USUARIOS} usuarios.")
        datos["usuarios"][nombre] = {**_registro(clave), "rol": rol}
        _guardar(datos)
    return listar()


def cambiar_clave(nombre, clave):
    nombre = normalizar_nombre(nombre)
    _validar_clave(clave)
    with _BLOQUEO:
        datos = _cargar()
        if nombre != ADMIN and nombre not in datos["usuarios"]:
            raise ValueError("El usuario no existe.")
        rol = "admin" if nombre == ADMIN else datos["usuarios"][nombre].get("rol", "usuario")
        datos["usuarios"][nombre] = {**_registro(clave), "rol": rol}
        _guardar(datos)


def borrar(nombre):
    nombre = normalizar_nombre(nombre)
    if nombre == ADMIN:
        raise ValueError("No se puede borrar al administrador.")
    with _BLOQUEO:
        datos = _cargar()
        if nombre not in datos["usuarios"]:
            raise ValueError("El usuario no existe.")
        del datos["usuarios"][nombre]
        datos["prefs"].pop(nombre, None)
        datos["perfiles"].pop(nombre, None)
        _guardar(datos)
    return listar()


def _limpiar_temas(temas):
    limpios = []
    for tema in temas or []:
        if not isinstance(tema, dict):
            continue
        nombre = re.sub(r"\s+", " ", str(tema.get("nombre", ""))).strip()[:40]
        palabras = []
        for p in tema.get("palabras", []):
            p = re.sub(r"\s+", " ", str(p)).strip()[:60]
            if p and p.lower() not in [x.lower() for x in palabras]:
                palabras.append(p)
        if nombre and palabras and nombre.lower() not in [t["nombre"].lower() for t in limpios]:
            limpios.append({"nombre": nombre, "palabras": palabras[:MAX_PALABRAS]})
    return limpios[:MAX_TEMAS]


def preferencias(nombre, codigos_validos=None):
    """{'secciones': [codigos] | None (todas), 'temas': [{'nombre', 'palabras'}]}"""
    p = _cargar()["prefs"].get(nombre) or {}
    secciones = p.get("secciones")
    if isinstance(secciones, list):
        secciones = list(dict.fromkeys("GLOBAL" if s == "SHARIJ" else s for s in secciones))
        secciones = [s for s in secciones if codigos_validos is None or s in codigos_validos]
    else:
        secciones = None
    grupo = grupo_de(nombre)
    temas_grupo = _limpiar_temas((_cargar()["grupos"].get(grupo) or {}).get("temas")) if grupo else []
    return {"secciones": secciones, "temas": _limpiar_temas(p.get("temas")), "grupo": grupo, "temas_grupo": temas_grupo}


def guardar_preferencias(nombre, secciones=None, temas=None, codigos_validos=None):
    if not existe(nombre):
        raise ValueError("El usuario no existe.")
    if secciones is not None:
        secciones = [str(s) for s in secciones if codigos_validos is None or s in codigos_validos]
        if not secciones:
            raise ValueError("Elige al menos una sección visible.")
    with _BLOQUEO:
        datos = _cargar()
        actual = datos["prefs"].get(nombre) or {}
        actual["secciones"] = secciones
        if temas is not None:
            actual["temas"] = _limpiar_temas(temas)
        datos["prefs"][nombre] = actual
        _guardar(datos)
    return preferencias(nombre, codigos_validos)


def guardar_temas(nombre, temas):
    if not existe(nombre):
        raise ValueError("El usuario no existe.")
    with _BLOQUEO:
        datos = _cargar()
        actual = datos["prefs"].get(nombre) or {}
        actual["temas"] = _limpiar_temas(temas)
        datos["prefs"][nombre] = actual
        _guardar(datos)
    return actual["temas"]


MAX_GRUPOS = 50
_CORREO = re.compile(r"[^@\s,;]{1,64}@[^@\s,;]{1,190}\.[^@\s,;]{2,20}")


def grupo_de(nombre):
    """Grupo al que pertenece el usuario ('' si ninguno o si el grupo ya no existe)."""
    datos = _cargar()
    g = (datos["perfiles"].get(nombre) or {}).get("grupo") or ""
    return g if g in datos["grupos"] else ""


def listar_grupos():
    datos = _cargar()
    return [
        {"grupo": g, "miembros": sorted(n for n, p in datos["perfiles"].items() if (p or {}).get("grupo") == g and (n == ADMIN or n in datos["usuarios"]))}
        for g in sorted(datos["grupos"])
    ]


def crear_grupo(nombre):
    nombre = normalizar_nombre(nombre)
    with _BLOQUEO:
        datos = _cargar()
        if nombre in datos["grupos"]:
            raise ValueError("Ese grupo ya existe.")
        if len(datos["grupos"]) >= MAX_GRUPOS:
            raise ValueError(f"Máximo {MAX_GRUPOS} grupos.")
        datos["grupos"][nombre] = {"temas": []}
        _guardar(datos)
    return listar_grupos()


def borrar_grupo(nombre):
    """Quita el grupo y deja a sus miembros sin grupo (el diccionario compartido se conserva en disco)."""
    with _BLOQUEO:
        datos = _cargar()
        if nombre not in datos["grupos"]:
            raise ValueError("El grupo no existe.")
        del datos["grupos"][nombre]
        for p in datos["perfiles"].values():
            if isinstance(p, dict) and p.get("grupo") == nombre:
                p["grupo"] = ""
        _guardar(datos)
    return listar_grupos()


def meter_en_grupo(usuario, grupo):
    """Asigna el usuario al grupo, creándolo si no existe."""
    if not existe(usuario):
        raise ValueError("El usuario no existe.")
    grupo = normalizar_nombre(grupo)
    if grupo not in {g["grupo"] for g in listar_grupos()}:
        crear_grupo(grupo)
    return asignar_grupo(usuario, grupo)


def asignar_grupo(usuario, grupo):
    """Asigna el usuario a un grupo ('' o None para quitarlo)."""
    if not existe(usuario):
        raise ValueError("El usuario no existe.")
    with _BLOQUEO:
        datos = _cargar()
        if grupo and grupo not in datos["grupos"]:
            raise ValueError("El grupo no existe.")
        perfil = datos["perfiles"].get(usuario)
        perfil = perfil if isinstance(perfil, dict) else {}
        perfil["grupo"] = grupo or ""
        datos["perfiles"][usuario] = perfil
        _guardar(datos)
    return listar_grupos()


def guardar_temas_grupo(usuario, temas):
    grupo = grupo_de(usuario)
    if not grupo:
        raise ValueError("No perteneces a ningún grupo.")
    with _BLOQUEO:
        datos = _cargar()
        datos["grupos"][grupo]["temas"] = _limpiar_temas(temas)
        _guardar(datos)
    return datos["grupos"][grupo]["temas"]


def correo_de(nombre):
    return ((_cargar()["perfiles"].get(nombre) or {}).get("correo")) or ""


def guardar_correo(nombre, correo):
    """Guarda el correo del usuario ('' lo borra)."""
    if not existe(nombre):
        raise ValueError("El usuario no existe.")
    correo = str(correo or "").strip()
    if correo and not _CORREO.fullmatch(correo):
        raise ValueError("El correo no es válido.")
    with _BLOQUEO:
        datos = _cargar()
        perfil = datos["perfiles"].get(nombre)
        perfil = perfil if isinstance(perfil, dict) else {}
        perfil["correo"] = correo
        datos["perfiles"][nombre] = perfil
        _guardar(datos)
    return correo


def cumple_tema(alerta, palabras):
    """True si alguna palabra del tema aparece en el titular o el cuerpo."""
    from .processing import normalizar_texto
    texto = normalizar_texto(f"{alerta.get('titular_raw_limpio', '')} {alerta.get('titular', '')} {alerta.get('cuerpo', '')}")
    return any(
        re.search(r"(?<!\w)" + re.escape(normalizar_texto(p).strip()) + r"(?!\w)", texto)
        for p in palabras if normalizar_texto(p).strip()
    )
