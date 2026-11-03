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
        self.assertTrue(primero["enlaces"])
        self.assertNotIn("http", primero["texto"])

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
