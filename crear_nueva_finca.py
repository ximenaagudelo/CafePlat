from app import create_app
from app.extensions import db
from app.models import Finca, Usuario


# =====================================================
# CONFIGURACIÓN DE LA NUEVA FINCA
# =====================================================
CODIGO_FINCA = "FINCA2"
NOMBRE_FINCA = "La Esperanza"
PROPIETARIO = ""
UBICACION = "Pereira, Risaralda"

# Sin logo
LOGO = None


# =====================================================
# CONFIGURACIÓN DEL USUARIO DE LA FINCA
# =====================================================
NOMBRE_USUARIO = "LAESPERANZA"

# Debe ser único. Puede ser un correo interno ficticio.
EMAIL_USUARIO = "laesperanza@camposuite.local"

PASSWORD_TEMPORAL = "Admin123*"


app = create_app()


with app.app_context():

    finca = Finca.query.filter_by(codigo=CODIGO_FINCA).first()

    if finca:
        print("La finca ya existe.")
        print(f"ID: {finca.id}")
        print(f"Código: {finca.codigo}")
        print(f"Nombre: {finca.nombre}")
    else:
        finca = Finca(
            codigo=CODIGO_FINCA,
            nombre=NOMBRE_FINCA,
            propietario=PROPIETARIO,
            logo=LOGO,
            ubicacion=UBICACION
        )

        db.session.add(finca)
        db.session.flush()

        print("Finca creada correctamente.")
        print(f"ID: {finca.id}")
        print(f"Código: {finca.codigo}")
        print(f"Nombre: {finca.nombre}")

    usuario_por_nombre = Usuario.query.filter_by(nombre=NOMBRE_USUARIO).first()
    usuario_por_email = Usuario.query.filter_by(email=EMAIL_USUARIO).first()

    if usuario_por_nombre:
        print("")
        print("El usuario ya existe por nombre.")
        print(f"ID: {usuario_por_nombre.id}")
        print(f"Usuario: {usuario_por_nombre.nombre}")
        print(f"Email: {usuario_por_nombre.email}")
        print(f"Finca ID asociada: {usuario_por_nombre.finca_id}")

    elif usuario_por_email:
        print("")
        print("Ya existe un usuario con ese email.")
        print(f"ID: {usuario_por_email.id}")
        print(f"Usuario: {usuario_por_email.nombre}")
        print(f"Email: {usuario_por_email.email}")
        print(f"Finca ID asociada: {usuario_por_email.finca_id}")

    else:
        usuario = Usuario(
            finca_id=finca.id,
            nombre=NOMBRE_USUARIO,
            email=EMAIL_USUARIO
        )

        usuario.set_password(PASSWORD_TEMPORAL)

        db.session.add(usuario)

        print("")
        print("Usuario base creado correctamente.")
        print(f"Usuario: {NOMBRE_USUARIO}")
        print(f"Email: {EMAIL_USUARIO}")
        print(f"Contraseña temporal: {PASSWORD_TEMPORAL}")
        print(f"Finca asociada: {NOMBRE_FINCA}")

    db.session.commit()

    print("")
    print("Proceso terminado correctamente.")
    print("--------------------------------")
    print(f"Finca: {NOMBRE_FINCA}")
    print(f"Código: {CODIGO_FINCA}")
    print(f"Usuario: {NOMBRE_USUARIO}")
    print(f"Email: {EMAIL_USUARIO}")
    print(f"Contraseña temporal: {PASSWORD_TEMPORAL}")