# Buscador de Amenazas Híbridas

Buscador de noticias sobre amenazas híbridas, desinformación y sabotaje, con traducción y diccionario personalizado.

## Instalar y ejecutar (Windows)

Requisito: [Python 3.10+](https://www.python.org/downloads/) con «Add Python to PATH» marcado, y [Git](https://git-scm.com/downloads).

Antes de arrancar, configura `GAD_PASSWORD` en el entorno o en `.streamlit/secrets.toml` (este último archivo está excluido de Git).

```
git clone <URL_DEL_REPOSITORIO>
cd <carpeta_del_repositorio>
INICIAR.bat
```

La primera vez instala las dependencias (un par de minutos) y abre http://localhost:8501.
La carga inicial de fuentes tarda 1-2 minutos.

## Actualizar

```
git pull
INICIAR.bat
```

## Usuarios, grupos y clave de acceso

Se entra con **usuario y clave**. El administrador es `admin`; configura la clave con `GAD_PASSWORD`
en `.streamlit/secrets.toml` o en una variable de entorno. No guardes esa clave en GitHub.

- Cada usuario tiene lo suyo: **diccionario**, **secciones visibles**, **temas propios** (filtro «🎯 Mis temas»), **alertas guardadas**, **valoraciones** y lo ya visto (NUEVO).
- El administrador crea y borra usuarios en «🛠️ Administración» (un único bloque plegable). Borrar un usuario le quita el acceso pero deja sus datos en disco.
- **Grupos (🌳):** el administrador crea grupos y asigna usuarios. Los miembros de un grupo comparten **diccionario** y **temas** (al añadir una palabra o un tema marcan «Compartir con mi grupo»); lo demás sigue siendo personal.
- **✉️ Mi correo:** cada usuario guarda su correo en una ventana; el informe diario se envía a ese correo (si no tiene, al general `GAD_MAIL_TO`). Sigue haciendo falta `GAD_SMTP_HOST` y `GAD_MAIL_FROM`.
- Las claves se guardan cifradas (PBKDF2) en `%LOCALAPPDATA%\BuscadorAmenazas\usuarios.json` (`GAD_USUARIOS` para cambiarlo); los datos de cada usuario en `...\usuarios\<nombre>\` y los de cada grupo en `...\grupos\<nombre>\`. El administrador conserva los ficheros de siempre.

## Alertas, picos y valoraciones

- **Picos de actividad:** avisa de actores, áreas o temas que hoy superan el doble de su media diaria.
- **🆕 NUEVO:** marca lo que ha entrado desde tu última visita (la primera vez no marca nada).
- **Línea de tiempo** de alertas por hora o por día, con la parte de peligro alto.
- **Hilos de una historia:** agrupa noticias del mismo hecho y muestra quién lo contó primero y cómo se propagó.
- **Valoraciones:** en cada tarjeta, ✅ Confirmada / 🚫 Falsa / 💤 No relevante. Ajustan los porcentajes y, con el tiempo, la fiabilidad de cada canal. Es una estimación, no una verificación.
- **Alertas guardadas (barra lateral):** guarda una búsqueda y verás cuántas noticias nuevas coinciden.

Todo se guarda en `%LOCALAPPDATA%\BuscadorAmenazas\estado.json` (variable `GAD_ESTADO` para cambiarlo).
En Streamlit Cloud los datos locales pueden perderse al reiniciar la aplicación.

## Informe diario por correo

Genera el HTML con lo de peligro alto de las últimas 24 h y lo envía por correo.
1. Crea `correo.local.bat` junto a `INFORME_DIARIO.bat` con `GAD_SMTP_HOST`, `GAD_SMTP_PORT`, `GAD_SMTP_USER`, `GAD_SMTP_PASS`, `GAD_MAIL_FROM` y `GAD_MAIL_TO` (ejemplo dentro del `.bat`). No se sube a git.
2. Ejecuta `INFORME_DIARIO.bat` (sin correo configurado solo guarda el HTML en `informes\`).
3. Para programarlo: `schtasks /create /tn "InformeAmenazas" /tr "\"C:\ruta\INFORME_DIARIO.bat\"" /sc daily /st 08:00`.

La app también tiene en la barra lateral «📧 Informe diario» para descargarlo o enviarlo al momento.

## Otros sistemas

```
python -m venv .venv
.venv/bin/pip install -r requirements.txt
GAD_PASSWORD=tu_clave .venv/bin/python -m streamlit run app_entry.py
```

## Publicar desde tu PC (gratis, sin tarjeta ni cuenta)

Streamlit Cloud gratuito falla con navegadores nuevos o privados (no aguanta la ráfaga de módulos JS). Alternativa: ejecutar la app en tu PC y publicarla con un túnel de Cloudflare.

1. Crea `.streamlit\secrets.toml` con `GAD_PASSWORD = "tu_clave"` (no se sube a Git).
2. Ejecuta `PUBLICAR.bat`. La primera vez instala `cloudflared` y pide volver a abrirlo.
3. Comparte la dirección `https://....trycloudflare.com` que aparece en la ventana.

La dirección cambia en cada arranque y solo funciona mientras el PC y esa ventana sigan abiertos. Los datos quedan en tu PC.

## Desplegar en Render

El archivo `render.yaml` prepara el servicio web `noticiasosint` para Render. Conecta el repositorio de GitHub
en Render y configura `GAD_PASSWORD` como variable secreta cuando Render la solicite; no la guardes en el repositorio.
Render asignará `noticiasosint.onrender.com` si ese nombre está disponible en tu cuenta. Si ya existe un servicio
con ese nombre, conecta ese servicio al repositorio `OSINT-NOTICIAS` en lugar de crear otro.

## Pruebas

```
python -m unittest discover -s tests
```
