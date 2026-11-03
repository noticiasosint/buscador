import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from buscador_noticias import almacen
from buscador_noticias.analisis import (
    agrupar_hilos,
    contar_nuevas_busqueda,
    detectar_picos,
    ids_nuevos,
    linea_tiempo,
    puntuar_con_aprendizaje,
    reputacion_canales,
)
from buscador_noticias import informe_diario


def alerta(i, titular, horas=1, canal="Canal", plataforma="PRENSA", ner=(), categoria="GLOBAL"):
    return {
        "id": f"id{i}", "plataforma": plataforma, "canal": canal, "num_fuentes": 1,
        "categoria": categoria, "titular": titular, "titular_raw_limpio": titular, "cuerpo": "",
        "etiquetas_ner": [(n, "#000") for n in ner], "impacto_potencial": False,
        "fecha_dt": datetime.now(timezone.utc) - timedelta(hours=horas), "fecha_estimada": False,
        "enlace": f"https://x.es/{i}",
    }


class AlmacenTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.p = mock.patch.dict(os.environ, {"GAD_ESTADO": os.path.join(self.dir.name, "e.json")})
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.dir.cleanup()

    def test_valoraciones(self):
        almacen.valorar("a", "falsa")
        self.assertEqual(almacen.cargar()["valoraciones"], {"a": "falsa"})
        almacen.valorar("a", None)
        self.assertEqual(almacen.cargar()["valoraciones"], {})
        with self.assertRaises(ValueError):
            almacen.valorar("a", "otra")

    def test_busquedas(self):
        almacen.guardar_busqueda("Polonia", "sabotaje polonia", "Equilibrado", ["1"])
        almacen.guardar_busqueda("Polonia", "sabotaje polonia 2", "Equilibrado")
        b = almacen.cargar()["busquedas"]
        self.assertEqual(len(b), 1)
        self.assertEqual(b[0]["consulta"], "sabotaje polonia 2")
        almacen.borrar_busqueda("Polonia")
        self.assertEqual(almacen.cargar()["busquedas"], [])
        with self.assertRaises(ValueError):
            almacen.guardar_busqueda("x", "  ", "m")

    def test_vistos_y_primera_visita(self):
        previos, visitado = almacen.registrar_vistos(["a", "b"])
        self.assertFalse(visitado)
        previos, visitado = almacen.registrar_vistos(["a", "c"])
        self.assertTrue(visitado)
        self.assertEqual(previos, {"a", "b"})

    def test_archivo_corrupto(self):
        from pathlib import Path
        Path(almacen.ruta_estado()).write_text("{no json", encoding="utf-8")
        self.assertEqual(almacen.cargar()["valoraciones"], {})


class AnalisisTest(unittest.TestCase):
    def test_pico(self):
        datos = [alerta(i, f"Sabotaje ferroviario caso {i}", 2, ner=["GRU"]) for i in range(5)]
        datos += [alerta(10, "Otro sabotaje antiguo", 72, ner=["GRU"])]
        picos = detectar_picos(datos)
        self.assertTrue(any(p["termino"] == "GRU" and p["hoy"] == 5 for p in picos))

    def test_pico_indica_su_area(self):
        datos = [alerta(i, f"Sabotaje ferroviario caso {i}", 2, ner=["GRU"]) for i in range(5)]
        pico = next(p for p in detectar_picos(datos) if p["termino"] == "GRU")
        self.assertTrue(pico["areas"])
        self.assertEqual(sum(z["n"] for z in pico["areas"]) >= 5, True)

    def test_sin_pico_si_es_habitual(self):
        datos = [alerta(i, "Tema habitual", 2, ner=["X"]) for i in range(3)]
        datos += [alerta(10 + i, "Tema habitual", 30 + i * 6, ner=["X"]) for i in range(18)]
        self.assertFalse([p for p in detectar_picos(datos) if p["termino"] == "X"])

    def test_nuevos(self):
        datos = [alerta(1, "a"), alerta(2, "b")]
        self.assertEqual(ids_nuevos(datos, {"id1"}, False), set())
        self.assertEqual(ids_nuevos(datos, {"id1"}, True), {"id2"})

    def test_linea_tiempo(self):
        datos = [alerta(1, "a", 0.2), alerta(2, "b", 0.3), alerta(3, "c", 5)]
        lt = linea_tiempo(datos, 48)
        self.assertEqual(len(lt), 48)
        self.assertEqual(sum(x["total"] for x in lt), 3)
        self.assertEqual(len(linea_tiempo(datos, 168)), 7)

    def test_hilos(self):
        datos = [
            alerta(1, "Detenidos en Alemania dos hombres acusados de sabotaje para Rusia", 3, "Prensa A"),
            alerta(2, "Alemania detiene dos hombres acusados de sabotaje para Rusia", 1, "Canal TG", "TELEGRAM"),
            alerta(3, "Partido de futbol aplazado por lluvia intensa", 2, "Deportes"),
        ]
        h = agrupar_hilos(datos)
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]["primero"]["canal"], "Prensa A")
        self.assertEqual(h[0]["sociales"], 1)

    def test_aprendizaje(self):
        datos = [alerta(i, f"t{i}", canal="Dudoso") for i in range(2)]
        val = {"id0": "falsa", "id1": "falsa"}
        rep = reputacion_canales(datos, val)
        self.assertEqual(rep["Dudoso"], -10)
        nuevo = alerta(9, "otro", canal="Dudoso")
        base = puntuar_con_aprendizaje(nuevo, {}, {})["fiabilidad"]
        self.assertEqual(puntuar_con_aprendizaje(nuevo, {}, rep)["fiabilidad"], base - 10)
        self.assertEqual(puntuar_con_aprendizaje(datos[0], val, rep)["fiabilidad"], 5)
        self.assertEqual(puntuar_con_aprendizaje(datos[0], {"id0": "confirmada"}, {})["fiabilidad"] >= 90, True)

    def test_busqueda_guardada(self):
        datos = [alerta(1, "sabotaje"), alerta(2, "sabotaje otra vez")]
        b = {"consulta": "sabotaje", "modo": "m", "vistos": ["id1"]}
        nuevas, todas = contar_nuevas_busqueda(datos, b, lambda a, q, m: q in a["titular"])
        self.assertEqual([a["id"] for a in nuevas], ["id2"])
        self.assertEqual(len(todas), 2)


class InformeTest(unittest.TestCase):
    def test_correo_sin_configurar(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                informe_diario.configuracion_correo()

    def test_envio_starttls(self):
        cfg = {"host": "h", "puerto": 587, "usuario": "u", "clave": "c", "remitente": "a@b.es", "destinos": ["c@d.es"]}
        with mock.patch("smtplib.SMTP") as smtp:
            informe_diario.enviar_correo("asunto", "texto", "<html></html>", cfg)
        srv = smtp.return_value.__enter__.return_value
        srv.starttls.assert_called_once()
        srv.login.assert_called_once_with("u", "c")
        srv.send_message.assert_called_once()

    def test_construir_informe(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"GAD_ESTADO": os.path.join(d, "e.json")}):
            asunto, texto, html = informe_diario.construir_informe([alerta(1, "Sabotaje ferroviario en Polonia")])
        self.assertIn("Informe diario", asunto)
        self.assertIn(b"<html", html.lower())


if __name__ == "__main__":
    unittest.main()
