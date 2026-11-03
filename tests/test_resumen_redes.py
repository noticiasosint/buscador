import unittest

from buscador_noticias.resumen import resumen_redes


def _a(canal, texto):
    return {"canal": canal, "cuerpo": texto, "titular": texto[:50]}


class ResumenRedesTests(unittest.TestCase):
    def test_resumen_sin_enlaces_y_con_temas(self):
        alertas = [
            _a("@uno", "El gobierno italiano oculta farmacias vacías https://t.me/x/1 #italia durante la crisis sanitaria."),
            _a("@uno", "Farmacias italianas sin medicinas: el gobierno italiano culpa a los ciudadanos de la crisis."),
            _a("@dos", "Visita al puerto de Marsella para hablar de comercio marítimo y logística en el Mediterráneo."),
        ]
        r = resumen_redes(alertas)
        self.assertIn("3 publicaciones", r["intro"])
        self.assertTrue(r["puntos"])
        for p in r["puntos"]:
            self.assertNotIn("http", p["texto"])
            self.assertNotIn("t.me", p["texto"])
            self.assertNotIn("#", p["texto"])

    def test_vacio(self):
        self.assertEqual(resumen_redes([])["puntos"], [])


if __name__ == "__main__":
    unittest.main()
