import unittest
from datetime import datetime, timezone
from unittest import mock

from buscador_noticias.perfiles import es_canal_tg_redes, perfil_de_canal, perfiles_en
from buscador_noticias import sources


class PerfilesTests(unittest.TestCase):
    def test_canal_propio(self):
        self.assertEqual(perfil_de_canal("@rusa_alena"), "PELICANO")
        self.assertEqual(perfiles_en("hola mundo", "@desdemoscubot"), ["ARIAS"])

    def test_canales_telegram_de_redes(self):
        self.assertTrue(es_canal_tg_redes("@GUERRASYGEO"))
        self.assertTrue(es_canal_tg_redes("@GuerrasyGeop"))
        self.assertTrue(es_canal_tg_redes("@noname05716_esp"))
        self.assertFalse(es_canal_tg_redes("@desdemoscubot"))

    def test_fuente_tg_redes_acepta_publicacion_no_tematicas(self):
        response = mock.Mock(
            status_code=200,
            text=(
                '<div class="tgme_widget_message_wrap">'
                '<div class="tgme_widget_message_text">Publicación de prueba sin palabras clave.</div>'
                '<time class="message_video_duration">2:01</time>'
                '<time class="time" datetime="2026-11-11T08:35:37+00:00">08:35</time>'
                '<a class="tgme_widget_message_date" href="https://t.me/liusivaya/1"></a>'
                "</div>"
            ),
        )
        with (
            mock.patch.object(sources.SESION_HTTP, "get", return_value=response),
            mock.patch.object(sources, "es_tematico_redes", return_value=False),
        ):
            publicaciones, error = sources._raspar_un_canal_tg_web("liusivaya")

        self.assertIsNone(error)
        self.assertEqual(len(publicaciones), 1)
        self.assertEqual(publicaciones[0]["canal"], "@liusivaya")
        self.assertEqual(
            publicaciones[0]["fecha_dt"],
            datetime(2026, 11, 11, 8, 35, 37, tzinfo=timezone.utc),
        )

    def test_menciones_por_nombre(self):
        self.assertIn("DORAO", perfiles_en("Eugenio Dorao presenta la plataforma"))
        self.assertIn("AGUILAR", perfiles_en("El Instituto Español de Geopolítica opina"))

    def test_medvedev_requiere_contexto_y_excluye_tenis(self):
        self.assertIn("MEDVEDEV", perfiles_en("Medvedev amenaza con armas nucleares a Europa"))
        self.assertEqual(perfiles_en("Daniil Medvedev gana el partido en Wimbledon"), [])


if __name__ == "__main__":
    unittest.main()
