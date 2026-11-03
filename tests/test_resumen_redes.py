import unittest
from datetime import datetime, timezone

from buscador_noticias.processing import es_eje_hostil
from buscador_noticias.resumen import resumen_redes


def _a(canal, texto, dia=28):
    return {
        "canal": canal, "cuerpo": texto, "titular": texto[:50],
        "fecha_dt": datetime(2026, 10, dia, 10, tzinfo=timezone.utc),
        "enlace": f"https://t.me/{canal.lstrip('@')}/{dia}{len(texto)}",
    }


class ResumenRedesTests(unittest.TestCase):
    def test_parrafo_escrito_con_temas_y_enlaces(self):
        alertas = [
            _a("@uno", "Buscamos informadores dentro del gobierno italiano https://t.me/x/1 #italia para la crisis.", 26),
            _a("@uno", "El gobierno italiano oculta farmacias vacías y busca colaboradores en la crisis sanitaria.", 27),
            _a("@dos", "Visita al puerto de Marsella para hablar de comercio marítimo y logística en el Mediterráneo."),
        ]
        r = resumen_redes(alertas)
        self.assertIn("3 publicaciones", r["intro"])
        primero = r["parrafos"][0]
        self.assertIn("@uno publicó 2 mensajes entre el 26/10 y el 27/10", primero["texto"])
        self.assertIn("informadores y colaboradores", primero["texto"])
        self.assertNotIn("palabras que más repite", primero["texto"])
        self.assertTrue(primero["enlaces"])
        self.assertNotIn("http", primero["texto"])

    def test_enlace_mas_visto_y_espana(self):
        a1 = _a("@uno", "Mensaje largo sobre la guerra en el frente de Ucrania y la OTAN hoy.", 26)
        a2 = _a("@uno", "Moncloa y el Gobierno de España preparan nuevas medidas ante el Kremlin.", 27)
        a3 = _a("@uno", "Canal en español con noticias del mundo y de la guerra en Ucrania siempre.", 28)
        a1["vistas"], a2["vistas"], a3["vistas"] = 5000, 100, 9000
        enlaces = resumen_redes([a1, a2, a3])["parrafos"][0]["enlaces"]
        motivos = {e["motivo"]: e["enlace"] for e in enlaces}
        self.assertEqual(motivos["Más visto (9.000 visualizaciones)"], a3["enlace"])
        self.assertEqual(motivos["Sobre España"], a2["enlace"])

    def test_vacio(self):
        self.assertEqual(resumen_redes([])["parrafos"], [])


class EjeHostilTests(unittest.TestCase):
    def test_exige_rusia_ucrania_china(self):
        self.assertTrue(es_eje_hostil("#russia sabotage on rail lines"))
        self.assertTrue(es_eje_hostil("Chinese APT targets telecoms"))
        self.assertFalse(es_eje_hostil("Iran-linked hackers hit hospitals"))
        self.assertFalse(es_eje_hostil("North Korea steals crypto"))
        self.assertFalse(es_eje_hostil("New ransomware advisory from CISA"))


if __name__ == "__main__":
    unittest.main()
