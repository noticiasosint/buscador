import unittest

from buscador_noticias.pagina_cifrada import (
    _b64,
    _id_usuario,
    clave_de_usuario,
    cifrar_pagina,
    leer_usuarios,
)


class PaginaCifradaTests(unittest.TestCase):
    def test_leer_usuarios(self):
        u = leer_usuarios("Ana:uno:dos\n\n# nota\nluis:x\nsinclave\n:vacio\n")
        self.assertEqual(u, {"ana": "uno:dos", "luis": "x"})

    def test_sin_usuarios_falla(self):
        with self.assertRaises(ValueError):
            cifrar_pagina("<html></html>", {})

    def test_no_filtra_texto_ni_claves(self):
        salida = cifrar_pagina("<html>SECRETO-NOTICIA</html>", {"ana": "clave-privada"})
        self.assertNotIn("SECRETO-NOTICIA", salida)
        self.assertNotIn("clave-privada", salida)
        self.assertIn(_id_usuario("ana"), salida)
        self.assertNotIn('"ana"', salida)

    def test_clave_depende_de_usuario_y_clave(self):
        self.assertNotEqual(clave_de_usuario("ana", "x"), clave_de_usuario("ana", "y"))
        self.assertNotEqual(clave_de_usuario("ana", "x"), clave_de_usuario("luis", "x"))
        self.assertEqual(clave_de_usuario("Ana ", "x"), clave_de_usuario("ana", "x"))


if __name__ == "__main__":
    unittest.main()
