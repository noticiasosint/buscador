"""Copia de seguridad de los datos en un dataset privado de Hugging Face.

Se activa solo si existen HF_TOKEN y HF_DATASET (p. ej. «usuario/buscador-datos»). Al arrancar restaura la
carpeta de datos y después la sube cada vez que detecta cambios.
"""
import hashlib
import os
import threading
import time

from .almacen import carpeta_base

INTERVALO = 45
_LOCK = threading.Lock()
_iniciado = False


def _huella(carpeta):
    h = hashlib.sha1()
    for ruta in sorted(carpeta.rglob("*")):
        if ruta.is_file() and not ruta.name.endswith(".tmp"):
            e = ruta.stat()
            h.update(f"{ruta.relative_to(carpeta)}|{e.st_size}|{e.st_mtime_ns}".encode())
    return h.hexdigest()


def _bucle(api, repo, carpeta):
    ultima = _huella(carpeta)
    while True:
        time.sleep(INTERVALO)
        try:
            actual = _huella(carpeta)
            if actual != ultima:
                api.upload_folder(
                    folder_path=str(carpeta),
                    repo_id=repo,
                    repo_type="dataset",
                    ignore_patterns=["*.tmp"],
                    commit_message="Copia automática",
                )
                ultima = actual
        except Exception:
            pass


def iniciar():
    global _iniciado
    token, repo = os.environ.get("HF_TOKEN"), os.environ.get("HF_DATASET")
    if not token or not repo:
        return False
    with _LOCK:
        if _iniciado:
            return True
        _iniciado = True
    try:
        from huggingface_hub import HfApi, snapshot_download

        api = HfApi(token=token)
        api.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)
        carpeta = carpeta_base()
        carpeta.mkdir(parents=True, exist_ok=True)
        snapshot_download(repo_id=repo, repo_type="dataset", local_dir=str(carpeta), token=token)
        threading.Thread(target=_bucle, args=(api, repo, carpeta), daemon=True).start()
    except Exception:
        return False
    return True
