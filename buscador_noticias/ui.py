import streamlit as st

def run_app():
    import os

    from .config import LOGO_FONDO_SVG, LOGO_OFICIAL_SVG, SECCIONES_INFORME
    from . import usuarios

    st.set_page_config(
        page_title="Buscador de Amenazas Híbridas",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown(f"""
    <style>
        #MainMenu, footer {{ visibility: hidden !important; display: none !important; height: 0px !important; }}
        header[data-testid="stHeader"], [data-testid="stToolbar"] {{ visibility: visible !important; display: flex !important; background: transparent !important; pointer-events: none !important; }}
        [data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"] {{
            visibility: visible !important; display: flex !important; opacity: 1 !important; pointer-events: auto !important;
        }}
        a.header-anchor, a[data-testid="header-anchor"] {{ display: none !important; visibility: hidden !important; }}
        [data-testid="stToolbarActions"], [data-testid="stMainMenu"], [data-testid="stAppDeployButton"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="manage-app-button"],
        button[kind="manage-app"], .manage-app, div[class*="manage-app"], .viewerBadge_container__1QSob, div[class*="viewerBadge"],
        div[class*="profileContainer"], a[href*="github.com"] {{
            visibility: hidden !important; display: none !important; opacity: 0 !important; pointer-events: none !important;
        }}
        .main {{
            background-color: #0b0f19;
            background-image: url('{LOGO_FONDO_SVG}');
            background-repeat: no-repeat;
            background-position: center 35%;
            background-size: min(520px, 70vw);
            background-attachment: fixed;
        }}
        .stTabs [data-baseweb="tab-list"] {{ gap: 6px !important; }}
        .stTabs [data-baseweb="tab"] {{ padding-left: 10px !important; padding-right: 10px !important; font-size: 12px !important; font-weight: 800 !important; }}
        .threat-card {{ background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 16px 20px; margin-bottom: 14px; }}
        .badge-item {{ font-size: 11px; font-weight: 800; padding: 3px 8px; border-radius: 4px; display: inline-block; }}
        .ner-pill {{ font-size: 10.5px; font-weight: 700; padding: 2px 7px; border-radius: 4px; color: #fff; margin-right: 5px; display: inline-block; }}
        .btn-source {{ background-color: #0f172a; color: #ffffff !important; padding: 6px 14px; border-radius: 4px; font-size: 12px; font-weight: 700; text-decoration: none !important; display: inline-block; margin-top: 8px; }}
        mark.osint-hit {{
            background-color: #fef08a !important;
            color: #854d0e !important;
            font-weight: 800 !important;
            padding: 1px 4px !important;
            border-radius: 3px !important;
            border: 1px solid #facc15 !important;
        }}
        .secondary-box {{
            background-color: #eff6ff;
            border-left: 4px solid #2563eb;
            padding: 10px 14px;
            margin-top: 8px;
            border-radius: 4px;
            margin-bottom: 6px;
        }}
    </style>
    """, unsafe_allow_html=True)

    try:
        CLAVE_SISTEMA = st.secrets.get("GAD_PASSWORD")
    except Exception:
        CLAVE_SISTEMA = None
    CLAVE_SISTEMA = CLAVE_SISTEMA or os.environ.get("GAD_PASSWORD")
    if not CLAVE_SISTEMA:
        st.error("Configura GAD_PASSWORD en los secretos de Streamlit o en las variables de entorno.")
        st.stop()

    def gestionar_acceso():
        if st.session_state.get("autenticado", False):
            return True

        st.markdown(f"""
            <div style="max-width: 500px; margin: 40px auto 16px auto; padding: 32px 28px; background: #0f172a; border-radius: 12px; border-left: 6px solid #dc2626; color: white; box-shadow: 0 16px 36px rgba(0,0,0,0.6); text-align: center;">
                <div style="margin-bottom: 14px;">{LOGO_OFICIAL_SVG}</div>
                <h2 style="margin: 0 0 10px 0; color: #ffffff; font-size: 22px; font-weight: 850; letter-spacing: 0.5px;">🔒 ACCESO RESTRINGIDO</h2>
                <div style="font-size: 14.5px; font-weight: 700; color: #38bdf8; margin-bottom: 6px;">
                    SISTEMA DE VIGILANCIA DE FUENTES ABIERTAS
                </div>
                <div style="font-size: 14px; color: #ffffff; font-weight: 600;">
                    Introduzca la clave autorizada para continuar.
                </div>
            </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1.1, 1])
        with col2:
            with st.form("form_login"):
                usuario_input = st.text_input("Usuario:", value=st.session_state.get("ultimo_usuario", "admin"))
                clave_input = st.text_input("Clave de acceso:", type="password", placeholder="Introduce la contraseña...")
                if st.form_submit_button("INGRESAR AL SISTEMA", type="primary", use_container_width=True):
                    sesion = usuarios.autenticar(usuario_input, clave_input, CLAVE_SISTEMA)
                    if sesion:
                        st.session_state.autenticado = True
                        st.session_state.usuario = sesion["usuario"]
                        st.session_state.rol = sesion["rol"]
                        st.session_state.ultimo_usuario = sesion["usuario"]
                        st.rerun()
                    else:
                        st.error("Credencial incorrecta.")
        return False

    if not gestionar_acceso():
        st.stop()

    import html as html_module
    import math
    import pandas as pd
    import streamlit.components.v1 as components
    from datetime import datetime, timezone

    from .dictionary import agregar_termino_personalizado, cargar_diccionario_efectivo
    from .translator import (
        IDIOMAS_ORIGEN,
        IDIOMAS_TRADUCCION,
        traducir_a_espanol,
        traducir_termino,
    )
    from .processing import (
        ZONA_MADRID,
        MODO_BUSQUEDA_DEFECTO,
        MODOS_BUSQUEDA,
        clave_actualidad_cobertura,
        cumple_busqueda_booleana_avanzada,
        cumple_ventana_temporal,
        es_url_segura,
        obtener_fecha_madrid_str,
        resaltar_coincidencias,
        url_sanitizada,
    )
    from .reports import generar_html_ejecutivo
    from . import almacen
    from .analisis import (
        agrupar_hilos,
        contar_nuevas_busqueda,
        ids_nuevos,
        puntuar_con_aprendizaje,
        reputacion_canales,
    )
    from .informe_diario import configuracion_correo, construir_informe, enviar_correo
    from .resumen import _md_texto, enlace_md, enlaces_numerados_md, resumen_a_texto, resumen_redes, resumir
    from .scoring import AVISO as AVISO_INDICADORES
    from .sources import cargar_todas_las_fuentes, obtener_ejecutor_fuentes
    from .perfiles import PERFILES, perfil_de_canal
    from .keepalive import iniciar_keepalive

    iniciar_keepalive()

    components.html(
        """<script>
        try {
            const root = window.parent.document.documentElement;
            root.removeAttribute("translate");
            root.classList.remove("notranslate");
        } catch (error) {}
        </script>""",
        height=0,
    )

    logo_svg = """<svg width="65" height="65" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="50" cy="50" r="47" fill="#1e293b" stroke="#334155" stroke-width="2" />
        <circle cx="50" cy="50" r="40" stroke="#38bdf8" stroke-width="1.2" stroke-dasharray="3 3" opacity="0.6" />
        <path d="M50 14 L75 25 V52 C75 69 50 84 50 84 C50 84 25 69 25 52 V25 Z" fill="#0f172a" stroke="#38bdf8" stroke-width="2.5" />
        <polygon points="53,24 37,48 48,48 43,72 61,44 51,44" fill="#ef4444" />
    </svg>"""

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-left: 8px solid #dc2626; border-radius: 10px; padding: 16px 22px; margin-bottom: 12px; display: flex; align-items: center; gap: 20px; width: 100%;">
        <div>{logo_svg}</div>
        <div>
            <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 900; letter-spacing: 0.5px;">BUSCADOR DE AMENAZAS HÍBRIDAS</h1>
            <p style="color: #94a3b8; font-size: 13.5px; margin: 4px 0 0 0;">SISTEMA DE VIGILANCIA DE FUENTES ABIERTAS</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    usuario = st.session_state.get("usuario", usuarios.ADMIN)
    es_admin = st.session_state.get("rol") == "admin"

    grupo_usuario = usuarios.grupo_de(usuario)

    try:
        diccionario_personalizado = cargar_diccionario_efectivo(usuario)
    except (OSError, ValueError) as exc:
        st.sidebar.error(f"No se pudo cargar el diccionario personalizado: {exc}")
        st.stop()

    nombres_categorias = {codigo: nombre.split(": ", 1)[-1] for codigo, nombre, _ in SECCIONES_INFORME}
    with st.sidebar.expander("📚 Añadir palabras", expanded=False):
        st.caption(
            "La traducción ofrece 40 idiomas y usa MyMemory, un servicio gratuito sin clave: el término "
            "se envía a Internet para traducirlo. No descarga modelos, por lo que "
            "funciona igual en local y en la nube."
        )
        idioma_origen_personalizado = st.selectbox(
            "Idioma del término:",
            options=list(IDIOMAS_ORIGEN),
            index=0,
        )
        codigo_origen_personalizado = IDIOMAS_ORIGEN[idioma_origen_personalizado]
        with st.form("form_diccionario_personalizado", clear_on_submit=True):
            termino_personalizado = st.text_input("Palabra o expresión:")
            categoria_personalizada = st.selectbox(
                "Categoría:",
                options=list(nombres_categorias),
                format_func=lambda codigo: nombres_categorias[codigo],
            )
            idiomas_destino_disponibles = [
                idioma
                for idioma, codigo in IDIOMAS_TRADUCCION.items()
                if codigo != codigo_origen_personalizado
            ]
            idiomas_personalizados = st.multiselect(
                "Traducir a:",
                options=idiomas_destino_disponibles,
                default=[
                    idioma
                    for idioma in (
                        "Inglés",
                        "Ruso",
                        "Ucraniano",
                        "Árabe",
                        "Chino simplificado",
                    )
                    if idioma in idiomas_destino_disponibles
                ],
            )
            compartir_palabra = st.checkbox(f"Compartir con mi grupo ({grupo_usuario})", value=False) if grupo_usuario else False
            agregar_enviado = st.form_submit_button("Añadir palabra", type="primary")

        if agregar_enviado:
            try:
                with st.spinner("Traduciendo el término a los idiomas seleccionados..."):
                    traducciones = traducir_termino(
                        termino_personalizado,
                        idiomas_personalizados,
                        codigo_origen_personalizado,
                    )
                    agregar_termino_personalizado(
                        termino_personalizado,
                        categoria_personalizada,
                        traducciones,
                        f"grupo:{grupo_usuario}" if compartir_palabra else usuario,
                    )
            except (OSError, ValueError, RuntimeError) as exc:
                st.error(f"No se pudo añadir la palabra: {exc}")
            else:
                st.session_state["diccionario_mensaje"] = (
                    "Palabra y traducciones guardadas. Se actualizarán las alertas."
                )
                st.cache_data.clear()
                for clave in (
                    "alertas_base",
                    "telemetria_fuentes",
                    "ultima_actualizacion",
                    "seleccionadas_ids",
                ):
                    st.session_state.pop(clave, None)
                st.rerun()

        mensaje_diccionario = st.session_state.pop("diccionario_mensaje", None)
        if mensaje_diccionario:
            st.success(mensaje_diccionario)

        if diccionario_personalizado:
            st.markdown("**Palabras guardadas**")
            for entrada in diccionario_personalizado:
                idiomas_guardados = ", ".join(
                    f"{traduccion['idioma']}: {traduccion['texto']}"
                    for traduccion in entrada["traducciones"]
                )
                detalle_traducciones = f" ({idiomas_guardados})" if idiomas_guardados else ""
                st.caption(f"{entrada['termino']}{detalle_traducciones}")
                st.caption(f"Categoría: {nombres_categorias[entrada['categoria']]}")
        else:
            st.caption("Aún no hay palabras personalizadas.")

    if "alertas_base" not in st.session_state:
        if "carga_fuentes_error" in st.session_state:
            st.error(f"No se pudieron cargar las fuentes: {st.session_state.carga_fuentes_error}")
        else:
            if "carga_fuentes_future" not in st.session_state:
                st.session_state.carga_fuentes_future = obtener_ejecutor_fuentes().submit(
                    cargar_todas_las_fuentes,
                    diccionario_personalizado,
                )
            st.markdown(
                '<style>@keyframes girar{0%{transform:rotate(0)}50%{transform:rotate(180deg)}100%{transform:rotate(180deg)}}'
                '.reloj-arena{display:inline-block;font-size:26px;animation:girar 1.6s ease-in-out infinite;margin-right:10px}</style>'
                '<div style="background:#eff6ff;border-left:4px solid #3b82f6;padding:10px 14px;color:#1e3a8a;">'
                '<span class="reloj-arena">⏳</span>Sincronizando las fuentes en segundo plano. '
                'Puedes configurar filtros mientras termina.</div>',
                unsafe_allow_html=True,
            )
            if hasattr(st, "fragment"):
                @st.fragment(run_every=2)
                def vigilar_carga_fuentes():
                    future = st.session_state.get("carga_fuentes_future")
                    if future is None:
                        return
                    if not future.done():
                        st.caption("Consultando prensa, RSS y canales sociales…")
                        return
                    try:
                        unicos, telemetria = future.result()
                    except Exception as exc:
                        st.session_state.carga_fuentes_error = str(exc)
                    else:
                        st.session_state.alertas_base = unicos
                        st.session_state.telemetria_fuentes = telemetria
                        st.session_state.ultima_actualizacion = obtener_fecha_madrid_str()
                        st.session_state.seleccionadas_ids = {a["id"] for a in unicos}
                    st.session_state.pop("carga_fuentes_future", None)
                    st.rerun()

                vigilar_carga_fuentes()
            else:
                future = st.session_state.carga_fuentes_future
                if future.done():
                    try:
                        unicos, telemetria = future.result()
                    except Exception as exc:
                        st.session_state.carga_fuentes_error = str(exc)
                    else:
                        st.session_state.alertas_base = unicos
                        st.session_state.telemetria_fuentes = telemetria
                        st.session_state.ultima_actualizacion = obtener_fecha_madrid_str()
                        st.session_state.seleccionadas_ids = {a["id"] for a in unicos}
                    st.session_state.pop("carga_fuentes_future", None)
                    st.rerun()

    alertas_totales = st.session_state.get("alertas_base", [])

    prefs = usuarios.preferencias(usuario, {c for c, _, _ in SECCIONES_INFORME})
    secciones_visibles = prefs["secciones"]
    nombres_propios = {t["nombre"].lower() for t in prefs["temas"]}
    temas_todos = prefs["temas"] + [t for t in prefs["temas_grupo"] if t["nombre"].lower() not in nombres_propios]

    def _seccion_de(a):
        return "TELEGRAM" if a["plataforma"] == "TELEGRAM" else "REDES" if a["plataforma"] == "REDES" else a["categoria"]

    if secciones_visibles is not None:
        alertas_totales = [a for a in alertas_totales if a["categoria"] in secciones_visibles or _seccion_de(a) in secciones_visibles]

    estado_usuario = almacen.cargar(usuario)
    valoraciones = estado_usuario["valoraciones"]
    reputacion = reputacion_canales(alertas_totales, valoraciones)
    if st.session_state.get("nuevos_para") != st.session_state.get("ultima_actualizacion"):
        previos, visitado = almacen.registrar_vistos([a["id"] for a in alertas_totales], usuario)
        st.session_state.nuevos_ids = ids_nuevos(alertas_totales, previos, visitado)
        st.session_state.nuevos_para = st.session_state.get("ultima_actualizacion")
    nuevos_ids = st.session_state.get("nuevos_ids", set())
    with st.container():
        c_flt1, c_flt1b, c_flt2, c_flt3, c_flt4, c_flt5 = st.columns([1.3, 0.9, 0.95, 1.1, 1.25, 0.7])
        with c_flt1:
            busqueda_txt = st.text_input(
                "🔍 Buscar:",
                key="busqueda_txt",
                placeholder="",
                help='Admite "frase exacta", OR, AND y NOT / -palabra. Ejemplo: sabotaje ferroviario -Ucrania',
            )
        with c_flt1b:
            modo_busqueda = st.selectbox(
                "🎯 Precisión:",
                list(MODOS_BUSQUEDA),
                index=list(MODOS_BUSQUEDA).index(MODO_BUSQUEDA_DEFECTO),
                key="modo_busqueda",
                help="\n\n".join(f"**{nombre}**: {descripcion}" for nombre, descripcion in MODOS_BUSQUEDA.items()),
            )
        with c_flt2:
            rango_tiempo = st.selectbox(
                "📅 Ventana Temporal:",
                ["Últimas 24 Horas", "Últimas 48 Horas", "Última Semana", "Histórico Completo"],
                index=0,
                key="ventana_tiempo_inicial_v1",
            )
        with c_flt3:
            canales_sel = st.multiselect("Filtrar por Canal:", sorted(list({a["canal"] for a in alertas_totales})))
            temas_sel = st.multiselect("🎯 Mis temas:", [t["nombre"] for t in temas_todos]) if temas_todos else []
        with c_flt4:
            orden_alertas = st.selectbox(
                "⭐ Priorizar:",
                ["Actualidad + cobertura", "Más recientes"],
                index=0,
                help="Agrupa por bandas de 6 horas: prioriza primero la actualidad y, dentro de cada banda, más fuentes/canales detectados. No mide viralidad ni prueba independencia editorial."
            )
        with c_flt5:
            noticias_por_pagina = st.selectbox("📄 Por pág.:", [10, 20, 50, "Todas"], index=1)

    if rango_tiempo == "Últimas 24 Horas": datos_filtrados = [x for x in alertas_totales if cumple_ventana_temporal(x["fecha_dt"], 24)]
    elif rango_tiempo == "Últimas 48 Horas": datos_filtrados = [x for x in alertas_totales if cumple_ventana_temporal(x["fecha_dt"], 48)]
    elif rango_tiempo == "Última Semana": datos_filtrados = [x for x in alertas_totales if cumple_ventana_temporal(x["fecha_dt"], 168)]
    else: datos_filtrados = alertas_totales

    if busqueda_txt: datos_filtrados = [x for x in datos_filtrados if cumple_busqueda_booleana_avanzada(x, busqueda_txt, modo_busqueda)]
    if canales_sel: datos_filtrados = [x for x in datos_filtrados if x["canal"] in canales_sel]
    if temas_sel:
        palabras_temas = [p for t in temas_todos if t["nombre"] in temas_sel for p in t["palabras"]]
        datos_filtrados = [x for x in datos_filtrados if usuarios.cumple_tema(x, palabras_temas)]

    # "No relevante" retira la noticia de todas las vistas
    datos_filtrados = [x for x in datos_filtrados if valoraciones.get(x["id"]) != "irrelevante"]

    if orden_alertas == "Actualidad + cobertura":
        datos_filtrados.sort(key=clave_actualidad_cobertura, reverse=True)

    def _aplicar_busqueda(b):
        st.session_state.busqueda_txt = b["consulta"]
        if b["modo"] in MODOS_BUSQUEDA:
            st.session_state.modo_busqueda = b["modo"]
        _, coinciden = contar_nuevas_busqueda(alertas_totales, b, cumple_busqueda_booleana_avanzada)
        almacen.marcar_busqueda_vista(b["nombre"], [a["id"] for a in coinciden], usuario)

    def _valorar(id_alerta, valor):
        almacen.valorar(id_alerta, valor, usuario)

    def _cerrar_sesion():
        for clave in ("autenticado", "usuario", "rol", "alertas_base", "nuevos_para", "nuevos_ids", "seleccionadas_ids"):
            st.session_state.pop(clave, None)

    def _recargar_datos():
        for clave in ("alertas_base", "telemetria_fuentes", "ultima_actualizacion", "seleccionadas_ids", "nuevos_para"):
            st.session_state.pop(clave, None)

    @st.dialog("✉️ Mi correo")
    def _dialogo_correo():
        st.caption("Aquí recibirás el informe diario. Déjalo vacío para usar el correo general de la aplicación.")
        correo_nuevo = st.text_input("Correo electrónico:", value=usuarios.correo_de(usuario))
        if st.button("💾 Guardar", type="primary", use_container_width=True):
            try:
                usuarios.guardar_correo(usuario, correo_nuevo)
            except (OSError, ValueError) as exc:
                st.error(str(exc))
            else:
                st.rerun()

    st.sidebar.markdown(f"👤 **{usuario}** · {'administrador' if es_admin else 'usuario'}" + (f" · 👥 {grupo_usuario}" if grupo_usuario else ""))
    c_ses1, c_ses2 = st.sidebar.columns(2)
    if st.sidebar.toggle("🙈 Ocultar paneles", key="ocultar_paneles"):
        st.sidebar.markdown(
            '<style>[data-testid="stSidebar"] [data-testid="stExpander"]{display:none}</style>',
            unsafe_allow_html=True,
        )
    c_ses1.button("🚪 Salir", on_click=_cerrar_sesion, use_container_width=True)
    if c_ses2.button("✉️ Mi correo", use_container_width=True):
        _dialogo_correo()

    with st.sidebar.expander("👥 Mi grupo", expanded=False):
        grupos_disp = [""] + [g["grupo"] for g in usuarios.listar_grupos()]
        mi_grupo = st.selectbox(
            "Grupo:", grupos_disp,
            index=grupos_disp.index(grupo_usuario) if grupo_usuario in grupos_disp else 0,
            format_func=lambda g: g or "(sin grupo)", key=f"mi_grupo_{usuario}",
        )
        if mi_grupo != (grupo_usuario or ""):
            try:
                usuarios.asignar_grupo(usuario, mi_grupo)
            except (OSError, ValueError) as exc:
                st.error(str(exc))
            else:
                _recargar_datos()
                st.rerun()

    with st.sidebar.expander("🎛️ Mis secciones y temas", expanded=False):
        todas_secciones = {c: n.split(": ", 1)[-1] for c, n, _ in SECCIONES_INFORME}
        elegidas = st.multiselect(
            "Secciones visibles:",
            options=list(todas_secciones),
            default=secciones_visibles if secciones_visibles is not None else list(todas_secciones),
            format_func=lambda c: todas_secciones[c],
            key=f"sel_secciones_{usuario}",
        )
        if st.button("💾 Guardar secciones", use_container_width=True):
            try:
                usuarios.guardar_preferencias(
                    usuario,
                    secciones=None if len(elegidas) == len(todas_secciones) else elegidas,
                    codigos_validos=set(todas_secciones),
                )
            except (OSError, ValueError) as exc:
                st.error(str(exc))
            else:
                _recargar_datos()
                st.rerun()
        st.markdown("**Mis temas** (palabras clave propias)")
        for tema in prefs["temas"]:
            c1, c2 = st.columns([0.8, 0.2])
            c1.caption(f"🎯 {tema['nombre']}: {', '.join(tema['palabras'])}")
            if c2.button("🗑️", key=f"bt_{tema['nombre']}", help="Borrar este tema"):
                usuarios.guardar_temas(usuario, [t for t in prefs["temas"] if t["nombre"] != tema["nombre"]])
                st.rerun()
        for tema in prefs["temas_grupo"]:
            c1, c2 = st.columns([0.8, 0.2])
            c1.caption(f"👥 {tema['nombre']} (grupo {grupo_usuario}): {', '.join(tema['palabras'])}")
            if c2.button("🗑️", key=f"btg_{tema['nombre']}", help="Borrar este tema del grupo"):
                usuarios.guardar_temas_grupo(usuario, [t for t in prefs["temas_grupo"] if t["nombre"] != tema["nombre"]])
                st.rerun()
        with st.form("form_tema", clear_on_submit=True):
            nombre_tema = st.text_input("Nombre del tema:", placeholder="Ej.: Sabotaje ferroviario")
            palabras_tema = st.text_input("Palabras (separadas por comas):", placeholder="tren, ferrocarril, vía")
            compartir_tema = st.checkbox(f"Compartir con mi grupo ({grupo_usuario})", value=False) if grupo_usuario else False
            if st.form_submit_button("Añadir tema"):
                nuevo_tema = {"nombre": nombre_tema, "palabras": [p for p in palabras_tema.split(",")]}
                if nombre_tema.strip() and any(p.strip() for p in palabras_tema.split(",")):
                    if compartir_tema:
                        usuarios.guardar_temas_grupo(usuario, prefs["temas_grupo"] + [nuevo_tema])
                    else:
                        usuarios.guardar_temas(usuario, prefs["temas"] + [nuevo_tema])
                    st.rerun()
                else:
                    st.error("Escribe un nombre y al menos una palabra.")

    with st.sidebar.expander("🔑 Cambiar mi clave", expanded=False):
        with st.form("form_clave", clear_on_submit=True):
            clave_nueva = st.text_input("Nueva clave (mín. 6):", type="password")
            if st.form_submit_button("Cambiar clave"):
                try:
                    usuarios.cambiar_clave(usuario, clave_nueva)
                except (OSError, ValueError) as exc:
                    st.error(str(exc))
                else:
                    st.success("Clave cambiada.")

    if es_admin:
        with st.sidebar.expander("🛠️ Administración", expanded=False):
            st.markdown("**👥 Usuarios**")
            lista_grupos = [g["grupo"] for g in usuarios.listar_grupos()]
            for u in usuarios.listar():
                c1, c2 = st.columns([0.8, 0.2])
                c1.caption(f"{u['usuario']} · {u['rol']}" + (f" · ✉️ {u['correo']}" if u["correo"] else ""))
                if u["usuario"] != usuarios.ADMIN and c2.button("🗑️", key=f"bu_{u['usuario']}", help="Borrar usuario (sus datos se conservan en disco)"):
                    usuarios.borrar(u["usuario"])
                    st.rerun()
                if lista_grupos:
                    opciones = [""] + lista_grupos
                    elegido = st.selectbox(
                        "Grupo:", opciones, index=opciones.index(u["grupo"]) if u["grupo"] in opciones else 0,
                        format_func=lambda g: g or "(sin grupo)", key=f"gu_{u['usuario']}", label_visibility="collapsed",
                    )
                    if elegido != u["grupo"]:
                        usuarios.asignar_grupo(u["usuario"], elegido)
                        st.cache_data.clear()
                        st.rerun()
            with st.form("form_usuario", clear_on_submit=True):
                nuevo_usuario = st.text_input("Nuevo usuario:")
                nueva_clave = st.text_input("Clave inicial (mín. 6):", type="password")
                nuevo_rol = st.selectbox("Rol:", list(usuarios.ROLES), index=1)
                if st.form_submit_button("Crear usuario"):
                    try:
                        usuarios.crear(nuevo_usuario, nueva_clave, nuevo_rol)
                    except (OSError, ValueError) as exc:
                        st.error(str(exc))
                    else:
                        st.rerun()
            st.markdown("**🌳 Grupos** (comparten diccionario y temas)")
            for g in usuarios.listar_grupos():
                c1, c2 = st.columns([0.8, 0.2])
                c1.caption(f"{g['grupo']}: {', '.join(g['miembros']) or 'sin miembros'}")
                if c2.button("🗑️", key=f"bg_del_{g['grupo']}", help="Borrar grupo (su diccionario se conserva en disco)"):
                    usuarios.borrar_grupo(g["grupo"])
                    st.cache_data.clear()
                    st.rerun()
            st.markdown("**➕ Meter un usuario en un grupo** (se crea si no existe)")
            with st.form("form_meter_grupo", clear_on_submit=True):
                u_sel = st.selectbox("Usuario:", [u["usuario"] for u in usuarios.listar()])
                g_txt = st.text_input("Grupo:", placeholder="p. ej. equipo1")
                if st.form_submit_button("Añadir al grupo"):
                    try:
                        usuarios.meter_en_grupo(u_sel, g_txt)
                    except (OSError, ValueError) as exc:
                        st.error(str(exc))
                    else:
                        st.cache_data.clear()
                        st.rerun()
            with st.form("form_grupo", clear_on_submit=True):
                nuevo_grupo = st.text_input("Nuevo grupo:")
                if st.form_submit_button("Crear grupo"):
                    try:
                        usuarios.crear_grupo(nuevo_grupo)
                    except (OSError, ValueError) as exc:
                        st.error(str(exc))
                    else:
                        st.rerun()
    with st.sidebar.expander("🔔 Alertas guardadas", expanded=bool(estado_usuario["busquedas"])):
        for b in estado_usuario["busquedas"]:
            nuevas, coinciden = contar_nuevas_busqueda(alertas_totales, b, cumple_busqueda_booleana_avanzada)
            etiqueta = f"🔔 {len(nuevas)} nuevas" if nuevas else f"{len(coinciden)} coincidencias"
            col_a, col_b = st.columns([0.8, 0.2])
            col_a.button(f"{b['nombre']} · {etiqueta}", key=f"bg_{b['nombre']}", on_click=_aplicar_busqueda, args=(b,), use_container_width=True, help=b["consulta"])
            col_b.button("🗑️", key=f"bd_{b['nombre']}", on_click=almacen.borrar_busqueda, args=(b["nombre"], usuario), help="Borrar esta alerta")
        nombre_busqueda = st.text_input("Nombre para la búsqueda actual", key="nombre_busqueda", placeholder="Ej.: Sabotaje Polonia")
        if st.button("💾 Guardar búsqueda actual", use_container_width=True):
            try:
                almacen.guardar_busqueda(nombre_busqueda, busqueda_txt, modo_busqueda, [x["id"] for x in alertas_totales if cumple_busqueda_booleana_avanzada(x, busqueda_txt, modo_busqueda)], usuario)
            except (OSError, ValueError) as exc:
                st.error(str(exc))
            else:
                st.rerun()
        if not estado_usuario["busquedas"]:
            st.caption("Guarda una búsqueda y te dirá cuántas noticias nuevas coinciden cada vez que abras la app.")

    with st.sidebar.expander("📧 Informe diario", expanded=False):
        asunto_diario, texto_diario, html_diario = construir_informe(alertas_totales)
        st.download_button("📥 Descargar informe de peligro alto (24 h)", data=html_diario, file_name=f"Informe_diario_{datetime.now(ZONA_MADRID).strftime('%Y%m%d')}.html", mime="text/html", use_container_width=True)
        try:
            _correo_usuario = usuarios.correo_de(usuario)
            _cfg_correo = configuracion_correo([_correo_usuario] if _correo_usuario else None)
            correo_listo = True
        except ValueError:
            correo_listo = False
        if st.button("✉️ Enviar por correo ahora", disabled=not correo_listo, use_container_width=True):
            try:
                enviar_correo(asunto_diario, texto_diario, html_diario, _cfg_correo)
                st.success("Correo enviado.")
            except (OSError, ValueError) as exc:
                st.error(f"No se pudo enviar: {exc}")
        if not correo_listo:
            st.caption("Correo sin configurar: define GAD_SMTP_HOST, GAD_MAIL_FROM y GAD_MAIL_TO (ver README).")
        elif _correo_usuario:
            st.caption(f"Se enviará a {_correo_usuario}.")
    # Barra de Herramientas y Exportación Única
    c_btn1, c_btn2, c_btn3 = st.columns([1.1, 1.6, 1.5])
    with c_btn1:
        carga_en_curso = (
            "carga_fuentes_future" in st.session_state
            and not st.session_state.carga_fuentes_future.done()
        )
        if st.button(
            "⏳ CARGANDO FUENTES" if carga_en_curso else "🔄 ACTUALIZAR FUENTES",
            type="primary",
            use_container_width=True,
            disabled=carga_en_curso,
        ):
            st.cache_data.clear()
            st.session_state.pop("carga_fuentes_error", None)
            if "alertas_base" in st.session_state:
                del st.session_state.alertas_base
            st.rerun()

    alertas_para_informe = [x for x in datos_filtrados if x["id"] in st.session_state.get("seleccionadas_ids", set())]

    with c_btn2:
        st.download_button(
            f"📥 GENERAR / DESCARGAR INFORME ({len(alertas_para_informe)})",
            data=generar_html_ejecutivo(alertas_para_informe, ventana_str=rango_tiempo),
            file_name=f"Informe_Amenazas_{datetime.now(ZONA_MADRID).strftime('%Y%m%d_%H%M')}.html",
            mime="text/html",
            use_container_width=True
        )

    with c_btn3:
        if "ultima_actualizacion" in st.session_state:
            st.markdown(f'<div style="font-size:12px;color:#94a3b8;margin-top:6px;">🕒 <strong>Actualizado:</strong> {st.session_state.ultima_actualizacion}<br>Mostrando <strong>{len(datos_filtrados)}</strong> alertas activas.</div>', unsafe_allow_html=True)

    with st.expander("📝 Resumen de la situación (según los filtros actuales)", expanded=False):
        resumen = resumir(
            [x for x in datos_filtrados if valoraciones.get(x["id"]) not in ("falsa", "irrelevante")],
            {c: n for c, n, _ in SECCIONES_INFORME},
            rango_tiempo,
        )
        st.markdown(f"**{resumen['titulo']}**")
        if resumen["total"]:
            st.markdown("**Las más relevantes (por peligro estimado):**")
            for d in resumen["destacadas"]:
                st.markdown(
                    f"- ⚠️ {d['peligro']}% · 🧭 {d['fiabilidad']}% · {enlace_md(d['titular'], d.get('enlace'))} "
                    f"— {_md_texto(d['canal'])} ({d['num_fuentes']} fuente/s)"
                    + ("" if d.get("enlace") else " _(sin enlace válido)_")
                )
        titulares_resumen = tuple(
            (d.get("id"), d["titular"]) for d in resumen["destacadas"]
        )
        resumen_traducido = st.session_state.get("resumen_traducido")
        if resumen_traducido and resumen_traducido[0] == titulares_resumen:
            traducciones = [x for x in resumen_traducido[1] if x[2] is not None]
            if traducciones:
                st.caption("🌐 Titulares traducidos al español")
                for original, traducido, _ in traducciones:
                    st.markdown(f"- **{_md_texto(original)}**  \n  {_md_texto(traducido)}")
            else:
                st.caption("🌐 Los titulares del resumen ya están en español.")
        elif st.button("🌐 Traducir resumen al español", key="btn_traducir_resumen"):
            try:
                with st.spinner("Traduciendo resumen..."):
                    traducciones = [
                        (original, *traducir_a_espanol(original))
                        for _, original in titulares_resumen
                    ]
                st.session_state.resumen_traducido = (titulares_resumen, traducciones)
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))
        st.caption(resumen["aviso"])
    st.caption("🧭 Fiabilidad y ⚠️ peligro: " + AVISO_INDICADORES + " Pasa el ratón por las barras para ver el porqué.")

    hilos = agrupar_hilos(datos_filtrados)
    with st.expander(f"🧵 Hilos de una historia ({len(hilos)})", expanded=False):
        if not hilos:
            st.caption("No hay noticias relacionadas entre sí con los filtros actuales.")
        for indice_hilo, h in enumerate(hilos):
            st.markdown(f"**{_md_texto(h['titular'])}** — {h['n']} noticias · ⚠️ {h['peligro']}% · {h['sociales']} canales sociales")
            titulares_hilo = tuple(
                (r.get("id"), r.get("titular", ""))
                for r in h["recorrido"] if r.get("titular")
            )
            clave_hilo = f"traduccion_hilo_{indice_hilo}"
            traduccion_hilo = st.session_state.get(clave_hilo)
            if traduccion_hilo and traduccion_hilo[0] == titulares_hilo:
                traducciones = [x for x in traduccion_hilo[1] if x[2] is not None]
                if traducciones:
                    st.caption("🌐 Titulares del hilo traducidos al español")
                    for original, traducido, _ in traducciones:
                        st.markdown(f"- **{_md_texto(original)}**  \n  {_md_texto(traducido)}")
                else:
                    st.caption("🌐 Los titulares del hilo ya están en español.")
            elif st.button("🌐 Traducir hilo al español", key=f"btn_{clave_hilo}"):
                try:
                    with st.spinner("Traduciendo hilo..."):
                        traducciones = [
                            (original, *traducir_a_espanol(original))
                            for _, original in titulares_hilo
                        ]
                    st.session_state[clave_hilo] = (titulares_hilo, traducciones)
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))
            for k, r in enumerate(h["recorrido"], 1):
                cuando = obtener_fecha_madrid_str(datetime.fromisoformat(r["fecha"])) if r["fecha"] else "fecha estimada"
                prefijo = "🥇 Primero: " if k == 1 else f"{k}. "
                st.markdown(f"- {prefijo}{_md_texto(r['canal'])} ({r['plataforma']}) · {cuando} · {enlace_md('ver', r['enlace'] if es_url_segura(r['enlace']) else '')}")

    def renderizar_tarjetas(lista_items, tab_key):
        lista_items = [x for x in lista_items if valoraciones.get(x["id"]) != "irrelevante"]
        if not lista_items:
            future = st.session_state.get("carga_fuentes_future")
            if future is not None and not future.done():
                st.info("Las fuentes siguen cargando; todavía no hay alertas para mostrar en esta sección.")
            else:
                st.info("No se registran alertas que cumplan los filtros.")
            return

        total_items = len(lista_items)
        
        # Manejo de paginación
        if noticias_por_pagina == "Todas":
            items_a_mostrar = lista_items
            pagina_actual = 1
            total_paginas = 1
        else:
            tam_pag = int(noticias_por_pagina)
            total_paginas = max(1, math.ceil(total_items / tam_pag))
            
            pag_key = f"pag_{tab_key}"
            if pag_key not in st.session_state:
                st.session_state[pag_key] = 1
                
            if st.session_state[pag_key] > total_paginas:
                st.session_state[pag_key] = total_paginas

            pagina_actual = st.session_state[pag_key]
            
            # Barra superior de navegación compacta
            def _barra_navegacion(posicion):
                col_nav1, col_nav2, col_nav3, col_nav4, col_nav5 = st.columns([0.8, 0.8, 2.4, 0.8, 0.8])
                with col_nav1:
                    if st.button("⏮️", key=f"btn_prim_{posicion}_{tab_key}", disabled=(pagina_actual <= 1), use_container_width=True, help="Primera página"):
                        st.session_state[pag_key] = 1
                        st.rerun()
                with col_nav2:
                    if st.button("◀️", key=f"btn_ant_{posicion}_{tab_key}", disabled=(pagina_actual <= 1), use_container_width=True, help="Página anterior"):
                        st.session_state[pag_key] -= 1
                        st.rerun()
                with col_nav3:
                    st.markdown(f'<div style="text-align: center; font-size: 13px; font-weight: 800; color: #38bdf8; padding-top: 6px;">Página {pagina_actual} de {total_paginas} &nbsp;({total_items} alertas)</div>', unsafe_allow_html=True)
                with col_nav4:
                    if st.button("▶️", key=f"btn_sig_{posicion}_{tab_key}", disabled=(pagina_actual >= total_paginas), use_container_width=True, help="Página siguiente"):
                        st.session_state[pag_key] += 1
                        st.rerun()
                with col_nav5:
                    if st.button("⏭️", key=f"btn_ult_{posicion}_{tab_key}", disabled=(pagina_actual >= total_paginas), use_container_width=True, help="Última página"):
                        st.session_state[pag_key] = total_paginas
                        st.rerun()

            _barra_navegacion("sup")

            inicio = (pagina_actual - 1) * tam_pag
            fin = inicio + tam_pag
            items_a_mostrar = lista_items[inicio:fin]

        for idx, item in enumerate(items_a_mostrar):
            cat = item.get("categoria", "GLOBAL")
            b_color = {
                "ESPANA": "#dc2626", "AGENCIAS": "#4f46e5", "EMPRESA": "#d97706", "GLOBAL": "#0f172a",
                "CRIPTO": "#7c3aed", "SANCIONES": "#b45309", "DETENCION": "#be123c",
                "CHINA": "#1e3a8a", "CRIMENES": "#991b1b", "DRONES": "#0284c7",
                "INJERENCIA": "#7c3aed", "OTAN": "#0369a1", "ASESINATOS": "#991b1b",
                "TELEGRAM": "#0284c7", "REDES": "#059669"
            }.get(cat, "#0f172a")

            badges = ""
            if item["id"] in nuevos_ids:
                badges += '<span class="badge-item" style="background:#16a34a;color:#fff;">🆕 NUEVO</span> '
            etiqueta_val = {"confirmada": "✅ CONFIRMADA", "falsa": "🚫 FALSA", "irrelevante": "💤 NO RELEVANTE"}.get(valoraciones.get(item["id"]))
            if etiqueta_val:
                badges += f'<span class="badge-item" style="background:#e2e8f0;color:#0f172a;">{etiqueta_val}</span> '
            if item["fecha_dt"]:
                if cumple_ventana_temporal(item["fecha_dt"], 6): badges += '<span class="badge-item" style="background:#fee2e2;color:#991b1b;">⚡ ÚLTIMAS 6 H</span> '
                elif cumple_ventana_temporal(item["fecha_dt"], 24): badges += '<span class="badge-item" style="background:#fee2e2;color:#991b1b;">⚡ 24H</span> '
                elif cumple_ventana_temporal(item["fecha_dt"], 48): badges += '<span class="badge-item" style="background:#fef08a;color:#854d0e;">🔥 48H</span> '
            if item.get("num_fuentes", 1) > 1:
                badges += f'<span class="badge-item" style="background:#dbeafe;color:#1e40af;">📰 {item["num_fuentes"]} FUENTES/CANALES</span> '
            if item.get("impacto_potencial"):
                badges += '<span class="badge-item" style="background:#ffedd5;color:#9a3412;">INDICIO TEXTUAL DE POSIBLE IMPACTO AMPLIO</span> '
            if item.get("coincidencia_personalizada"):
                termino_badge = html_module.escape(str(item["coincidencia_personalizada"]))
                badges += f'<span class="badge-item" style="background:#ede9fe;color:#5b21b6;">📚 TÉRMINO: {termino_badge}</span> '

            pildoras_ner = "".join([f'<span class="ner-pill" style="background-color:{c};">{html_module.escape(n)}</span>' for n, c in item.get("etiquetas_ner", [])])

            enlace_seguro = url_sanitizada(item.get("enlace", ""))

            pun = puntuar_con_aprendizaje(item, valoraciones, reputacion)
            def _barra(etiqueta, valor, color, motivos):
                ayuda = html_module.escape(" · ".join(motivos), quote=True)
                return (
                    f'<div title="{ayuda}" style="flex:1;min-width:150px;"><div style="font-size:11px;font-weight:800;color:#334155;">'
                    f'{etiqueta}: {valor}%</div><div style="background:#e2e8f0;border-radius:4px;height:8px;">'
                    f'<div style="width:{valor}%;background:{color};height:8px;border-radius:4px;"></div></div></div>'
                )
            col_f = "#16a34a" if pun["fiabilidad"] >= 66 else "#d97706" if pun["fiabilidad"] >= 40 else "#dc2626"
            col_p = "#dc2626" if pun["peligro"] >= 66 else "#d97706" if pun["peligro"] >= 40 else "#16a34a"
            indicadores = (
                '<div style="display:flex;gap:16px;margin-bottom:8px;">'
                + _barra("🧭 Fiabilidad estimada", pun["fiabilidad"], col_f, pun["motivos_fiabilidad"])
                + _barra("⚠️ Peligro estimado", pun["peligro"], col_p, pun["motivos_peligro"])
                + '</div>'
            )
            
            titular_resaltado = resaltar_coincidencias(item["titular"], busqueda_txt, modo_busqueda)
            cuerpo_resaltado = resaltar_coincidencias(item.get("cuerpo", ""), busqueda_txt, modo_busqueda)
            fecha_str = obtener_fecha_madrid_str(item["fecha_dt"]) if item["fecha_dt"] else "Fecha estimada"

            media_html = ""
            if item.get("multimedia") and es_url_segura(item["multimedia"]):
                media_html = f'<div style="flex: 0 0 280px; max-width: 280px; margin-right: 18px;"><img src="{html_module.escape(item["multimedia"])}" referrerpolicy="no-referrer" loading="lazy" style="width: 100%; border-radius: 6px; max-height: 220px; object-fit: cover;" /></div>'

            bloque_texto = ""
            if item.get("plataforma") in ["TELEGRAM", "REDES"]:
                bloque_texto = f'<div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 14px; color: #1e293b; font-size: 13.5px; line-height: 1.55; text-align: justify; margin-bottom: 8px; white-space: pre-wrap;"><strong>📄 Reporte / Contenido:</strong><br>{cuerpo_resaltado}</div>'
            elif item.get("cuerpo") and len(item.get("cuerpo")) > 15:
                cuerpo_recortado = item.get("cuerpo")[:350] + ("..." if len(item.get("cuerpo")) > 350 else "")
                bloque_texto = f'<div style="background-color: #f8fafc; border: 1px solid #f1f5f9; border-radius: 6px; padding: 8px 12px; color: #334155; font-size: 13px; line-height: 1.5; margin-bottom: 8px;">{resaltar_coincidencias(cuerpo_recortado, busqueda_txt, modo_busqueda)}</div>'

            partes_html = [
                f'<div class="threat-card" style="border-left: 8px solid {b_color};">',
                f'<div style="display: flex; flex-wrap: wrap; align-items: flex-start;">',
                media_html,
                f'<div style="flex: 1; min-width: 260px;">',
                f'<div style="font-size:12px;color:#64748b;margin-bottom:8px;">{badges} 📅 {fecha_str} | 📢 {html_module.escape(item["canal"])}</div>',
                f'<div style="font-size:17px;font-weight:850;color:#0f172a;margin-bottom:8px;">{titular_resaltado}</div>',
                f'<div style="margin-bottom:8px;">{pildoras_ner}</div>',
                indicadores,
                bloque_texto,
                f'<div style="background:#f0f9ff;border-left:4px solid #0284c7;padding:8px 12px;color:#0c4a6e;font-size:13px;margin-bottom:10px;">{html_module.escape(item["evaluacion_contexto"])}</div>',
                f'<a href="{enlace_seguro}" target="_blank" rel="noopener noreferrer" class="btn-source">🔗 ABRIR FUENTE ORIGINAL</a>',
                f'</div>',
                f'</div>',
                f'</div>'
            ]
            html_card = "".join(partes_html)

            c_chk, c_card = st.columns([0.05, 0.95])
            with c_chk:
                marcado = item["id"] in st.session_state.seleccionadas_ids
                nuevo_estado = st.checkbox("Sel", value=marcado, key=f"chk_{tab_key}_{item['id']}", label_visibility="collapsed")
                if nuevo_estado != marcado:
                    if nuevo_estado: st.session_state.seleccionadas_ids.add(item["id"])
                    else: st.session_state.seleccionadas_ids.discard(item["id"])
                    st.rerun()

            with c_card:
                st.markdown(html_card, unsafe_allow_html=True)
                actual = valoraciones.get(item["id"])
                cv = st.columns([1, 1, 1, 1, 2])
                for col, (clave, texto) in zip(cv, (("confirmada", "✅ Confirmada"), ("falsa", "🚫 Falsa"), ("irrelevante", "💤 No relevante"))):
                    col.button(texto, key=f"val_{clave}_{tab_key}_{item['id']}", on_click=_valorar, args=(item["id"], clave), disabled=(actual == clave), use_container_width=True)
                if actual:
                    cv[3].button("↩️ Quitar", key=f"val_q_{tab_key}_{item['id']}", on_click=_valorar, args=(item["id"], None), use_container_width=True)
                clave_trad = f"trad_{item['id']}"
                if clave_trad in st.session_state:
                    tit_es, cue_es, idioma_orig = st.session_state[clave_trad]
                    if idioma_orig is None:
                        st.caption("🌐 Esta noticia ya está en español.")
                    else:
                        cuerpo_es = f"<br>{html_module.escape(cue_es)}" if cue_es else ""
                        st.markdown(
                            f'<div style="background:#ecfdf5;border-left:4px solid #059669;padding:8px 12px;color:#064e3b;font-size:13.5px;margin-bottom:8px;">'
                            f'<strong>🌐 Traducción automática ({idioma_orig} → es):</strong><br>'
                            f'<strong>{html_module.escape(tit_es)}</strong>{cuerpo_es}</div>',
                            unsafe_allow_html=True,
                        )
                elif st.button("🌐 Traducir al español", key=f"btn_trad_{tab_key}_{item['id']}"):
                    try:
                        with st.spinner("Traduciendo..."):
                            tit_es, idioma_orig = traducir_a_espanol(item["titular"])
                            cue_es = ""
                            if idioma_orig is not None and item.get("cuerpo"):
                                cue_es, _ = traducir_a_espanol(item["cuerpo"][:600])
                        st.session_state[clave_trad] = (tit_es, cue_es, idioma_orig)
                        st.rerun()
                    except RuntimeError as exc:
                        st.error(str(exc))
                if item.get("fuentes_coincidentes"):
                    with st.expander(f"📑 Coberturas coincidentes ({len(item['fuentes_coincidentes'])} fuentes adicionales)"):
                        for f_sec in item["fuentes_coincidentes"]:
                            sec_link = url_sanitizada(f_sec.get('enlace', ''))
                            f_fecha_str = obtener_fecha_madrid_str(f_sec.get('fecha_dt')) if f_sec.get('fecha_dt') else "Fecha reciente"
                            st.markdown(f"""
                            <div class="secondary-box">
                                <div style="font-size: 11px; color: #1e40af; font-weight: 700;">📢 {html_module.escape(f_sec['canal'])} &nbsp;|&nbsp; 📅 {f_fecha_str}</div>
                                <div style="font-size: 13.5px; font-weight: 700; color: #0f172a; margin: 3px 0 6px 0;">{html_module.escape(f_sec['titular'])}</div>
                                <a href="{sec_link}" target="_blank" style="font-size: 11.5px; font-weight: 800; color: #2563eb; text-decoration: underline;">🔗 Abrir este medio &rarr;</a>
                            </div>
                            """, unsafe_allow_html=True)

        if noticias_por_pagina != "Todas" and total_paginas > 1:
            _barra_navegacion("inf")

    secciones_ui = [
        ("ESPANA", "🇪🇸 ESPAÑA"), ("AGENCIAS", "🕵️‍♂️ AGENCIAS"), ("EMPRESA", "🏢 EMPRESAS"),
        ("GLOBAL", "📰 GLOBAL"), ("CRIPTO", "🟣 CRIPTO"), ("SANCIONES", "📦 SANCIONES"),
        ("DETENCION", "🛑 DETENCIONES"), ("CHINA", "🇨🇳 CHINA"), ("CRIMENES", "⚖️ CRÍMENES"),
        ("DRONES", "🛸 DRONES"), ("INJERENCIA", "🗳️ INJERENCIA"), ("OTAN", "🛡️ OTAN"),
        ("ASESINATOS", "🔎 ASESINATOS"),
        ("TELEGRAM", "✈️ TELEGRAM"), ("REDES", "🌐 REDES"),
    ]
    secciones_ui = [s for s in secciones_ui if secciones_visibles is None or s[0] in secciones_visibles]
    if st.session_state.get("seccion_activa") == "SHARIJ":
        st.session_state.seccion_activa = "GLOBAL"
    listas = {codigo: [] for codigo, _ in secciones_ui}
    for item in datos_filtrados:
        codigo = item["categoria"]
        if codigo in listas and codigo not in ("TELEGRAM", "REDES"):
            listas[codigo].append(item)
        telegram_propio_sharij = (
            item["plataforma"] == "TELEGRAM"
            and "asupersharij" in str(item.get("canal", "")).lower()
        )
        if "TELEGRAM" in listas and (
            codigo == "TELEGRAM"
            or (item["plataforma"] == "TELEGRAM" and not telegram_propio_sharij)
        ):
            listas["TELEGRAM"].append(item)
        if "REDES" in listas and (codigo == "REDES" or item["plataforma"] == "REDES"):
            listas["REDES"].append(item)

    if secciones_ui:
        etiquetas_ui = dict(secciones_ui)
        seccion_activa = st.radio(
            "Sección",
            [codigo for codigo, _ in secciones_ui],
            horizontal=True,
            key="seccion_activa",
            format_func=lambda codigo: f"{etiquetas_ui[codigo]} ({len(listas[codigo])})",
            label_visibility="collapsed",
        )
        lista_activa = listas[seccion_activa]
        if seccion_activa == "REDES":
            opciones = ["TODOS", "MASTODON", "YOUTUBE"] + list(PERFILES)
            ids_vistos = {x["id"] for x in lista_activa}
            if not busqueda_txt:
                ultimas_vigiladas = {}
                for x in alertas_totales:
                    canal_vig = perfil_de_canal(x["canal"])
                    if canal_vig and x["id"] not in ids_vistos and x["plataforma"] == "TELEGRAM":
                        ultimas_vigiladas.setdefault(x["canal"], []).append(x)
                extra = [x for lista in ultimas_vigiladas.values() for x in lista[:5]]
                if extra:
                    lista_activa = sorted(
                        lista_activa + extra,
                        key=lambda x: x["fecha_dt"] or datetime.min.replace(tzinfo=timezone.utc),
                        reverse=True,
                    )

            def _es_mastodon(x):
                return str(x.get("canal", "")).startswith("Mastodon")

            def _es_youtube(x):
                return "youtube" in str(x.get("canal", "")).lower()

            def _etiqueta_perfil(c):
                if c == "TODOS":
                    return "Todos (incluye los últimos mensajes de los canales vigilados)"
                if c == "MASTODON":
                    return f"🐘 Mastodon ({sum(1 for x in alertas_totales if _es_mastodon(x))})"
                if c == "YOUTUBE":
                    return f"▶️ YouTube ({sum(1 for x in alertas_totales if _es_youtube(x))})"
                return f"{PERFILES[c]['etiqueta']} ({sum(1 for x in alertas_totales if c in x.get('perfiles', []))})"

            perfil_sel = st.selectbox("👁️ Perfil o fuente", opciones, key="perfil_vigilado", format_func=_etiqueta_perfil)
            if perfil_sel == "MASTODON":
                lista_activa = [x for x in datos_filtrados if _es_mastodon(x)]
            elif perfil_sel == "YOUTUBE":
                lista_activa = [x for x in datos_filtrados if _es_youtube(x)]
            elif perfil_sel != "TODOS":
                st.caption(PERFILES[perfil_sel]["descripcion"] + " · se muestra todo el histórico, sin filtro de fechas")
                lista_activa = [x for x in alertas_totales if perfil_sel in x.get("perfiles", [])]

            etiqueta_resumen = {"TODOS": "todas las redes", "MASTODON": "Mastodon", "YOUTUBE": "YouTube"}.get(
                perfil_sel, PERFILES.get(perfil_sel, {}).get("etiqueta", "")
            )
            with st.expander(f"📝 Resumen: de qué se habla en {etiqueta_resumen}", expanded=False):
                res_redes = resumen_redes(
                    [x for x in lista_activa if valoraciones.get(x["id"]) not in ("falsa", "irrelevante")]
                )
                st.markdown(res_redes["intro"])
                clave_trad = f"resumen_redes_trad_{perfil_sel}"
                traducidos = st.session_state.get(clave_trad)
                if traducidos and traducidos[0] == len(res_redes["parrafos"]):
                    textos_mostrar = traducidos[1]
                else:
                    textos_mostrar = [p["texto"] for p in res_redes["parrafos"]]
                for p, texto in zip(res_redes["parrafos"], textos_mostrar):
                    st.markdown(_md_texto(texto))
                    for e in p["enlaces"]:
                        st.markdown(f"- **{e['motivo']}:** {enlace_md(e['titular'], e['enlace'])}")
                if res_redes["parrafos"] and not traducidos and st.button("🌐 Traducir resumen al español", key=f"btn_trad_redes_{perfil_sel}"):
                    try:
                        with st.spinner("Traduciendo resumen..."):
                            textos = [traducir_a_espanol(p["texto"])[0] or p["texto"] for p in res_redes["parrafos"]]
                        st.session_state[clave_trad] = (len(textos), textos)
                        st.rerun()
                    except RuntimeError as exc:
                        st.error(str(exc))
                st.caption("Resumen automático por temas; no verifica los hechos. Los enlaces llevan a las publicaciones citadas.")
        renderizar_tarjetas(lista_activa, f"{seccion_activa.lower()}_{st.session_state.get('perfil_vigilado', 'TODOS')}" if seccion_activa == "REDES" else seccion_activa.lower())
