from app import create_app
from app.extensions import db
from app.models import Finca, Usuario


# =====================================================
# DATOS DE LA FINCA
# =====================================================
CODIGO_FINCA = "FINCA2"
NOMBRE_FINCA = "La Esperanza"
PROPIETARIO = ""
UBICACION = "Pereira, Risaralda"
LOGO = None


# =====================================================
# DATOS DEL USUARIO
# =====================================================
NOMBRE_USUARIO = "LAESPERANZA"
EMAIL_USUARIO = "laesperanza@camposuite.local"
PASSWORD_TEMPORAL = "Admin123*"


app = create_app()


with app.app_context():

    if not EMAIL_USUARIO or EMAIL_USUARIO.strip() == "":
        raise ValueError("EMAIL_USUARIO no puede estar vacío.")

    # =========================
    # Crear o buscar finca
    # =========================
    finca = Finca.query.filter_by(codigo=CODIGO_FINCA).first()

    if not finca:
        finca = Finca(
            codigo=CODIGO_FINCA,
            nombre=NOMBRE_FINCA,
            propietario=PROPIETARIO,
            logo=LOGO,
            ubicacion=UBICACION
        )

        db.session.add(finca)
        db.session.commit()

        print("Finca creada correctamente.")
    else:
        print("La finca ya existía.")

    print(f"Finca ID: {finca.id}")
    print(f"Código: {finca.codigo}")
    print(f"Nombre: {finca.nombre}")

    # =========================
    # Crear o reparar usuario
    # =========================
    usuario = Usuario.query.filter_by(nombre=NOMBRE_USUARIO).first()

    if not usuario:
        usuario = Usuario.query.filter_by(email=EMAIL_USUARIO).first()

    if usuario:
        print("")
        print("Usuario encontrado. Se actualizará la asociación con la finca.")

        usuario.finca_id = finca.id
        usuario.nombre = NOMBRE_USUARIO
        usuario.email = EMAIL_USUARIO

        # Solo cambia la clave si quieres resetearla.
        usuario.set_password(PASSWORD_TEMPORAL)

        db.session.commit()

        print("Usuario actualizado correctamente.")
    else:
        usuario = Usuario(
            finca_id=finca.id,
            nombre=NOMBRE_USUARIO,
            email=EMAIL_USUARIO
        )

        usuario.set_password(PASSWORD_TEMPORAL)

        db.session.add(usuario)
        db.session.commit()

        print("")
        print("Usuario creado correctamente.")

    # =========================
    # Verificación final
    # =========================
    finca_verificada = Finca.query.filter_by(codigo=CODIGO_FINCA).first()
    usuario_verificado = Usuario.query.filter_by(nombre=NOMBRE_USUARIO).first()

    print("")
    print("VERIFICACIÓN FINAL")
    print("--------------------------------")

    if finca_verificada:
        print("Finca registrada:")
        print(f"ID: {finca_verificada.id}")
        print(f"Código: {finca_verificada.codigo}")
        print(f"Nombre: {finca_verificada.nombre}")
    else:
        print("ERROR: La finca no quedó registrada.")

    print("")

    if usuario_verificado:
        print("Usuario registrado:")
        print(f"ID: {usuario_verificado.id}")
        print(f"Usuario: {usuario_verificado.nombre}")
        print(f"Email: {usuario_verificado.email}")
        print(f"Finca ID asociada: {usuario_verificado.finca_id}")
    else:
        print("ERROR: El usuario no quedó registrado.")

    print("")
    print("Datos de acceso:")
    print(f"Usuario: {NOMBRE_USUARIO}")
    print(f"Email: {EMAIL_USUARIO}")
    print(f"Contraseña temporal: {PASSWORD_TEMPORAL}")