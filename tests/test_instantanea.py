import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from buscador_noticias import instantanea


class InstantaneaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["GAD_INSTANTANEA"] = str(Path(self.tmp.name) / "snap.json")

    def tearDown(self):
        os.environ.pop("GAD_INSTANTANEA", None)
        self.tmp.cleanup()

    def test_ida_y_vuelta_conserva_fechas(self):
        fecha = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
        alertas = [{"id": "a", "fecha_dt": fecha, "fuentes_coincidentes": [{"canal": "x", "fecha": fecha}]}]
        instantanea.guardar(alertas, [{"fuente": "rss"}], "03/11 10:00")
        r = instantanea.cargar()
        self.assertEqual(r[0][0]["fecha_dt"], fecha)
        self.assertEqual(r[0][0]["fuentes_coincidentes"][0]["fecha"], fecha)
        self.assertEqual(r[2], "03/11 10:00")

    def test_sin_copia_o_vacia(self):
        self.assertIsNone(instantanea.cargar())
        instantanea.guardar([], [], "x")
        self.assertIsNone(instantanea.cargar())

    def test_archivo_corrupto(self):
        Path(os.environ["GAD_INSTANTANEA"]).write_text("{no json", encoding="utf-8")
        self.assertIsNone(instantanea.cargar())


if __name__ == "__main__":
    unittest.main()
