import json
import re
import unittest
from datetime import datetime, timezone

from buscador_noticias.pagina_movil import construir_pagina


def _alerta(i, titular, enlace="https://example.com/x", plataforma="PRENSA", categoria="CHINA"):
    return {
        "id": str(i), "titular": titular, "canal": "Medio", "enlace": enlace,
        "plataforma": plataforma, "categoria": categoria,
        "fecha_dt": datetime(2026, 11, 3, 10, i, tzinfo=timezone.utc),
    }


class PaginaMovilTest(unittest.TestCase):
    def _datos(self, pagina):
        return json.loads(re.search(r"const D=(\[.*?\]);const SEC", pagina, re.S).group(1))

    def test_ordena_por_fecha_y_filtra_enlaces_inseguros(self):
        pagina = construir_pagina([
            _alerta(1, "vieja"),
            _alerta(2, "nueva"),
            _alerta(3, "mala", enlace="javascript:alert(1)"),
        ])
        datos = self._datos(pagina)
        self.assertEqual([d["t"] for d in datos], ["mala", "nueva", "vieja"])
        self.assertEqual(datos[0]["u"], "")

    def test_titular_no_cierra_el_script(self):
        pagina = construir_pagina([_alerta(1, "</script><img src=x onerror=alert(1)>")])
        self.assertEqual(pagina.count("</script>"), 1)
        self.assertEqual(self._datos(pagina)[0]["t"], "</script><img src=x onerror=alert(1)>")

    def test_sin_fecha_se_omite(self):
        a = _alerta(1, "sin fecha")
        a["fecha_dt"] = None
        self.assertEqual(self._datos(construir_pagina([a])), [])


if __name__ == "__main__":
    unittest.main()
