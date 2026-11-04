import unittest
from unittest import mock

from buscador_noticias import keepalive


class KeepaliveTests(unittest.TestCase):
    def test_precarga_no_compite_con_la_carga_inicial(self):
        with mock.patch.object(keepalive.time, "sleep", side_effect=RuntimeError("stop")):
            with mock.patch(
                "buscador_noticias.sources.cargar_todas_las_fuentes"
            ) as cargar:
                with self.assertRaisesRegex(RuntimeError, "stop"):
                    keepalive._bucle_precarga()

        cargar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
