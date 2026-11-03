import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from buscador_noticias.config import SECCIONES_INFORME
from buscador_noticias.dictionary import (
    agregar_termino_personalizado,
    cargar_diccionario_personalizado,
    coincidencia_personalizada,
)


class CustomDictionaryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dictionary_path = Path(self.temp_dir.name) / "dictionary.json"
        self.path_patcher = patch(
            "buscador_noticias.dictionary.ruta_diccionario_personalizado",
            return_value=self.dictionary_path,
        )
        self.path_patcher.start()
        self.addCleanup(self.path_patcher.stop)
        self.addCleanup(self.temp_dir.cleanup)

    def test_add_and_reload_persists_term_and_category(self):
        category = SECCIONES_INFORME[0][0]
        translations = [{"idioma": "Inglés", "codigo": "en", "texto": "undersea cable"}]

        entries = agregar_termino_personalizado("cable submarino", category, translations)

        self.assertEqual(entries, cargar_diccionario_personalizado())
        self.assertEqual(
            entries[0],
            {
                "termino": "cable submarino",
                "categoria": category,
                "traducciones": translations,
            },
        )

    def test_duplicate_terms_are_rejected_case_insensitively(self):
        category = SECCIONES_INFORME[0][0]
        agregar_termino_personalizado("Sabotaje", category)

        with self.assertRaisesRegex(ValueError, "ya está"):
            agregar_termino_personalizado("sabotaje", category)

    def test_longest_matching_phrase_selects_its_category(self):
        entries = [
            {"termino": "ataque", "categoria": SECCIONES_INFORME[0][0]},
            {"termino": "ataque a infraestructura crítica", "categoria": SECCIONES_INFORME[1][0]},
        ]

        result = coincidencia_personalizada(
            "Ataque a infraestructura critica",
            "",
            entries,
        )

        self.assertEqual(result["termino"], entries[1]["termino"])
        self.assertEqual(result["categoria"], entries[1]["categoria"])

    def test_translated_variants_are_used_for_matching(self):
        entry = {
            "termino": "sabotaje",
            "categoria": SECCIONES_INFORME[0][0],
            "traducciones": [
                {"idioma": "Inglés", "codigo": "en", "texto": "sabotage"},
            ],
        }

        result = coincidencia_personalizada("railway sabotage", "", [entry])

        self.assertEqual(result["coincidencia"], "sabotage")
        self.assertEqual(result["idioma"], "Inglés")

    def test_terms_are_matched_as_whole_words(self):
        entries = [{"termino": "red", "categoria": SECCIONES_INFORME[0][0]}]

        self.assertIsNone(coincidencia_personalizada("redes sociales", "", entries))
        result = coincidencia_personalizada("corte de red", "", entries)
        self.assertEqual(result["termino"], "red")
        self.assertEqual(result["coincidencia"], "red")


if __name__ == "__main__":
    unittest.main()
