import os
import unittest
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import Finca, Usuario


TEST_DB_PATH = Path(__file__).resolve().parent.parent / "instance" / "test_isolated_fase3.db"


class TestFase3AdminLogin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Asegurar que no exista una base de pruebas previa
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()

        cls.app = create_app()
        cls.app.config.update({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{TEST_DB_PATH.as_posix()}",
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "clave-de-prueba-fase3"
        })

        with cls.app.app_context():
            db.create_all()

            # 1. Crear dos fincas distintas
            finca1 = Finca(
                codigo="FINCA_CAFE",
                nombre="Finca La Esperanza",
                ubicacion="Manizales"
            )
            finca2 = Finca(
                codigo="FINCA_PLATANO",
                nombre="Finca El Paraiso",
                ubicacion="Armenia"
            )
            db.session.add_all([finca1, finca2])
            db.session.commit()

            # 2. Crear administrador general sin finca (finca_id=None, is_admin=True)
            admin = Usuario(
                nombre="AdminGeneral",
                email="admin@test.com",
                is_admin=True,
                finca_id=None
            )
            admin.set_password("AdminSecret123")

            # 3. Crear usuario normal asociado a Finca 1
            user_finca1 = Usuario(
                nombre="OperadorCafe",
                email="operador1@test.com",
                is_admin=False,
                finca_id=finca1.id
            )
            user_finca1.set_password("OperadorPass1")

            # 4. Crear usuario normal asociado a Finca 2
            user_finca2 = Usuario(
                nombre="OperadorPlatano",
                email="operador2@test.com",
                is_admin=False,
                finca_id=finca2.id
            )
            user_finca2.set_password("OperadorPass2")

            # 5. Crear usuario normal huérfano (sin finca)
            user_huerfano = Usuario(
                nombre="UsuarioSinFinca",
                email="sinfinca@test.com",
                is_admin=False,
                finca_id=None
            )
            user_huerfano.set_password("SinFincaPass")

            db.session.add_all([admin, user_finca1, user_finca2, user_huerfano])
            db.session.commit()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()

    def setUp(self):
        self.client = self.app.test_client()

    # =========================================================================
    # PRUEBAS DEL ADMINISTRADOR GENERAL
    # =========================================================================
    def test_01_admin_login_exitoso_y_redireccion_a_admin(self):
        """Admin inicia sesión y es redirigido a /admin/"""
        res = self.client.post("/auth/login", data={
            "usuario": "admin@test.com",
            "password": "AdminSecret123"
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/admin/"))

    def test_02_admin_accede_a_panel_admin(self):
        """Admin accede a /admin/ y visualiza el panel con status 200"""
        self.client.post("/auth/login", data={
            "usuario": "admin@test.com",
            "password": "AdminSecret123"
        }, follow_redirects=True)

        res = self.client.get("/admin/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Administración", res.get_data(as_text=True))
        self.assertIn("Fincas Registradas", res.get_data(as_text=True))
        self.assertIn("Finca La Esperanza", res.get_data(as_text=True))
        self.assertIn("Finca El Paraiso", res.get_data(as_text=True))

    def test_03_admin_bloqueado_de_rutas_operativas(self):
        """Admin intentando acceder a rutas operativas es redirigido a /admin/"""
        self.client.post("/auth/login", data={
            "usuario": "admin@test.com",
            "password": "AdminSecret123"
        }, follow_redirects=True)

        rutas_operativas = [
            "/",
            "/trabajadores/",
            "/produccion-cafe/",
            "/produccion-platano/",
            "/gastos/",
            "/ventas/",
            "/inventario/",
            "/reportes/"
        ]

        for ruta in rutas_operativas:
            with self.subTest(ruta=ruta):
                res = self.client.get(ruta, follow_redirects=False)
                self.assertEqual(res.status_code, 302, f"Falló en ruta {ruta}")
                self.assertTrue(res.headers["Location"].endswith("/admin/"))

    def test_04_admin_autenticado_visita_login(self):
        """Admin ya autenticado que visita /auth/login es redirigido a /admin/"""
        self.client.post("/auth/login", data={
            "usuario": "admin@test.com",
            "password": "AdminSecret123"
        }, follow_redirects=True)

        res = self.client.get("/auth/login", follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/admin/"))

    def test_05_admin_cierra_sesion_correctamente(self):
        """Admin puede cerrar sesión y es redirigido al login"""
        self.client.post("/auth/login", data={
            "usuario": "admin@test.com",
            "password": "AdminSecret123"
        }, follow_redirects=True)

        res = self.client.get("/auth/logout", follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/auth/login"))

    # =========================================================================
    # PRUEBAS DE USUARIO NORMAL CON FINCA 1
    # =========================================================================
    def test_06_usuario_finca1_login_y_dashboard(self):
        """Usuario de finca 1 inicia sesión y va al dashboard /"""
        res = self.client.post("/auth/login", data={
            "usuario": "operador1@test.com",
            "password": "OperadorPass1"
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/"))

        # Acceder al dashboard
        dash = self.client.get("/", follow_redirects=True)
        self.assertEqual(dash.status_code, 200)
        self.assertIn("Finca La Esperanza", dash.get_data(as_text=True))

    def test_07_usuario_finca1_bloqueado_de_admin(self):
        """Usuario normal que intenta acceder a /admin/ es devuelto a su dashboard"""
        self.client.post("/auth/login", data={
            "usuario": "operador1@test.com",
            "password": "OperadorPass1"
        }, follow_redirects=True)

        res = self.client.get("/admin/", follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/"))

    # =========================================================================
    # PRUEBAS DE USUARIO NORMAL CON FINCA 2
    # =========================================================================
    def test_08_usuario_finca2_login_y_dashboard(self):
        """Usuario de finca 2 inicia sesión y ve los datos de su propia finca"""
        res = self.client.post("/auth/login", data={
            "usuario": "operador2@test.com",
            "password": "OperadorPass2"
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/"))

        dash = self.client.get("/", follow_redirects=True)
        self.assertEqual(dash.status_code, 200)
        self.assertIn("Finca El Paraiso", dash.get_data(as_text=True))

    def test_09_usuario_finca2_bloqueado_de_admin(self):
        """Usuario normal de finca 2 intentando acceder a /admin/ es devuelto a /"""
        self.client.post("/auth/login", data={
            "usuario": "operador2@test.com",
            "password": "OperadorPass2"
        }, follow_redirects=True)

        res = self.client.get("/admin/", follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/"))

    # =========================================================================
    # PRUEBAS DE USUARIO SIN FINCA ASOCIADA
    # =========================================================================
    def test_10_usuario_sin_finca_bloqueado_en_login(self):
        """Usuario normal sin finca no puede iniciar sesión"""
        res = self.client.post("/auth/login", data={
            "usuario": "sinfinca@test.com",
            "password": "SinFincaPass"
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/auth/login"))

        # Seguir redirección y verificar mensaje de aviso
        pagina = self.client.get(res.headers["Location"])
        self.assertIn("Tu usuario no tiene una finca asignada", pagina.get_data(as_text=True))

    # =========================================================================
    # PRUEBAS DE USUARIO ANÓNIMO (NO AUTENTICADO)
    # =========================================================================
    def test_11_anonimo_bloqueado_de_admin_y_dashboard(self):
        """Usuario no autenticado es redirigido a login"""
        res_admin = self.client.get("/admin/", follow_redirects=False)
        self.assertEqual(res_admin.status_code, 302)
        self.assertIn("/auth/login", res_admin.headers["Location"])

        res_dash = self.client.get("/", follow_redirects=False)
        self.assertEqual(res_dash.status_code, 302)
        self.assertIn("/auth/login", res_dash.headers["Location"])


if __name__ == "__main__":
    unittest.main()
