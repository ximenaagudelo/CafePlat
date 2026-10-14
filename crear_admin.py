import os
import sys

from app import create_app
from app.extensions import db
from app.models import Usuario


def crear_admin():
    email = os.environ.get("ADMIN_EMAIL", "").strip()
    password = os.environ.get("ADMIN_PASSWORD")
    nombre = os.environ.get("ADMIN_NOMBRE", "").strip()

    if not email or not password or not nombre:
        print(
            "Error: Las variables de entorno ADMIN_EMAIL, ADMIN_PASSWORD y ADMIN_NOMBRE son obligatorias.",
            file=sys.stderr
        )
        sys.exit(1)

    app = create_app()
    with app.app_context():
        usuario_existente = Usuario.query.filter(
            (Usuario.email == email) | (Usuario.nombre == nombre)
        ).first()

        if usuario_existente:
            print(
                "Error: Ya existe un usuario registrado con el email o nombre proporcionado.",
                file=sys.stderr
            )
            sys.exit(1)

        try:
            admin = Usuario(
                nombre=nombre,
                email=email,
                is_admin=True,
                finca_id=None
            )
            admin.set_password(password)

            db.session.add(admin)
            db.session.commit()
            print(f"Administrador general '{nombre}' creado exitosamente.")
        except Exception as e:
            db.session.rollback()
            print(
                f"Error al guardar el administrador en la base de datos: {type(e).__name__}",
                file=sys.stderr
            )
            sys.exit(1)


if __name__ == "__main__":
    crear_admin()
