import unittest

from buscador_noticias.processing import (
    cumple_busqueda_booleana_avanzada as cumple,
    resaltar_coincidencias,
)


def noticia(titular, cuerpo=""):
    return {"titular": titular, "cuerpo": cuerpo}


class SearchPrecisionTests(unittest.TestCase):
    def test_short_term_does_not_match_inside_other_words(self):
        grupo = noticia("Un grupo de empresarios visita la feria")
        for modo in ("Exacto", "Equilibrado", "Amplio"):
            self.assertFalse(cumple(grupo, "gru", modo), modo)

    def test_surname_does_not_trigger_sanctions_synonyms(self):
        politica = noticia("Sánchez defiende el presupuesto")
        for modo in ("Exacto", "Equilibrado", "Amplio"):
            self.assertFalse(cumple(politica, "sanciones", modo), modo)

    def test_equilibrado_accepts_plurals_accents_and_synonyms(self):
        self.assertTrue(cumple(noticia("Ataques de DRONES sobre Kiev"), "ataque dron"))
        self.assertTrue(cumple(noticia("Russian sabotage on railways"), "sabotaje"))
        self.assertTrue(cumple(noticia("Sanción de la UE a Rusia"), "sancion"))

    def test_exacto_rejects_plural_and_synonyms(self):
        self.assertFalse(cumple(noticia("Ataques con drones"), "dron", "Exacto"))
        self.assertTrue(cumple(noticia("Un dron cae en Polonia"), "dron", "Exacto"))
        self.assertFalse(cumple(noticia("Russian sabotage"), "sabotaje", "Exacto"))

    def test_strict_modes_require_every_word_amplio_needs_most(self):
        item = noticia("Sabotaje en la red ferroviaria alemana")
        self.assertFalse(cumple(item, "sabotaje ferroviario cibernetico espionaje", "Equilibrado"))
        self.assertTrue(cumple(item, "sabotaje ferroviaria alemana espionaje", "Amplio"))
        self.assertFalse(cumple(item, "sabotaje cibernetico espionaje drones", "Amplio"))

    def test_stopwords_do_not_block_matches(self):
        self.assertFalse(cumple(noticia("Ciberataque contra hospitales"), "ataque de hospitales"))
        self.assertTrue(cumple(noticia("Sabotaje al gasoducto"), "sabotaje del gasoducto"))

    def test_boolean_operators_phrases_and_negation(self):
        item = noticia("Sabotaje ferroviario en Alemania")
        self.assertTrue(cumple(item, '"sabotaje ferroviario"'))
        self.assertFalse(cumple(item, '"ferroviario sabotaje"'))
        self.assertFalse(cumple(item, "sabotaje -alemania"))
        self.assertTrue(cumple(item, "espionaje OR sabotaje"))

    def test_non_latin_terms_still_match(self):
        self.assertTrue(cumple(noticia("Диверсии на железной дороге"), "диверсия"))
        self.assertTrue(cumple(noticia("تخريب السكك الحديدية"), "تخريب"))

    def test_highlight_matches_accents_and_only_whole_words(self):
        html = resaltar_coincidencias("Sabotaje en un grupo", "sabotaje gru")
        self.assertIn('<mark class="osint-hit">Sabotaje</mark>', html)
        self.assertNotIn(">gru<", html)
        self.assertIn("&lt;b&gt;", resaltar_coincidencias("<b> dron", "dron"))


if __name__ == "__main__":
    unittest.main()
