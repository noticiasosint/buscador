import unittest

from buscador_noticias.processing import categorizar_noticia


class DesinformacionSinEjeTests(unittest.TestCase):
    def test_vivienda_se_descarta(self):
        cat = categorizar_noticia(
            "Desinformación sobre las manifestaciones por la vivienda en España",
            "Bulos sobre las protestas por el alquiler.", "PRENSA", "Prensa Nacional",
        )
        self.assertEqual(cat, "DESCARTE")

    def test_politica_interna_espanola_se_descarta(self):
        cat = categorizar_noticia(
            "La juez denuncia ante la Audiencia Nacional un espionaje y presiones",
            "", "PRENSA", "Prensa Nacional",
        )
        self.assertEqual(cat, "DESCARTE")

    def test_sabotaje_en_espana_con_rusia_se_mantiene(self):
        cat = categorizar_noticia(
            "Detectan un sabotaje ruso en una línea ferroviaria en España",
            "", "PRENSA", "Prensa Nacional",
        )
        self.assertNotEqual(cat, "DESCARTE")


if __name__ == "__main__":
    unittest.main()
