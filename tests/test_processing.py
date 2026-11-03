import unittest
from datetime import datetime, timedelta, timezone

from buscador_noticias.config import PATRON_IMPACTO_MULTILINGUE
from buscador_noticias.processing import (
    categorizar_noticia,
    clave_actualidad_cobertura,
    cumple_ventana_temporal,
    extraer_entidades_clave,
    es_tematico_redes,
    normalizar_texto,
)


class ProcessingTests(unittest.TestCase):
    def test_unknown_and_future_dates_are_not_recent(self):
        now = datetime.now(timezone.utc)

        self.assertFalse(cumple_ventana_temporal(None, 24))
        self.assertFalse(cumple_ventana_temporal(now + timedelta(hours=1), 24))
        self.assertTrue(cumple_ventana_temporal(now - timedelta(hours=2), 24))

    def test_priority_uses_recency_band_then_source_count(self):
        now = datetime.now(timezone.utc)
        recent = {"fecha_dt": now - timedelta(hours=1), "num_fuentes": 1}
        older = {"fecha_dt": now - timedelta(hours=7), "num_fuentes": 5}
        more_covered = {"fecha_dt": now - timedelta(hours=2), "num_fuentes": 3}

        self.assertGreater(
            clave_actualidad_cobertura(recent),
            clave_actualidad_cobertura(older),
        )
        self.assertGreater(
            clave_actualidad_cobertura(more_covered),
            clave_actualidad_cobertura(recent),
        )

    def test_multilingual_hybrid_topics_are_recognized(self):
        self.assertEqual(
            categorizar_noticia("Terrorist attack in Russia", "", "PRENSA", "test"),
            "GLOBAL",
        )
        labels = extraer_entidades_clave("China disinformation operation")
        self.assertIn("Desinformación / Injerencia", [label for label, _ in labels])

    def test_sharij_news_and_own_social_posts_have_no_dedicated_section(self):
        self.assertEqual(
            categorizar_noticia("News about Anatolii Sharij", "", "PRENSA", "News"),
            "GLOBAL",
        )
        self.assertEqual(
            categorizar_noticia("New post", "", "TELEGRAM", "@ASupersharij"),
            "REDES",
        )

    def test_crypto_heist_precedes_incidental_fbi_mention(self):
        self.assertEqual(
            categorizar_noticia(
                "FBI investigates crypto heist after Binance was hacked",
                "Stolen funds were frozen.",
                "PRENSA",
                "Newswire",
            ),
            "CRIPTO",
        )

    def test_agency_posts_pass_social_relevance_filter(self):
        self.assertTrue(es_tematico_redes("CNI publishes its annual report"))
        self.assertTrue(es_tematico_redes("CIA announces an investigation"))

    def test_argentina_security_news_is_not_assumed_to_be_spain(self):
        self.assertEqual(
            categorizar_noticia(
                "Argentina: investigan espionaje ruso tras alerta de seguridad nacional",
                "La agencia publicó un informe.",
                "PRENSA",
                "España: seguimiento",
            ),
            "GLOBAL",
        )

    def test_english_defense_company_headline_goes_to_empresa(self):
        self.assertEqual(
            categorizar_noticia(
                "Spanish defense company Indra faces Russian cyber threat",
                "Security officials confirmed the incident.",
                "PRENSA",
                "España: empresas",
            ),
            "EMPRESA",
        )

    def test_incidental_agency_mention_does_not_override_drone_story(self):
        self.assertEqual(
            categorizar_noticia(
                "Russian drone attack hits Baltic port",
                "The FBI was mentioned in an unrelated case.",
                "PRENSA",
                "Newswire",
            ),
            "DRONES",
        )

    def test_spain_channel_label_alone_does_not_assign_espana(self):
        self.assertEqual(
            categorizar_noticia(
                "Russian drone attack hits Baltic port",
                "No Spanish location is involved.",
                "PRENSA",
                "España: sabotajes",
            ),
            "DRONES",
        )

    def test_spanish_language_and_negated_spain_reference_are_not_geography(self):
        self.assertEqual(
            categorizar_noticia(
                "News about the Spanish language and Russian cyberattacks",
                "No location in Spain is mentioned.",
                "PRENSA",
                "España: seguimiento",
            ),
            "GLOBAL",
        )

    def test_us_department_of_homeland_security_is_not_spain(self):
        self.assertEqual(
            categorizar_noticia(
                "Un ciberataque contra el Departamento de Seguridad Nacional de EEUU filtra los datos de 40.000 trabajadores",
                "ANF Agencia de Noticias Fides Bolivia",
                "PRENSA",
                "España: ciberdefensa [ES]",
            ),
            "DESCARTE",
        )

    def test_company_mentioned_only_in_body_does_not_capture_story(self):
        self.assertEqual(
            categorizar_noticia(
                "Russian cyberattack targets a Baltic port",
                "Indra was cited in an unrelated report.",
                "PRENSA",
                "Newswire",
            ),
            "GLOBAL",
        )

    def test_china_hybrid_news_precedes_drone_and_global_categories(self):
        self.assertEqual(
            categorizar_noticia(
                "Chinese drone attack raises security concerns",
                "Officials investigate the incident.",
                "PRENSA",
                "Newswire",
            ),
            "CHINA",
        )

    def test_us_department_of_homeland_security_is_not_spain(self):
        self.assertEqual(
            categorizar_noticia(
                "Un ciberataque contra el Departamento de Seguridad Nacional de EEUU filtra los datos de 40.000 trabajadores",
                "ANF Agencia de Noticias Fides Bolivia",
                "PRENSA",
                "España: ciberdefensa [ES]",
            ),
            "DESCARTE",
        )

    def test_impact_indicator_is_a_textual_signal(self):
        text = normalizar_texto("Evacuación de infraestructura crítica")

        self.assertIsNotNone(PATRON_IMPACTO_MULTILINGUE.search(text))


if __name__ == "__main__":
    unittest.main()
