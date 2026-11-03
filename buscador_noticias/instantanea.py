"""Copia de la última carga de fuentes, para mostrarla al instante mientras se actualiza en segundo plano."""
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

MAX_EDAD_HORAS = 48


def _ruta():
    return Path(os.environ.get("GAD_INSTANTANEA") or Path(tempfile.gettempdir()) / "buscador_instantanea.json")


def _codificar(obj):
    if isinstance(obj, datetime):
        return {"__dt__": obj.isoformat()}
    if isinstance(obj, (set, frozenset, tuple)):
        return list(obj)
    raise TypeError(type(obj).__name__)


def _decodificar(d):
    if "__dt__" in d and len(d) == 1:
        return datetime.fromisoformat(d["__dt__"])
    return d


def guardar(alertas, telemetria, actualizado):
    """Escritura atómica; un fallo de disco nunca debe romper la app."""
    try:
        ruta = _ruta()
        tmp = ruta.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(
                {"guardado": datetime.now().isoformat(), "actualizado": actualizado,
                 "alertas": alertas, "telemetria": telemetria},
                default=_codificar, ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        os.replace(tmp, ruta)
    except (OSError, TypeError, ValueError):
        pass


def cargar():
    """Devuelve (alertas, telemetria, actualizado) o None si no hay copia válida y reciente."""
    try:
        datos = json.loads(_ruta().read_text(encoding="utf-8"), object_hook=_decodificar)
        edad = datetime.now() - datetime.fromisoformat(datos["guardado"])
        if edad.total_seconds() > MAX_EDAD_HORAS * 3600 or not datos["alertas"]:
            return None
        return datos["alertas"], datos.get("telemetria") or [], datos.get("actualizado") or ""
    except (OSError, ValueError, KeyError, TypeError):
        return None
