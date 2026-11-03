import unittest
from datetime import datetime, timezone

from buscador_noticias.resumen import resumir, resumen_a_texto


def alerta(i, titular, categoria="GLOBAL", fuentes=1, ner=(), impacto=False):
    return {
        "id": f"id{i}", "plataforma": "PRENSA", "canal": "Canal", "num_fuentes": fuentes,
        "categoria": categoria, "titular": titular, "titular_raw_limpio": titular, "cuerpo": "",
        "etiquetas_ner": [(n, "#000") for n in ner], "impacto_potencial": impacto,
        "fecha_dt": datetime.now(timezone.utc), "fecha_estimada": False, "enlace": "https://x.es",
    }


class ResumenTest(unittest.TestCase):
    def test_vacio(self):
        r = resumir([])
        self.assertEqual(r["total"], 0)
        self.assertIn("No hay alertas", r["titulo"])

    def test_cifras_y_ranking(self):
        datos = [
            alerta(1, "Sabotaje ferroviario en Polonia", "DETENCION", 3, ["GRU"], True),
            alerta(2, "Sabotaje ferroviario investigado", "DETENCION", 1, ["GRU"]),
            alerta(3, "Reunion comercial sin incidentes", "GLOBAL"),
        ]
        r = resumir(datos, {"DETENCION": "Detenciones"}, "Últimas 24 Horas")
        self.assertEqual(r["total"], 3)
        self.assertEqual(r["corroboradas"], 1)
        self.assertEqual(r["categorias"][0]["nombre"], "Detenciones")
        self.assertEqual(r["actores"][0][:2], ["GRU", 2])
        self.assertEqual(r["actores"][0][2][0]["enlace"], "https://x.es")
        self.assertEqual(r["destacadas"][0]["id"], "id1")
        self.assertEqual(r["destacadas"][0]["enlace"], "https://x.es")
        self.assertIn("sabotaje", [t[0] for t in r["temas"]])
        self.assertTrue(r["categorias"][0]["ejemplos"])

    def test_enlace_inseguro_se_descarta(self):
        a = alerta(1, "Sabotaje ferroviario", "DETENCION", ner=["GRU"])
        a["enlace"] = "javascript:alert(1)"
        r = resumir([a, alerta(2, "Sabotaje ferroviario grave")])
        self.assertEqual(r["destacadas"][0]["enlace"] if r["destacadas"][0]["id"] == "id1" else "", "")
        self.assertEqual(r["actores"][0][2], [])

    def test_texto(self):
        t = resumen_a_texto(resumir([alerta(1, "Sabotaje ferroviario", "DETENCION"), alerta(2, "Sabotaje ferroviario grave")]))
        self.assertIn("Por área", t)


if __name__ == "__main__":
    unittest.main()
