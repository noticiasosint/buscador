"""Cifra la página móvil para que cada usuario la abra con su propia clave.

Esquema: el HTML se comprime y se cifra una sola vez con una clave aleatoria (AES-GCM).
Esa clave se guarda envuelta una vez por usuario, con una clave derivada de su contraseña (PBKDF2).
Quitar a un usuario de la lista y regenerar la página le impide abrir las siguientes versiones.

Uso:  GAD_PAGINA_USUARIOS="ana:clave1\nluis:clave2" python -m buscador_noticias.pagina_cifrada ENTRADA.html SALIDA.html
"""
import base64
import gzip
import hashlib
import json
import os
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITERACIONES = 250_000


def _b64(b):
    return base64.b64encode(b).decode("ascii")


def _id_usuario(usuario):
    return hashlib.sha256(usuario.strip().lower().encode("utf-8")).hexdigest()[:16]


def _sal(usuario):
    return hashlib.sha256(b"sal:" + usuario.strip().lower().encode("utf-8")).digest()[:16]


def clave_de_usuario(usuario, clave):
    return hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), _sal(usuario), ITERACIONES, 32)


def leer_usuarios(texto):
    """Líneas 'usuario:clave'. Ignora vacías y comentarios (#)."""
    resultado = {}
    for linea in (texto or "").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or ":" not in linea:
            continue
        usuario, clave = linea.split(":", 1)
        usuario = usuario.strip().lower()
        if usuario and clave:
            resultado[usuario] = clave
    return resultado


def cifrar_pagina(html, usuarios):
    if not usuarios:
        raise ValueError("No hay usuarios: define GAD_PAGINA_USUARIOS (líneas usuario:clave)")
    k = os.urandom(32)
    nonce = os.urandom(12)
    contenido = AESGCM(k).encrypt(nonce, gzip.compress(html.encode("utf-8"), 9), None)
    envolturas = {}
    for usuario, clave in usuarios.items():
        n = os.urandom(12)
        envolturas[_id_usuario(usuario)] = _b64(n + AESGCM(clave_de_usuario(usuario, clave)).encrypt(n, k, None))
    datos = {"i": ITERACIONES, "w": envolturas, "c": _b64(nonce + contenido)}
    return PLANTILLA.replace("__DATOS__", json.dumps(datos, separators=(",", ":")))


PLANTILLA = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0f172a"><meta name="robots" content="noindex">
<title>Acceso restringido</title>
<style>
*{box-sizing:border-box}body{margin:0;font:16px system-ui,sans-serif;background:#fff;color:#0f172a}
.t{background:#0f172a;color:#fff;border-left:6px solid #dc2626;border-radius:12px;margin:24px 14px 12px;padding:22px 16px;text-align:center}
.t h1{margin:8px 0 4px;font-size:20px}.t p{margin:4px 0;color:#7dd3fc;font-weight:700;font-size:13px}
form{margin:0 14px;padding:14px;border:1px solid #e2e8f0;border-radius:10px}
label{display:block;font-size:13px;margin:8px 0 4px;color:#475569}
input[type=text],input[type=password]{width:100%;padding:11px;border:0;border-radius:8px;background:#f0f2f6;font-size:16px}
.r{display:flex;gap:8px;align-items:center;margin:10px 0;font-size:13px;color:#475569}
button{width:100%;padding:12px;border:0;border-radius:8px;background:#ff4b4b;color:#fff;font-size:15px;font-weight:700}
#e{color:#b91c1c;font-size:14px;margin-top:10px;min-height:18px}
</style></head><body>
<div class="t"><div style="font-size:38px">🛡️</div><h1>🔒 ACCESO RESTRINGIDO</h1><p>SISTEMA DE VIGILANCIA DE FUENTES ABIERTAS</p></div>
<form id="f"><label>Usuario</label><input id="u" type="text" autocomplete="username" autocapitalize="none" autocorrect="off">
<label>Clave de acceso</label><input id="p" type="password" autocomplete="current-password">
<div class="r"><input id="r" type="checkbox" checked><label for="r" style="margin:0">Recordarme en este dispositivo</label></div>
<button id="b">INGRESAR AL SISTEMA</button><div id="e"></div></form>
<script>
(()=>{const P=__DATOS__,te=new TextEncoder(),$=i=>document.getElementById(i);
const d64=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
const hex=b=>[...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,"0")).join("");
async function sha(s){return new Uint8Array(await crypto.subtle.digest("SHA-256",te.encode(s)))}
async function derivar(u,c){const sal=(await sha("sal:"+u)).slice(0,16);
 const m=await crypto.subtle.importKey("raw",te.encode(c),"PBKDF2",false,["deriveBits"]);
 return new Uint8Array(await crypto.subtle.deriveBits({name:"PBKDF2",hash:"SHA-256",salt:sal,iterations:P.i},m,256))}
async function aes(raw,usos){return crypto.subtle.importKey("raw",raw,"AES-GCM",false,usos)}
async function abrir(u,wk){
 const id=hex(await sha(u)).slice(0,16),w=P.w[id];if(!w)throw 0;
 const b=d64(w),k=new Uint8Array(await crypto.subtle.decrypt({name:"AES-GCM",iv:b.slice(0,12)},await aes(wk,["decrypt"]),b.slice(12)));
 const c=d64(P.c),z=await crypto.subtle.decrypt({name:"AES-GCM",iv:c.slice(0,12)},await aes(k,["decrypt"]),c.slice(12));
 const s=new Response(new Blob([z]).stream().pipeThrough(new DecompressionStream("gzip")));
 const h=await s.text();document.open();document.write(h);document.close()}
async function entrar(u,wk,recordar){await abrir(u,wk);
 try{if(recordar)localStorage.setItem("gad_s",JSON.stringify([u,hex(wk)]));else localStorage.removeItem("gad_s")}catch(_){}}
$("f").onsubmit=async ev=>{ev.preventDefault();const e=$("e"),b=$("b");e.textContent="";
 if(!(window.crypto&&crypto.subtle)){e.textContent="Este navegador no admite el acceso seguro.";return}
 const u=$("u").value.trim().toLowerCase();b.disabled=true;b.textContent="Comprobando…";
 try{await entrar(u,await derivar(u,$("p").value),$("r").checked)}
 catch(_){e.textContent="Usuario o clave incorrectos.";b.disabled=false;b.textContent="INGRESAR AL SISTEMA"}};
(async()=>{try{const s=JSON.parse(localStorage.getItem("gad_s")||"null");
 if(s)await abrir(s[0],Uint8Array.from(s[1].match(/../g),h=>parseInt(h,16)))}
 catch(_){try{localStorage.removeItem("gad_s")}catch(_){}}})();
})();
</script></body></html>"""


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__)
        return 2
    usuarios = leer_usuarios(os.environ.get("GAD_PAGINA_USUARIOS", ""))
    with open(argv[0], encoding="utf-8") as f:
        html = f.read()
    os.makedirs(os.path.dirname(os.path.abspath(argv[1])), exist_ok=True)
    with open(argv[1], "w", encoding="utf-8") as f:
        f.write(cifrar_pagina(html, usuarios))
    print(f"Página cifrada para {len(usuarios)} usuario(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
