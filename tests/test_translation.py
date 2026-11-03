import unittest
from unittest.mock import patch

from buscador_noticias.translator import (
    detectar_idioma,
    traducir_a_espanol,
    traducir_termino,
)


class _FakeMyMemory:
    def __init__(self, source, target, email=None):
        self.source = source
        self.target = target

    def translate(self, texto):
        return f"{texto}/{self.source}-{self.target}"


class NewsTranslationTests(unittest.TestCase):
    def setUp(self):
        traducir_a_espanol.cache_clear()
        patcher = patch(
            "buscador_noticias.translator._traducir_google",
            side_effect=RuntimeError("sin Google"),
        )
        self.google = patcher.start()
        self.addCleanup(patcher.stop)

    def test_google_is_the_primary_engine(self):
        self.google.side_effect = None
        self.google.return_value = ("Rumania acusa a Rusia", "en")
        self.assertEqual(traducir_a_espanol("Romania accuses Russia"), ("Rumania acusa a Rusia", "en"))

    def test_spanish_detected_by_google_is_returned_unchanged(self):
        self.google.side_effect = None
        self.google.return_value = ("x", "es")
        self.assertEqual(traducir_a_espanol("Hola mundo"), ("Hola mundo", None))

    def test_detects_language_by_script_and_skips_spanish(self):
        self.assertEqual(detectar_idioma("ФСБ задержала пользователей"), "ru")
        self.assertEqual(detectar_idioma("ФСБ затримала користувачів із Києва і їх"), "uk")
        self.assertEqual(detectar_idioma("تخريب السكك الحديدية"), "ar")
        self.assertEqual(detectar_idioma("破坏关键基础设施"), "zh-CN")
        self.assertEqual(detectar_idioma("Romania accuses Russia of sabotage"), "en")
        self.assertIsNone(detectar_idioma("Hola mundo"))
        self.assertIsNone(detectar_idioma("España permanece sin respuestas ante el riesgo"))

    @patch("deep_translator.MyMemoryTranslator", _FakeMyMemory)
    def test_translates_news_to_spanish_and_caches(self):
        texto, origen = traducir_a_espanol("Russia sabotage network")
        self.assertEqual(origen, "en")
        self.assertEqual(texto, "Russia sabotage network/en-GB-es-ES")

    @patch("deep_translator.MyMemoryTranslator", _FakeMyMemory)
    def test_google_misdetecting_an_english_headline_as_spanish_uses_fallback(self):
        self.google.side_effect = None
        texto = "Russian cyberattack targets a Baltic port"
        self.google.return_value = (texto, "es")
        traducido, origen = traducir_a_espanol(texto)
        self.assertEqual(origen, "en")
        self.assertEqual(texto, "Russian cyberattack targets a Baltic port")
        self.assertEqual(traducido, "Russian cyberattack targets a Baltic port/en-GB-es-ES")

    @patch("deep_translator.MyMemoryTranslator", _FakeMyMemory)
    def test_spanish_news_is_not_sent_to_the_service(self):
        texto, origen = traducir_a_espanol("España detiene a un espía ante la UE")
        self.assertIsNone(origen)
        self.assertEqual(texto, "España detiene a un espía ante la UE")

    @patch("deep_translator.MyMemoryTranslator")
    def test_quota_warning_becomes_error(self, translator):
        translator.return_value.translate.return_value = "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS"
        with self.assertRaisesRegex(RuntimeError, "límite diario"):
            traducir_a_espanol("Russia sabotage network")


class TranslationTests(unittest.TestCase):
    @patch("deep_translator.MyMemoryTranslator", _FakeMyMemory)
    def test_translates_to_each_selected_language(self):
        result = traducir_termino("sabotaje", ["Ruso", "Chino simplificado"])

        self.assertEqual(
            result,
            [
                {"idioma": "Ruso", "codigo": "ru", "texto": "sabotaje/es-ES-ru-RU"},
                {"idioma": "Chino simplificado", "codigo": "zh-CN", "texto": "sabotaje/es-ES-zh-CN"},
            ],
        )

    @patch("deep_translator.MyMemoryTranslator")
    def test_wraps_service_errors(self, translator):
        translator.return_value.translate.side_effect = Exception("sin red")

        with self.assertRaisesRegex(RuntimeError, "No se pudo traducir a Ruso"):
            traducir_termino("sabotaje", ["Ruso"])

    def test_requires_term_and_target_language(self):
        with self.assertRaisesRegex(ValueError, "palabra o expresión"):
            traducir_termino("", ["Inglés"])

        with self.assertRaisesRegex(ValueError, "al menos un idioma"):
            traducir_termino("sabotaje", [])

    def test_rejects_source_language_as_target(self):
        with self.assertRaisesRegex(ValueError, "idioma de origen"):
            traducir_termino("sabotaje", ["Inglés"], "en")


if __name__ == "__main__":
    unittest.main()
