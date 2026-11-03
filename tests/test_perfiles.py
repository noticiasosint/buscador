import unittest

from buscador_noticias.perfiles import perfil_de_canal, perfiles_en


class PerfilesTests(unittest.TestCase):
    def test_canal_propio(self):
        self.assertEqual(perfil_de_canal("@rusa_alena"), "PELICANO")
        self.assertEqual(perfiles_en("hola mundo", "@desdemoscubot"), ["ARIAS"])

    def test_menciones_por_nombre(self):
        self.assertIn("DORAO", perfiles_en("Eugenio Dorao presenta la plataforma"))
        self.assertIn("AGUILAR", perfiles_en("El Instituto Español de Geopolítica opina"))

    def test_medvedev_requiere_contexto_y_excluye_tenis(self):
        self.assertIn("MEDVEDEV", perfiles_en("Medvedev amenaza con armas nucleares a Europa"))
        self.assertEqual(perfiles_en("Daniil Medvedev gana el partido en Wimbledon"), [])


if __name__ == "__main__":
    unittest.main()
