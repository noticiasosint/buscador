import re

LOGO_FONDO_SVG = """data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none"><circle cx="50" cy="50" r="47" stroke="%2338bdf8" stroke-width="1.5" stroke-dasharray="3 3" opacity="0.35" /><path d="M50 14 L75 25 V52 C75 69 50 84 50 84 C50 84 25 69 25 52 V25 Z" fill="%230f172a" stroke="%2338bdf8" stroke-width="2" opacity="0.45" /><polygon points="53,24 37,48 48,48 43,72 61,44 51,44" fill="%23ef4444" opacity="0.4" /></svg>"""

LOGO_OFICIAL_SVG = """<svg width="85" height="85" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="50" cy="50" r="47" fill="#1e293b" stroke="#334155" stroke-width="2" />
    <circle cx="50" cy="50" r="40" stroke="#38bdf8" stroke-width="1.5" stroke-dasharray="3 3" opacity="0.8" />
    <path d="M50 14 L75 25 V52 C75 69 50 84 50 84 C50 84 25 69 25 52 V25 Z" fill="#0f172a" stroke="#38bdf8" stroke-width="2.5" />
    <polygon points="53,24 37,48 48,48 43,72 61,44 51,44" fill="#ef4444" />
</svg>"""

EMPRESAS_ESTRATEGICAS_ESP = [
    "destinus", "mikhail kokorich", "kokorich", "uav navigation", "grupo oesia", "oesia", "odesia",
    "tecnobit", "indra", "navantia", "escribano", "em&e", "sener", "arquimea",
    "santa barbara sistemas", "santa barbara", "gdels", "expal", "rheinmetall expal", "instalaza", "sapla", "urovesa",
    "itp aero", "airbus espana", "airbus getafe", "hisdesat", "hispasat", "sateliot", "pld space", "talgo"
]

PATRON_AGENCIAS = re.compile(
    r'\b('
    r'cia\b|cni\b|centro nacional de inteligencia|mi5\b|mi6\b|gchq\b|ken mccallum|william burns|'
    r'bfv\b|bnd\b|dgsi\b|dgse\b|abw\b|kapo\b|vsd\b|supo\b|mossad\b|fbi\b|nsa\b|sbu\b|fsb\b|gru\b|svr\b|mss\b|alerta de la cia|informe de la cia|'
    r'inteligencia britanica|inteligencia estadounidense|inteligencia alemana|inteligencia francesa'
    r')\b', re.IGNORECASE
)

PATRON_CHINA = re.compile(
    r'\b('
    r'china|chino\w*|chinese|pekin|beijing|xi jinping|pcc|pla|taiwan|taipei|canton|hong kong|'
    r'apt41|volt typhoon|flax typhoon|mustang panda|salt typhoon|mss|ciberespionaje chino|injerencia china|'
    r'espionaje chino|espia chino|espias chinos|sabotaje chino|guerra hibrida china|comisarias secretas|'
    r'topos chinos|infiltracion china|'
    r'الصين|بكين|تجسس صيني' # China, Beijing, Espionaje chino en Árabe
    r')\b', re.IGNORECASE
)

RAICES_CHINO = ["中国", "北京", "习近平", "解放军", "台湾", "华为", "国安部", "间谍", "黑客", "网络攻击"]

PATRON_RUSIA_UCRANIA = re.compile(
    r'\b('
    r'rusia|ruso\w*|russia\w*|moscu|moscow|kremlin|putin|'
    r'gru|fsb|svr|apt28|apt29|fancy bear|cozy bear|sandworm|noname057\w*|killnet|turla|garantex|wagner|'
    r'bielorrusia|belarus|kaliningrado|lukashenko|estonia|letonia|lituania|moldavia|moldova|'
    r'georgia|armenia|azerbaiyan|kazajistan|kirguistan|tayikistan|uzbekistan|turkmenistan|'
    r'estonian\w*|latvian\w*|lithuanian\w*|georgian\w*|armenian\w*|kazakh\w*|'
    r'эстони\w*|латви\w*|литв\w*|молдов\w*|грузин\w*|армян\w*|азербайджан\w*|'
    r'казахстан\w*|кыргызстан\w*|таджикистан\w*|узбекистан\w*|туркменистан\w*|'
    r'ucrania|ucranian\w*|ukraine\w*|zelensky|zelenski|zsu|vsu|sbu|gur|hur|'
    r'kursk|belgorod|donbas\w*|crimea|zaporiyia|zaporizhzhia|kherson|donetsk|lugansk|luhansk|jarkov|kharkiv|'
    r'shariy|sharij|rybar|zvinchuk|'
    r'mar negro|black sea|bloqueo naval|drones pirata|'
    r'россия|российск\w*|рф|кремль|путин|гру|фсб|свр|украин\w*|вагнер|шарий|шарій|'
    r'روسيا|بوتين|موسكو|أوكرانيا' # Rusia, Putin, Moscú, Ucrania en Árabe
    r')\b', re.IGNORECASE
)

# Filtro estricto para Oriente Medio
PATRON_PAISES_AJENOS = re.compile(
    r'\b('
    r'marruecos|marroqui\w*|rabat|mohamed vi|pegasus.*marruecos|sahara occidental|polisario|argelia|argelino\w*|'
    r'gaza|hamas|hezbollah|hezbola|netanyahu|tel aviv|cisjordania|palestina|israel|israeli|'
    r'yemen|huti|huties|siria|damasco'
    r')\b', re.IGNORECASE
)

# Raíces multilingües
PATRON_DETENCION_MULTI = re.compile(
    r'\b('
    r'detenido|detenida|detenidos|detencion|arrestado|arresto|arrested|arrests?|'
    r'zatrzymany|zatrzymano|aresztowany|aresztowano|'
    r'задержан|задержали|арестован|арестовали|'
    r'затримано|заарештовано|затримали|'
    r'اعتقال|احتجاز|القبض على' # Detención/Arresto en Árabe
    r')\b', re.IGNORECASE
)

PATRON_CRIMENES_MULTI = re.compile(
    r'\b('
    r'crimen de guerra|crímenes de guerra|cpi|icc|corte penal|lesa humanidad|genocidio|masacre|fosa comun|deportacion forzosa|tortura\w*|'
    r'robo de grano|silos de grano|grano ucraniano|ecocidio|ataque a gasoducto|'
    r'war crimes?|crimes against humanity|grain theft|grain silos|ecocide|'
    r'военные преступления|экоцид|кража зерна|зерновые терминалы|казнь|пытки|'
    r'воєнні злочини|екоцид|викрадення зерна|зерновий коридор|масові поховання|'
    r'جرائم حرب|المحكمة الجنائية الدولية|إبادة جماعية' # Crímenes en Árabe
    r')\b', re.IGNORECASE
)

PATRON_DRONES_MULTI = re.compile(
    r'\b('
    r'dron\w*|drone\w*|uav\w*|shahed\w*|geran\w*|lancet\w*|fpv\b|enjambre\w* de drones|'
    r'bpla|бпла|дрон\w*|шахед\w*|герань\w*|ланцет\w*|'
    r'bezpilotnik|kamikaze drone|'
    r'طائرة مسيرة|مسيرات|طائرات بدون طيار' # Drones/UAVs en Árabe
    r')\b', re.IGNORECASE
)

PATRON_DESINFORMACION_MULTI = re.compile(
    r'\b('
    r'desinformaci\w*|injerenci\w*|fimi|doppelganger|'
    r'operaci\w* de influenci\w*|campan\w* de desinformaci\w*|'
    r'disinformation|foreign influence|influence operation|election interference|'
    r'information operation|'
    r'дезинформац\w*|вмешательств\w*|операци\w* влияни\w*|'
    r'дезінформац\w*|втручанн\w*|операці\w* вплив\w*|'
    r'تضليل|تدخل أجنبي|حملة تضليل|عملية تأثير'
    r')\b', re.IGNORECASE
)

PATRON_SABOTAJE_MULTI = re.compile(
    r'\b('
    r'sabotaj\w*|sabotage|arson|dywers\w*|диверси\w*|саботаж\w*|'
    r'диверсант\w*|підпал\w*|تخريب|تدمير متعمد'
    r')\b', re.IGNORECASE
)

PATRON_TERRORISMO_MULTI = re.compile(
    r'\b('
    r'terroris\w*|atentad\w*|ataque terrorista|terror attack|bombing|'
    r'терроризм|террорист\w*|теракт\w*|'
    r'тероризм|терорист\w*|теракт\w*|'
    r'إرهاب|إرهابي|هجوم إرهابي|تفجير إرهابي'
    r')\b', re.IGNORECASE
)

PATRON_IMPACTO_MULTILINGUE = re.compile(
    r'\b('
    r'evacuaci\w*|victim\w*|herid\w*|fallecid\w*|muert\w*|'
    r'infraestructura critica|apag\w*|corte de energia|red electrica|'
    r'cables? submarinos?|oleoduct\w*|aeropuert\w*|puert\w*|'
    r'casualt\w*|injur\w*|fatalit\w*|evacuat\w*|critical infrastructure|'
    r'widespread outage|power grid|undersea cables?|pipeline\w*|'
    r'airport\w*|state of emergency|'
    r'эвакуац\w*|жертв\w*|пострадавш\w*|погиб\w*|отключен\w*|'
    r'инфраструктур\w*|'
    r'евакуац\w*|загибл\w*|постраждал\w*|відключен\w*|'
    r'інфраструктур\w*|'
    r'إجلاء|إخلاء|ضحايا|قتلى|جرحى|انفجار|بنية تحتية حرجة|'
    r'انقطاع واسع|شبكة الكهرباء'
    r')\b', re.IGNORECASE
)

SINONIMOS_MULTILINGUES = {
    "incendio": ["incendio", "incendios", "fire", "fires", "arson", "поджог", "пожар", "feuer", "brand"],
    "fuego": ["fuego", "fire", "arson", "поджог", "пожар", "feuer"],
    "sabotaje": ["sabotaje", "sabotajes", "sabotage", "диверсия", "саботаж", "saboteur", "dywersja", "sabotaż", "تخريب"],
    "espia": ["espia", "espias", "spy", "spies", "espionage", "spying", "шпион", "шпионаж", "szpieg", "шпигун", "جاسوس"],
    "espionaje": ["espionaje", "espia", "espionage", "spying", "шпионаж", "шпион", "szpiegostwo", "تجسس"],
    "anatolii": ["anatolii", "anatoli", "anatoly", "sharij", "shariy", "шарий", "шарій", "saharij", "saharii"],
    "sharij": ["sharij", "shariy", "anatolii", "anatoly", "шарий", "шарій"],
    "dron": ["dron", "drones", "drone", "uav", "бпла", "дрон", "шахед", "shahed", "geran", "طائرة مسيرة", "مسيرات"],
    "asesinato": ["asesinato", "sicario", "targeted killing", "assassination", "убийство", "казнь", "اغتيال"],
    "blanqueo": ["blanqueo", "lavado", "money laundering", "отмывание", "garantex"],
    "sancion": ["sancion", "sanciones", "sanction", "sanctions", "санкции", "ofac", "عقوبات"],
    "yuzuk": ["yuzuk", "operacion yuzuk"],
    "cni": ["cni", "centro nacional de inteligencia"],
    "cia": ["cia", "central intelligence agency"],
    "grano": ["grano", "cereal", "grain", "silos", "зерно", "хлеб", "ecocidio", "قمح"]
}

SECCIONES_INFORME = [
    ("ESPANA", "SECCIÓN 1: ESPAÑA E INFRAESTRUCTURAS CRÍTICAS", "#dc2626"),
    ("AGENCIAS", "SECCIÓN 2: AGENCIAS DE INTELIGENCIA (CIA, CNI, MI6, ETC.)", "#4f46e5"),
    ("EMPRESA", "SECCIÓN 3: EMPRESAS ESTRATÉGICAS DE ESPAÑA Y DEFENSA", "#d97706"),
    ("GLOBAL", "SECCIÓN 4: RUSIA, UCRANIA, VOR V ZAKONE Y AMENAZAS GLOBALES", "#0f172a"),
    ("CRIPTO", "SECCIÓN 5: CRIPTOACTIVOS Y FINANCIACIÓN ILÍCITA", "#7c3aed"),
    ("SANCIONES", "SECCIÓN 6: SANCIONES Y FLOTA FANTASMA", "#b45309"),
    ("DETENCION", "SECCIÓN 7: DETENCIONES POR ESPIONAJE Y SABOTAJE", "#be123c"),
    ("CHINA", "SECCIÓN 8: CHINA E INJERENCIA ESTRATÉGICA", "#1e3a8a"),
    ("CRIMENES", "SECCIÓN 9: CRÍMENES DE GUERRA, GRANO Y DERECHOS HUMANOS", "#991b1b"),
    ("DRONES", "SECCIÓN 10: GUERRA AÉREA Y DRONES", "#0284c7"),
    ("TELEGRAM", "SECCIÓN 11: TELEGRAM TÁCTICO", "#0284c7"),
    ("REDES", "SECCIÓN 12: REDES SOCIALES Y ANÁLISIS MULTIMEDIA", "#059669"),
    ("INJERENCIA", "SECCIÓN 13: INJERENCIA Y OPERACIONES DE INFLUENCIA", "#7c3aed"),
    ("OTAN", "SECCIÓN 14: OTAN Y AMENAZAS HÍBRIDAS", "#0369a1"),
    ("ASESINATOS", "SECCIÓN 15: ASESINATOS Y ENVENENAMIENTOS", "#991b1b"),
]
