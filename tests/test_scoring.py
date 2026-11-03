import unittest
from datetime import datetime, timedelta, timezone

from buscador_noticias.scoring import puntuar


def item(**kw):
    base = {
        "plataforma": "PRENSA", "canal": "Blog X", "num_fuentes": 1, "categoria": "GLOBAL",
        "titular": "Reunion sobre comercio", "cuerpo": "", "etiquetas_ner": [],
        "impacto_potencial": False, "fecha_estimada": False,
        "fecha_dt": datetime.now(timezone.utc) - timedelta(days=3),
    }
    base.update(kw)
    return base


class ScoringTest(unittest.TestCase):
    def test_rango(self):
        p = puntuar(item())
        self.assertTrue(0 <= p["fiabilidad"] <= 100 and 0 <= p["peligro"] <= 100)

    def test_corroboracion_y_medio_de_referencia_suben_fiabilidad(self):
        base = puntuar(item())["fiabilidad"]
        self.assertGreater(puntuar(item(num_fuentes=4))["fiabilidad"], base)
        self.assertGreater(puntuar(item(canal="Reuters World"))["fiabilidad"], base)

    def test_telegram_y_sensacionalismo_bajan_fiabilidad(self):
        base = puntuar(item())["fiabilidad"]
        self.assertLess(puntuar(item(plataforma="TELEGRAM"))["fiabilidad"], base)
        self.assertLess(puntuar(item(titular="URGENTE!! LO QUE PASA AHORA"))["fiabilidad"], base)

    def test_peligro_sube_con_sabotaje_y_terrorismo(self):
        base = puntuar(item())["peligro"]
        self.assertGreater(puntuar(item(titular="Sabotaje en la via del tren"))["peligro"], base)
        self.assertGreater(puntuar(item(titular="Atentado terrorista en la estacion"))["peligro"], base)

    def test_muchos_canales_sociales_suben_sobre_todo_el_peligro(self):
        solo = puntuar(item(plataforma="TELEGRAM", num_canales_sociales=1))
        muchos = puntuar(item(plataforma="TELEGRAM", num_canales_sociales=5))
        sube_p = muchos["peligro"] - solo["peligro"]
        sube_f = muchos["fiabilidad"] - solo["fiabilidad"]
        self.assertGreater(sube_p, sube_f)
        self.assertGreaterEqual(sube_p, 25)

    def test_incluye_motivos(self):
        self.assertTrue(puntuar(item(num_fuentes=3))["motivos_fiabilidad"])


if __name__ == "__main__":
    unittest.main()
