BUSCADOR DE AMENAZAS - WINDOWS

El ejecutable se inicia con doble clic, levanta Streamlit solo en el equipo
local y abre el navegador en http://127.0.0.1:8501. Mantén abierta la ventana
de consola mientras uses la aplicación; ciérrala para detener el servidor.

El panel lateral permite añadir una palabra o expresión y asignarla a una
categoría. Se guarda en %LOCALAPPDATA%\BuscadorAmenazas y se aplica al volver
a consultar las fuentes.

La traducción de términos usa MyMemory (vía deep-translator): gratuito, sin clave y
sin descargar modelos, por lo que funciona también en GitHub/Streamlit Cloud.
El término se envía a Internet para traducirlo y hay un límite diario gratuito.

Para generar de nuevo el ejecutable:
1. Instala Python 3.11 de 64 bits.
2. Ejecuta build_exe.ps1 desde PowerShell.
3. El resultado estará en dist\BuscadorAmenazas.exe.

La aplicación necesita conexión a Internet para consultar las fuentes
configuradas y descargar los modelos de traducción la primera vez. El ejecutable
no contiene credenciales ni incluye las fuentes de noticias descargadas.
