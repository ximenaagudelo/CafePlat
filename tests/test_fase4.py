import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import Finca, Usuario

MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
    b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)


class TestFase4GestionFincasYLogos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Directorios temporales exclusivos para DB y Uploads
        cls._temp_db_dir = tempfile.TemporaryDirectory()
        cls._temp_upload_dir = tempfile.TemporaryDirectory()

        cls.test_db_path = (Path(cls._temp_db_dir.name) / "test_fase4_isolated.db").resolve()
        cls.test_upload_dir = Path(cls._temp_upload_dir.name).resolve()

        # 2. Inicializar la app configurando DB y Uploads antes de db.init_app
        cls.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{cls.test_db_path.as_posix()}",
            "FINCAS_UPLOAD_FOLDER": str(cls.test_upload_dir),
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "clave-segura-fase4-test"
        })

        # 3. Comprobaciones de seguridad obligatorias (Kill-Switch)
        with cls.app.app_context():
            engine_db = Path(db.engine.url.database).resolve()
            expected_db = cls.test_db_path.resolve()
            if engine_db != expected_db:
                raise RuntimeError(
                    f"KILL-SWITCH ACTIVADO: Motor DB ({engine_db}) no coincide con esperado ({expected_db})."
                )

            effective_upload = Path(cls.app.config["FINCAS_UPLOAD_FOLDER"]).resolve()
            expected_upload = cls.test_upload_dir.resolve()
            if effective_upload != expected_upload:
                raise RuntimeError(
                    f"KILL-SWITCH ACTIVADO: Directorio Uploads ({effective_upload}) no coincide con esperado ({expected_upload})."
                )

            db.create_all()

            # Finca inicial
            finca_inicial = Finca(
                codigo="FINCA_BASE",
                nombre="Finca Base Inicial",
                propietario="Don Pedro",
                ubicacion="Vereda La Linda",
                logo=None
            )
            db.session.add(finca_inicial)
            db.session.commit()

            # Admin
            admin = Usuario(
                nombre="AdminFase4",
                email="admin_fase4@test.com",
                is_admin=True,
                finca_id=None
            )
            admin.set_password("AdminPass4")

            # Operador normal asociado a finca_inicial
            operador = Usuario(
                nombre="OperadorFase4",
                email="operador_fase4@test.com",
                is_admin=False,
                finca_id=finca_inicial.id
            )
            operador.set_password("OperadorPass4")

            db.session.add_all([admin, operador])
            db.session.commit()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.engine.dispose()
        try:
            cls._temp_db_dir.cleanup()
        except Exception:
            pass
        try:
            cls._temp_upload_dir.cleanup()
        except Exception:
            pass

    def setUp(self):
        self.client = self.app.test_client()

    def _login_admin(self):
        return self.client.post("/auth/login", data={
            "usuario": "admin_fase4@test.com",
            "password": "AdminPass4"
        }, follow_redirects=True)

    def _login_operador(self):
        return self.client.post("/auth/login", data={
            "usuario": "operador_fase4@test.com",
            "password": "OperadorPass4"
        }, follow_redirects=True)

    # =========================================================================
    # 1. BLOQUEO DE USUARIO NORMAL
    # =========================================================================
    def test_01_usuario_normal_bloqueado_de_rutas_fincas(self):
        """Usuario operador normal es bloqueado de todas las rutas de fincas en admin"""
        self._login_operador()

        rutas = [
            ("/admin/fincas", "GET"),
            ("/admin/fincas/nueva", "GET"),
            ("/admin/fincas/nueva", "POST"),
            ("/admin/fincas/1/editar", "GET"),
            ("/admin/fincas/1/editar", "POST")
        ]

        for ruta, metodo in rutas:
            with self.subTest(ruta=ruta, metodo=metodo):
                if metodo == "GET":
                    res = self.client.get(ruta, follow_redirects=False)
                else:
                    res = self.client.post(ruta, data={}, follow_redirects=False)
                self.assertEqual(res.status_code, 302)
                self.assertTrue(res.headers["Location"].endswith("/"))

    # =========================================================================
    # 2. LISTADO DE FINCAS
    # =========================================================================
    def test_02_admin_lista_fincas(self):
        """Admin accede a /admin/fincas y visualiza la lista con status 200"""
        self._login_admin()
        res = self.client.get("/admin/fincas")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Gestión de Fincas", html)
        self.assertIn("FINCA_BASE", html)
        self.assertIn("Finca Base Inicial", html)

    # =========================================================================
    # 3. CREACIÓN VÁLIDA Y NORMALIZACIÓN DE CÓDIGO
    # =========================================================================
    def test_03_admin_crear_finca_valida_y_normaliza_codigo(self):
        """Crear finca normaliza el código con mayúsculas y espacios eliminados"""
        self._login_admin()
        res = self.client.post("/admin/fincas/nueva", data={
            "codigo": "  cafetal_sur  ",
            "nombre": "  Finca El Cafetal Sur  ",
            "propietario": "Carlos Gómez",
            "ubicacion": "Chinchiná, Caldas"
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/admin/fincas"))

        with self.app.app_context():
            creada = Finca.query.filter_by(codigo="CAFETAL_SUR").first()
            self.assertIsNotNone(creada)
            self.assertEqual(creada.nombre, "Finca El Cafetal Sur")
            self.assertEqual(creada.propietario, "Carlos Gómez")
            self.assertEqual(creada.ubicacion, "Chinchiná, Caldas")
            self.assertIsNone(creada.logo)

    # =========================================================================
    # 4. DUPLICADOS RECHAZADOS AL CREAR
    # =========================================================================
    def test_04_admin_crear_finca_codigo_duplicado_rechazado(self):
        """No permite registrar una finca con código ya existente"""
        self._login_admin()
        res = self.client.post("/admin/fincas/nueva", data={
            "codigo": "finca_base",  # Ya existe FINCA_BASE
            "nombre": "Intento Duplicado"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Ya existe una finca con el código", html)

        with self.app.app_context():
            conteo = Finca.query.filter_by(codigo="FINCA_BASE").count()
            self.assertEqual(conteo, 1)

    # =========================================================================
    # 5. VALIDACIÓN DE CAMPOS OBLIGATORIOS Y LONGITUDES
    # =========================================================================
    def test_05_admin_crear_finca_validaciones_campos(self):
        """Valida obligatoriedad y longitudes de código y nombre"""
        self._login_admin()

        # Código vacío
        res = self.client.post("/admin/fincas/nueva", data={
            "codigo": "",
            "nombre": "Sin Código"
        }, follow_redirects=True)
        self.assertIn("código de la finca es obligatorio", res.get_data(as_text=True))

        # Nombre vacío
        res = self.client.post("/admin/fincas/nueva", data={
            "codigo": "COD_OK",
            "nombre": ""
        }, follow_redirects=True)
        self.assertIn("nombre de la finca es obligatorio", res.get_data(as_text=True))

        # Código mayor a 50
        res = self.client.post("/admin/fincas/nueva", data={
            "codigo": "A" * 51,
            "nombre": "Nombre OK"
        }, follow_redirects=True)
        self.assertIn("código no puede exceder los 50 caracteres", res.get_data(as_text=True))

        # Nombre mayor a 150
        res = self.client.post("/admin/fincas/nueva", data={
            "codigo": "COD_OK2",
            "nombre": "B" * 151
        }, follow_redirects=True)
        self.assertIn("nombre no puede exceder los 150 caracteres", res.get_data(as_text=True))

    # =========================================================================
    # 6. FALLBACK GERLUZ SIN LOGO
    # =========================================================================
    def test_06_admin_crear_finca_gerluz_fallback_logo(self):
        """Crear finca GERLUZ sin subir archivo asigna automáticamente 'img/gerluz-isotipo.png'"""
        self._login_admin()
        res = self.client.post("/admin/fincas/nueva", data={
            "codigo": "gerluz",
            "nombre": "Hacienda GERLUZ"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            gerluz = Finca.query.filter_by(codigo="GERLUZ").first()
            self.assertIsNotNone(gerluz)
            self.assertEqual(gerluz.logo, "img/gerluz-isotipo.png")

    # =========================================================================
    # 7. SUBIDA EXITOSA DE LOGO PNG
    # =========================================================================
    def test_07_admin_crear_finca_con_logo_png_valido(self):
        """Subida de logo PNG válido lo guarda en uploads configurado con ruta relativa en BD"""
        self._login_admin()

        data = {
            "codigo": "FINCA_LOGO",
            "nombre": "Finca Con Logo",
            "logo": (io.BytesIO(MINIMAL_PNG), "logotipo.png")
        }

        res = self.client.post("/admin/fincas/nueva", data=data, content_type="multipart/form-data", follow_redirects=False)
        self.assertEqual(res.status_code, 302)

        with self.app.app_context():
            finca = Finca.query.filter_by(codigo="FINCA_LOGO").first()
            self.assertIsNotNone(finca)
            self.assertIsNotNone(finca.logo)
            self.assertTrue(finca.logo.startswith("uploads/fincas/"))
            self.assertTrue(finca.logo.endswith(".png"))

            # Verificar que el archivo realmente existe en el directorio temporal configurado
            nombre_archivo = Path(finca.logo).name
            archivo_en_disco = self.test_upload_dir / nombre_archivo
            self.assertTrue(archivo_en_disco.exists())
            self.assertEqual(archivo_en_disco.read_bytes(), MINIMAL_PNG)

    # =========================================================================
    # 8. RECHAZO DE ARCHIVO NO PNG POR EXTENSIÓN
    # =========================================================================
    def test_08_admin_rechazar_archivo_no_png_extension(self):
        """Rechaza archivos cuya extensión no sea .png"""
        self._login_admin()

        data = {
            "codigo": "FINCA_JPG",
            "nombre": "Finca JPG",
            "logo": (io.BytesIO(MINIMAL_PNG), "logo.jpg")
        }

        res = self.client.post("/admin/fincas/nueva", data=data, content_type="multipart/form-data", follow_redirects=True)
        html = res.get_data(as_text=True)
        self.assertIn("Solo se admiten imágenes en formato PNG", html)

        with self.app.app_context():
            self.assertIsNone(Finca.query.filter_by(codigo="FINCA_JPG").first())

    # =========================================================================
    # 9. RECHAZO DE ARCHIVO CON EXTENSIÓN .PNG PERO CONTENIDO INVÁLIDO
    # =========================================================================
    def test_09_admin_rechazar_png_falso_contenido_invalido(self):
        """Rechaza archivos con extensión .png pero sin la firma real de PNG"""
        self._login_admin()

        falso_png = b"ESTO NO ES UN ARCHIVO PNG REAL EN ABSOLUTO"
        data = {
            "codigo": "FINCA_FAKE_PNG",
            "nombre": "Finca Fake PNG",
            "logo": (io.BytesIO(falso_png), "disfrazado.png")
        }

        res = self.client.post("/admin/fincas/nueva", data=data, content_type="multipart/form-data", follow_redirects=True)
        html = res.get_data(as_text=True)
        self.assertIn("no contiene una imagen PNG válida", html)

        with self.app.app_context():
            self.assertIsNone(Finca.query.filter_by(codigo="FINCA_FAKE_PNG").first())

    # =========================================================================
    # 10. RECHAZO DE ARCHIVO QUE EXCEDE 2 MB
    # =========================================================================
    def test_10_admin_rechazar_archivo_excede_2mb(self):
        """Rechaza imágenes PNG cuyo tamaño exceda los 2 MB"""
        self._login_admin()

        # 2 MB + 100 bytes comenzando con firma PNG
        png_gigante = b"\x89PNG\r\n\x1a\n" + (b"X" * (2 * 1024 * 1024 + 100))
        data = {
            "codigo": "FINCA_GRANDE",
            "nombre": "Finca Logo Grande",
            "logo": (io.BytesIO(png_gigante), "pesado.png")
        }

        res = self.client.post("/admin/fincas/nueva", data=data, content_type="multipart/form-data", follow_redirects=True)
        html = res.get_data(as_text=True)
        self.assertIn("El logo no debe superar los 2 MB", html)

        with self.app.app_context():
            self.assertIsNone(Finca.query.filter_by(codigo="FINCA_GRANDE").first())

    # =========================================================================
    # 11. EDICIÓN SIN SUBIR LOGO CONSERVA EL EXISTENTE
    # =========================================================================
    def test_11_admin_editar_finca_sin_subir_logo_conserva_existente(self):
        """Editar una finca sin seleccionar nuevo archivo conserva el logo anterior"""
        self._login_admin()

        with self.app.app_context():
            finca = Finca(codigo="FINCA_EDIT_LOGO", nombre="Original", logo="uploads/fincas/logo_viejo.png")
            db.session.add(finca)
            db.session.commit()
            finca_id = finca.id

        res = self.client.post(f"/admin/fincas/{finca_id}/editar", data={
            "codigo": "FINCA_EDIT_LOGO",
            "nombre": "Nombre Editado",
            "propietario": "Nuevo Dueño"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            actualizada = Finca.query.get(finca_id)
            self.assertEqual(actualizada.nombre, "Nombre Editado")
            self.assertEqual(actualizada.logo, "uploads/fincas/logo_viejo.png")

    # =========================================================================
    # 12. EDICIÓN Y COMPROBACIÓN DE DUPLICADOS EXCLUYENDO LA FINCA ACTUAL
    # =========================================================================
    def test_12_admin_editar_finca_duplicados_excluye_actual(self):
        """Permite conservar el propio código pero rechaza usar el código de otra finca"""
        self._login_admin()

        with self.app.app_context():
            f_a = Finca(codigo="FINCA_ALFA", nombre="Alfa")
            f_b = Finca(codigo="FINCA_BETA", nombre="Beta")
            db.session.add_all([f_a, f_b])
            db.session.commit()
            id_a = f_a.id

        # Intentar ponerle a Alfa el código de Beta -> RECHAZADO
        res_dup = self.client.post(f"/admin/fincas/{id_a}/editar", data={
            "codigo": "FINCA_BETA",
            "nombre": "Alfa Intentando ser Beta"
        }, follow_redirects=True)
        self.assertIn("Ya existe otra finca con el código", res_dup.get_data(as_text=True))

        # Editar Alfa manteniendo su propio código FINCA_ALFA -> PERMITIDO
        res_ok = self.client.post(f"/admin/fincas/{id_a}/editar", data={
            "codigo": "FINCA_ALFA",
            "nombre": "Alfa Renombrada"
        }, follow_redirects=False)
        self.assertEqual(res_ok.status_code, 302)

        with self.app.app_context():
            f_actualizada = Finca.query.get(id_a)
            self.assertEqual(f_actualizada.nombre, "Alfa Renombrada")

    # =========================================================================
    # 13. REEMPLAZO DE LOGO Y ELIMINACIÓN SEGURA DEL ANTERIOR
    # =========================================================================
    def test_13_admin_editar_finca_reemplazar_logo(self):
        """Al subir un nuevo logo, se guarda el nuevo y se elimina el logo subido anterior"""
        self._login_admin()

        # Crear archivo viejo en test_upload_dir
        nombre_viejo = "logo_anterior_uuid.png"
        archivo_viejo_disco = self.test_upload_dir / nombre_viejo
        archivo_viejo_disco.write_bytes(MINIMAL_PNG)

        with self.app.app_context():
            finca = Finca(
                codigo="FINCA_REEMP",
                nombre="Finca Reemplazo",
                logo=f"uploads/fincas/{nombre_viejo}"
            )
            db.session.add(finca)
            db.session.commit()
            finca_id = finca.id

        self.assertTrue(archivo_viejo_disco.exists())

        # Subir nuevo logo
        nuevo_png_bytes = MINIMAL_PNG + b"\x00"
        res = self.client.post(f"/admin/fincas/{finca_id}/editar", data={
            "codigo": "FINCA_REEMP",
            "nombre": "Finca Reemplazo OK",
            "logo": (io.BytesIO(nuevo_png_bytes), "nuevo_logo.png")
        }, content_type="multipart/form-data", follow_redirects=False)

        self.assertEqual(res.status_code, 302)

        with self.app.app_context():
            actualizada = Finca.query.get(finca_id)
            # El logo viejo se borró del disco
            self.assertFalse(archivo_viejo_disco.exists())

            # El nuevo existe en disco
            nombre_nuevo = Path(actualizada.logo).name
            archivo_nuevo_disco = self.test_upload_dir / nombre_nuevo
            self.assertTrue(archivo_nuevo_disco.exists())
            self.assertEqual(archivo_nuevo_disco.read_bytes(), nuevo_png_bytes)

    # =========================================================================
    # 14. NUNCA ELIMINAR EL LOGO ESTÁTICO DE GERLUZ AL REEMPLAZAR
    # =========================================================================
    def test_14_admin_reemplazo_no_elimina_logo_estatico_gerluz(self):
        """Si la finca tenía 'img/gerluz-isotipo.png', nunca se borra ni se toca al subir nuevo logo"""
        self._login_admin()

        with self.app.app_context():
            finca = Finca(
                codigo="GERLUZ_STATIC_TEST",
                nombre="Prueba Gerluz",
                logo="img/gerluz-isotipo.png"
            )
            db.session.add(finca)
            db.session.commit()
            finca_id = finca.id

        # Simular reemplazar logo
        res = self.client.post(f"/admin/fincas/{finca_id}/editar", data={
            "codigo": "GERLUZ_STATIC_TEST",
            "nombre": "Prueba Gerluz Con Logo Nuevo",
            "logo": (io.BytesIO(MINIMAL_PNG), "gerluz_nuevo.png")
        }, content_type="multipart/form-data", follow_redirects=False)

        self.assertEqual(res.status_code, 302)

        # Verificar que el logo original estático en app/static/img/gerluz-isotipo.png existe intacto
        static_gerluz = Path(self.app.root_path) / "static" / "img" / "gerluz-isotipo.png"
        self.assertTrue(static_gerluz.exists(), "El archivo estático de GERLUZ jamás debe ser eliminado!")

    # =========================================================================
    # 15. ROLLBACK DE BD ELIMINA ÚNICAMENTE EL ARCHIVO NUEVO GENERADO
    # =========================================================================
    def test_15_rollback_bd_elimina_nuevo_archivo_generado(self):
        """Si ocurre un error en la base de datos al guardar, el archivo nuevo subido se elimina"""
        self._login_admin()

        # Provocamos un fallo en db.session.commit simulando un error inesperado
        with patch("app.routes.admin.db.session.commit", side_effect=RuntimeError("Fallo simulado")):
            archivos_antes = set(self.test_upload_dir.glob("*.png"))

            data = {
                "codigo": "FINCA_FAIL_ROLLBACK",
                "nombre": "Finca Falla",
                "logo": (io.BytesIO(MINIMAL_PNG), "falla.png")
            }
            res = self.client.post("/admin/fincas/nueva", data=data, content_type="multipart/form-data", follow_redirects=True)
            self.assertIn("Error al registrar la finca en la base de datos", res.get_data(as_text=True))

            archivos_despues = set(self.test_upload_dir.glob("*.png"))
            self.assertEqual(archivos_antes, archivos_despues, "El archivo nuevo no debe permanecer si falló la BD")


if __name__ == "__main__":
    unittest.main()
