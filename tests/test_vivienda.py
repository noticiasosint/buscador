import unittest

from buscador_noticias.processing import categorizar_noticia


class DesinformacionSinEjeTests(unittest.TestCase):
    def test_vivienda_se_descarta(self):
        cat = categorizar_noticia(
            "Desinformación sobre las manifestaciones por la vivienda en España",
            "Bulos sobre las protestas por el alquiler.", "PRENSA", "Prensa Nacional",
        )
        self.assertEqual(cat, "DESCARTE")

    def test_sabotaje_en_espana_se_mantiene(self):
        cat = categorizar_noticia(
            "Detectan un sabotaje en una línea ferroviaria en España",
            "", "PRENSA", "Prensa Nacional",
        )
        self.assertNotEqual(cat, "DESCARTE")


if __name__ == "__main__":
    unittest.main()
