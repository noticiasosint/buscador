"""Estado persistente del usuario: valoraciones, búsquedas guardadas y noticias ya vistas."""
import json
import os
import re
import tempfile
import threading
from pathlib import Path

VALORACIONES = ("confirmada", "falsa", "irrelevante")
MAX_VISTOS = 20000
MAX_BUSQUEDAS = 30
_BLOQUEO = threading.RLock()


def carpeta_base():
    if os.environ.get("GAD_ESTADO"):
        return Path(os.environ["GAD_ESTADO"]).parent
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "BuscadorAmenazas"


def carpeta_usuario(usuario=None):
    """El administrador (o sin usuario) conserva los ficheros de siempre; el resto tiene su carpeta."""
    if usuario in (None, "", "admin"):
        return carpeta_base()
    if str(usuario).startswith("grupo:"):
        g = str(usuario)[6:]
        if not re.fullmatch(r"[a-z0-9_.-]{2,30}", g):
            raise ValueError("Nombre de grupo no válido.")
        return carpeta_base() / "grupos" / g
    if not re.fullmatch(r"[a-z0-9_.-]{2,30}", str(usuario)):
        raise ValueError("Nombre de usuario no válido.")
    return carpeta_base() / "usuarios" / str(usuario)


def ruta_estado(usuario=None):
    if usuario in (None, "", "admin") and os.environ.get("GAD_ESTADO"):
        return Path(os.environ["GAD_ESTADO"])
    return carpeta_usuario(usuario) / "estado.json"


def _vacio():
    return {"valoraciones": {}, "busquedas": [], "vistos": [], "visitado": False}


def cargar(usuario=None):
    try:
        datos = json.loads(ruta_estado(usuario).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _vacio()
    if not isinstance(datos, dict):
        return _vacio()
    estado = _vacio()
    if isinstance(datos.get("valoraciones"), dict):
        estado["valoraciones"] = {
            str(k): v for k, v in datos["valoraciones"].items() if v in VALORACIONES
        }
    if isinstance(datos.get("busquedas"), list):
        estado["busquedas"] = [b for b in datos["busquedas"] if isinstance(b, dict) and b.get("nombre")]
    if isinstance(datos.get("vistos"), list):
        estado["vistos"] = [str(v) for v in datos["vistos"]][-MAX_VISTOS:]
    estado["visitado"] = bool(datos.get("visitado"))
    return estado


def _guardar(estado, usuario=None):
    ruta = ruta_estado(usuario)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False)
        os.replace(tmp, ruta)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def valorar(id_alerta, valoracion, usuario=None):
    """Guarda la valoración del analista; None la elimina."""
    if valoracion is not None and valoracion not in VALORACIONES:
        raise ValueError("Valoración no válida.")
    with _BLOQUEO:
        estado = cargar(usuario)
        if valoracion is None:
            estado["valoraciones"].pop(str(id_alerta), None)
        else:
            estado["valoraciones"][str(id_alerta)] = valoracion
        _guardar(estado, usuario)
    return estado["valoraciones"]


def guardar_busqueda(nombre, consulta, modo, ids_actuales=(), usuario=None):
    nombre = re.sub(r"\s+", " ", str(nombre)).strip()[:60]
    consulta = str(consulta).strip()[:500]
    if not nombre:
        raise ValueError("Escribe un nombre para la búsqueda.")
    if not consulta:
        raise ValueError("Escribe primero algo en el buscador.")
    with _BLOQUEO:
        estado = cargar(usuario)
        estado["busquedas"] = [b for b in estado["busquedas"] if b["nombre"] != nombre]
        if len(estado["busquedas"]) >= MAX_BUSQUEDAS:
            raise ValueError(f"Máximo {MAX_BUSQUEDAS} búsquedas guardadas.")
        estado["busquedas"].append(
            {"nombre": nombre, "consulta": consulta, "modo": str(modo), "vistos": [str(i) for i in ids_actuales][-2000:]}
        )
        _guardar(estado, usuario)
    return estado["busquedas"]


def borrar_busqueda(nombre, usuario=None):
    with _BLOQUEO:
        estado = cargar(usuario)
        estado["busquedas"] = [b for b in estado["busquedas"] if b["nombre"] != nombre]
        _guardar(estado, usuario)
    return estado["busquedas"]


def marcar_busqueda_vista(nombre, ids, usuario=None):
    with _BLOQUEO:
        estado = cargar(usuario)
        for b in estado["busquedas"]:
            if b["nombre"] == nombre:
                b["vistos"] = [str(i) for i in ids][-2000:]
        _guardar(estado, usuario)


def registrar_vistos(ids, usuario=None):
    """Devuelve los ids que ya se conocían antes de esta visita y guarda los nuevos."""
    with _BLOQUEO:
        estado = cargar(usuario)
        previos = set(estado["vistos"])
        visitado = estado["visitado"]
        orden = estado["vistos"] + [str(i) for i in ids if str(i) not in previos]
        estado["vistos"] = orden[-MAX_VISTOS:]
        estado["visitado"] = True
        _guardar(estado, usuario)
    return previos, visitado
