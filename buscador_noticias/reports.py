import html as html_module

from .config import SECCIONES_INFORME
from .processing import obtener_fecha_madrid_str, url_sanitizada

def generar_html_ejecutivo(alertas, ventana_str="GENERAL"):
    fecha_actual = obtener_fecha_madrid_str()
    
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe Buscador de Amenazas Híbridas</title>
    <style>
        @page {{ size: A4 portrait; margin: 10mm; }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background-color: #0b0f19; color: #0f172a; margin: 0; padding: 20px; line-height: 1.35;
        }}
        #contenedor-reporte {{
            max-width: 900px; margin: 0 auto; background: #ffffff; padding: 26px;
            border: 1px solid #cbd5e1; border-radius: 8px;
        }}
        .toolbar {{
            max-width: 900px; margin: 0 auto 16px auto; display: flex;
            justify-content: space-between; align-items: center; background: #1e293b;
            padding: 12px 18px; border-radius: 8px; border: 1px solid #334155; color: #ffffff;
        }}
        .btn-action {{
            background: #0284c7; color: #ffffff; border: none; padding: 8px 16px;
            font-size: 13px; font-weight: 800; border-radius: 6px; cursor: pointer; margin-left: 6px;
        }}
        .btn-print {{
            background: #dc2626; color: #ffffff; border: none; padding: 8px 16px;
            font-size: 13px; font-weight: 800; border-radius: 6px; cursor: pointer; margin-left: 6px;
        }}
        @media print {{
            body {{ background: #ffffff !important; padding: 0 !important; }}
            .toolbar {{ display: none !important; }}
            #contenedor-reporte {{ border: none !important; padding: 0 !important; width: 100% !important; }}
            .card {{ page-break-inside: avoid !important; margin-bottom: 6px !important; }}
        }}
        .header {{
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #ffffff; border-left: 8px solid #dc2626; padding: 16px 20px; margin-bottom: 16px; border-radius: 6px;
        }}
        .header h1 {{ margin: 0 0 4px 0; font-size: 18px; text-transform: uppercase; }}
        .header p {{ margin: 0; color: #cbd5e1; font-size: 12px; }}
        .card {{
            background: #ffffff; border: 1px solid #cbd5e1; border-left-width: 6px;
            border-left-style: solid; padding: 12px 16px; margin-bottom: 10px; border-radius: 4px;
        }}
        .card h3 {{ margin: 0 0 6px 0; font-size: 15px; color: #0f172a; line-height: 1.35; }}
        .meta {{ font-size: 11px; color: #64748b; font-weight: 700; margin-bottom: 6px; }}
        .cuerpo-box {{
            background: #f8fafc; border: 1px solid #e2e8f0; padding: 8px 12px;
            font-size: 12.5px; color: #1e293b; margin-bottom: 6px; text-align: justify; line-height: 1.45; white-space: pre-wrap;
        }}
        .analisis-box {{
            background: #f0f9ff; border-left: 3px solid #0284c7; padding: 6px 10px;
            font-size: 12px; color: #0c4a6e; margin-bottom: 6px;
        }}
        .link-button {{ color: #0284c7 !important; font-size: 11px; font-weight: 700; text-decoration: underline !important; }}
    </style>
    <script type="text/javascript">
        function googleTranslateElementInit() {{
            new google.translate.TranslateElement({{pageLanguage: 'auto', includedLanguages: 'es', layout: google.translate.TranslateElement.InlineLayout.SIMPLE}}, 'google_translate_element');
        }}
        function exportarWord() {{
            var header = "<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'><head><meta charset='utf-8'><title>Informe</title></head><body>";
            var footer = "</body></html>";
            var sourceHTML = header + document.getElementById("contenedor-reporte").innerHTML + footer;
            var source = 'data:application/vnd.ms-word;charset=utf-8,' + encodeURIComponent(sourceHTML);
            var fileDownload = document.createElement("a");
            document.body.appendChild(fileDownload);
            fileDownload.href = source;
            fileDownload.download = 'Informe_Amenazas.doc';
            fileDownload.click();
            document.body.removeChild(fileDownload);
        }}
    </script>
    <script type="text/javascript" src="//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"></script>
</head>
<body>
    <div class="toolbar">
        <div><span id="google_translate_element"></span></div>
        <div>
            <button class="btn-action" onclick="exportarWord()">📝 GUARDAR EN WORD (.DOC)</button>
            <button class="btn-print" onclick="window.print()">🖨️ IMPRIMIR / GUARDAR PDF</button>
        </div>
    </div>
    <div id="contenedor-reporte">
        <div class="header">
            <h1>BUSCADOR DE AMENAZAS HÍBRIDAS</h1>
            <p>INFORME DE SITUACIÓN | Ventana: {ventana_str} | Emisión: {fecha_actual} (Madrid)</p>
        </div>"""

    for cat_cod, cat_nombre, cat_color in SECCIONES_INFORME:
        items_seccion = [a for a in alertas if a.get("categoria") == cat_cod]
        if not items_seccion: continue
        html += f"""
        <div style="background-color: {cat_color}; color:#fff; font-size:12px; font-weight:900; padding:6px 12px; margin:14px 0 8px 0; text-transform:uppercase; border-radius:3px;">
            {cat_nombre} ({len(items_seccion)})
        </div>"""
        for a in items_seccion:
            tit = html_module.escape(str(a.get('titular', '')))
            hecho = html_module.escape(str(a.get('cuerpo', '')))
            ana = html_module.escape(str(a.get('evaluacion_contexto', '')))
            f_str = obtener_fecha_madrid_str(a["fecha_dt"]) if a["fecha_dt"] else "Fecha estimada"
            canal = html_module.escape(str(a.get('canal', '')))
            enlace = url_sanitizada(a.get('enlace', '#'))
            num_fuentes = a.get("num_fuentes", 1)
            impacto_html = (
                '<div class="meta">Indicador textual: posible impacto amplio; requiere verificar el contexto.</div>'
                if a.get("impacto_potencial") else ""
            )

            cuerpo_html = f'<div class="cuerpo-box"><strong>Reporte / Contenido:</strong><br>{hecho}</div>' if hecho else ""

            html += f"""
            <div class="card" style="border-left-color: {cat_color};">
                <div class="meta">📅 {f_str} | 📢 {canal} | Fuentes/canales detectados: {num_fuentes}</div>
                <h3>{tit}</h3>
                {impacto_html}
                {cuerpo_html}
                <div class="analisis-box"><strong>Evaluación:</strong> {ana}</div>
                <div><a href="{enlace}" target="_blank" class="link-button">🔗 Fuente original en {canal} &rarr;</a></div>
            </div>"""
    html += "</div></body></html>"
    return html.encode('utf-8-sig')
