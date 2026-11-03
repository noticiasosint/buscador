import os
import tempfile
import unittest
from pathlib import Path

from buscador_noticias import almacen, dictionary, usuarios


class UsuariosTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.antes = {k: os.environ.get(k) for k in ("GAD_ESTADO", "GAD_USUARIOS", "GAD_PASSWORD")}
        os.environ["GAD_ESTADO"] = str(Path(self.tmp.name) / "estado.json")
        os.environ["GAD_USUARIOS"] = str(Path(self.tmp.name) / "usuarios.json")
        os.environ["GAD_PASSWORD"] = "claveadmin"

    def tearDown(self):
        for k, v in self.antes.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def test_admin_con_clave_del_sistema(self):
        self.assertEqual(usuarios.autenticar("admin", "claveadmin")["rol"], "admin")
        self.assertIsNone(usuarios.autenticar("admin", "otra"))
        self.assertIsNone(usuarios.autenticar("nadie", "claveadmin"))

    def test_crear_autenticar_y_borrar(self):
        usuarios.crear("Ana", "secreto1")
        self.assertEqual(usuarios.autenticar("ana", "secreto1"), {"usuario": "ana", "rol": "usuario"})
        self.assertIsNone(usuarios.autenticar("ana", "secreto2"))
        with self.assertRaises(ValueError):
            usuarios.crear("ana", "secreto1")
        with self.assertRaises(ValueError):
            usuarios.crear("../x", "secreto1")
        with self.assertRaises(ValueError):
            usuarios.crear("bob", "corta")
        usuarios.borrar("ana")
        self.assertIsNone(usuarios.autenticar("ana", "secreto1"))
        with self.assertRaises(ValueError):
            usuarios.borrar("admin")

    def test_la_clave_no_se_guarda_en_claro(self):
        usuarios.crear("ana", "secreto1")
        self.assertNotIn("secreto1", usuarios.ruta_usuarios().read_text(encoding="utf-8"))

    def test_cambiar_clave_del_admin(self):
        usuarios.cambiar_clave("admin", "nuevaclave")
        self.assertIsNone(usuarios.autenticar("admin", "claveadmin"))
        self.assertEqual(usuarios.autenticar("admin", "nuevaclave")["rol"], "admin")

    def test_datos_separados_por_usuario(self):
        usuarios.crear("ana", "secreto1")
        almacen.valorar("a1", "falsa", "ana")
        almacen.valorar("a2", "confirmada")
        self.assertEqual(almacen.cargar("ana")["valoraciones"], {"a1": "falsa"})
        self.assertEqual(almacen.cargar()["valoraciones"], {"a2": "confirmada"})
        dictionary.agregar_termino_personalizado("dron", "DRONES", [], "ana")
        self.assertEqual(len(dictionary.cargar_diccionario_personalizado("ana")), 1)
        self.assertEqual(dictionary.cargar_diccionario_personalizado(), [])

    def test_usuario_invalido_no_sale_de_la_carpeta(self):
        with self.assertRaises(ValueError):
            almacen.ruta_estado("../admin")

    def test_preferencias_y_temas(self):
        usuarios.crear("ana", "secreto1")
        validos = {"ESPANA", "DRONES"}
        self.assertIsNone(usuarios.preferencias("ana", validos)["secciones"])
        usuarios.guardar_preferencias("ana", secciones=["DRONES", "XXX"], codigos_validos=validos)
        self.assertEqual(usuarios.preferencias("ana", validos)["secciones"], ["DRONES"])
        with self.assertRaises(ValueError):
            usuarios.guardar_preferencias("ana", secciones=["XXX"], codigos_validos=validos)
        usuarios.guardar_temas("ana", [{"nombre": "Tren", "palabras": ["tren", " vía ", "tren"]}, {"nombre": "", "palabras": ["x"]}])
        temas = usuarios.preferencias("ana")["temas"]
        self.assertEqual(temas, [{"nombre": "Tren", "palabras": ["tren", "vía"]}])
        self.assertEqual(usuarios.preferencias("ana", validos)["secciones"], ["DRONES"])

    def test_preferencia_sharij_antigua_migra_a_global(self):
        usuarios.crear("ana", "secreto1")
        usuarios.guardar_preferencias("ana", secciones=["SHARIJ"])
        self.assertEqual(
            usuarios.preferencias("ana", {"GLOBAL", "REDES"})["secciones"],
            ["GLOBAL"],
        )

    def test_cumple_tema(self):
        alerta = {"titular": "Sabotaje en el ferrocarril", "cuerpo": "", "titular_raw_limpio": ""}
        self.assertTrue(usuarios.cumple_tema(alerta, ["ferrocarril"]))
        self.assertFalse(usuarios.cumple_tema(alerta, ["ferro"]))


    def test_grupos_comparten_diccionario_y_temas(self):
        usuarios.crear("ana", "secreto1")
        usuarios.crear("luis", "secreto2")
        usuarios.crear("eva", "secreto3")
        usuarios.crear_grupo("equipo1")
        usuarios.asignar_grupo("ana", "equipo1")
        usuarios.asignar_grupo("luis", "equipo1")
        self.assertEqual(usuarios.listar_grupos()[0]["miembros"], ["ana", "luis"])
        dictionary.agregar_termino_personalizado("sabotaje ferroviario", "DRONES", [], "grupo:equipo1")
        dictionary.agregar_termino_personalizado("solo ana", "DRONES", [], "ana")
        terminos = lambda u: {e["termino"] for e in dictionary.cargar_diccionario_efectivo(u)}
        self.assertEqual(terminos("ana"), {"sabotaje ferroviario", "solo ana"})
        self.assertEqual(terminos("luis"), {"sabotaje ferroviario"})
        self.assertEqual(terminos("eva"), set())
        usuarios.guardar_temas_grupo("ana", [{"nombre": "Tren", "palabras": ["tren"]}])
        self.assertEqual(usuarios.preferencias("luis")["temas_grupo"][0]["nombre"], "Tren")
        self.assertEqual(usuarios.preferencias("eva")["temas_grupo"], [])
        with self.assertRaises(ValueError):
            usuarios.guardar_temas_grupo("eva", [])
        usuarios.cambiar_clave("ana", "nuevaclave")
        self.assertEqual(usuarios.grupo_de("ana"), "equipo1")
        usuarios.borrar_grupo("equipo1")
        self.assertEqual(usuarios.grupo_de("ana"), "")
        self.assertEqual(terminos("ana"), {"solo ana"})

    def test_correo_de_usuario(self):
        usuarios.crear("ana", "secreto1")
        usuarios.guardar_correo("ana", " ana@ejemplo.es ")
        self.assertEqual(usuarios.correo_de("ana"), "ana@ejemplo.es")
        with self.assertRaises(ValueError):
            usuarios.guardar_correo("ana", "no-es-correo")
        usuarios.guardar_correo("admin", "jefe@ejemplo.es")
        self.assertEqual(usuarios.autenticar("admin", "claveadmin")["rol"], "admin")
        self.assertEqual(usuarios.listar()[0]["correo"], "jefe@ejemplo.es")
        usuarios.guardar_correo("ana", "")
        self.assertEqual(usuarios.correo_de("ana"), "")


if __name__ == "__main__":
    unittest.main()
