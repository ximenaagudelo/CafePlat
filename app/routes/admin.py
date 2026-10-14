import functools
import re

import os

from pathlib import Path

from uuid import uuid4

from flask_wtf.csrf import generate_csrf, validate_csrf

from wtforms.validators import ValidationError



from flask import (

    Blueprint,

    render_template,

    request,

    redirect,

    url_for,

    flash,

    current_app
)

from flask_login import login_required, current_user

from werkzeug.utils import secure_filename



from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.extensions import db

from app.models import Finca, Usuario



admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.context_processor
def incluir_csrf():
    """Proporciona un generador de token a las plantillas administrativas."""
    return {"csrf_token": generate_csrf}




PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2 MB





def admin_required(f):

    @functools.wraps(f)

    def decorated_function(*args, **kwargs):

        if not current_user.is_authenticated:

            return redirect(url_for("auth.login"))

        if not current_user.is_admin:

            flash("No tienes permisos de administrador para acceder a esta sección.", "danger")

            return redirect(url_for("dashboard.index"))

        return f(*args, **kwargs)

    return decorated_function





def validar_csrf():
    """Valida el token firmado del formulario antes de guardar datos o logos."""
    try:
        validate_csrf(request.form.get("csrf_token"))
        return True
    except ValidationError:
        return False


def obtener_directorio_uploads():

    upload_folder = Path(current_app.config.get(

        "FINCAS_UPLOAD_FOLDER",

        Path(current_app.root_path) / "static" / "uploads" / "fincas"

    ))

    upload_folder.mkdir(parents=True, exist_ok=True)

    return upload_folder





def procesar_archivo_logo(file_storage):

    """

    Valida y guarda un archivo PNG de logo en el directorio de uploads.

    Retorna (ruta_relativa, error_msg, ruta_absoluta_guardada).

    """

    if not file_storage or file_storage.filename == "":

        return None, None, None



    filename = file_storage.filename

    if not filename.lower().endswith(".png"):

        return None, "Solo se admiten imágenes en formato PNG (.png).", None



    contenido = file_storage.read()

    file_storage.seek(0)



    if len(contenido) > MAX_LOGO_SIZE:

        return None, "El logo no debe superar los 2 MB.", None



    if len(contenido) < 8 or contenido[:8] != PNG_SIGNATURE:

        return None, "El archivo suministrado no contiene una imagen PNG válida.", None



    safe_name = secure_filename(filename)

    if not safe_name.lower().endswith(".png"):

        safe_name = f"{safe_name}.png"

    unique_filename = f"{uuid4().hex}_{safe_name}"



    upload_dir = obtener_directorio_uploads()

    target_path = upload_dir / unique_filename



    try:

        with open(target_path, "wb") as f:

            f.write(contenido)

    except Exception as e:

        return None, f"Error al guardar el archivo: {type(e).__name__}", None



    rel_path = f"uploads/fincas/{unique_filename}"

    return rel_path, None, target_path





def eliminar_archivo_logo_anterior(logo_relativo):

    """

    Elimina un archivo de logo previamente subido.

    NUNCA elimina logos estáticos como 'img/gerluz-isotipo.png'.

    """

    if not logo_relativo:

        return

    if not logo_relativo.startswith("uploads/fincas/"):

        return



    upload_dir = obtener_directorio_uploads()

    file_name = Path(logo_relativo).name

    target = upload_dir / file_name

    if target.exists():

        try:

            target.unlink()

        except OSError:

            pass





@admin_bp.route("/")

@login_required

@admin_required

def index():

    fincas = Finca.query.all()

    usuarios = Usuario.query.all()

    total_fincas = len(fincas)

    total_usuarios = len(usuarios)

    return render_template(

        "admin/index.html",

        fincas=fincas,

        usuarios=usuarios,

        total_fincas=total_fincas,

        total_usuarios=total_usuarios

    )





@admin_bp.route("/fincas")

@login_required

@admin_required

def fincas():

    fincas_list = Finca.query.order_by(Finca.id).all()

    return render_template("admin/fincas.html", fincas=fincas_list)





@admin_bp.route("/fincas/nueva", methods=["GET", "POST"])

@login_required

@admin_required

def nueva_finca():

    if request.method == "POST":

        if not validar_csrf():

            flash("Error de validación CSRF. Por favor recarga el formulario.", "danger")

            return redirect(url_for("admin.nueva_finca"))



        codigo = request.form.get("codigo", "").strip().upper()

        nombre = request.form.get("nombre", "").strip()

        propietario = request.form.get("propietario", "").strip()

        ubicacion = request.form.get("ubicacion", "").strip()



        # Validaciones de campos obligatorios

        if not codigo:

            flash("El código de la finca es obligatorio.", "danger")

            return render_template(

                "admin/finca_formulario.html",

                finca=None,

                codigo=codigo,

                nombre=nombre,

                propietario=propietario,

                ubicacion=ubicacion

            )



        if len(codigo) > 50:

            flash("El código no puede exceder los 50 caracteres.", "danger")

            return render_template(

                "admin/finca_formulario.html",

                finca=None,

                codigo=codigo,

                nombre=nombre,

                propietario=propietario,

                ubicacion=ubicacion

            )



        if not nombre:

            flash("El nombre de la finca es obligatorio.", "danger")

            return render_template(

                "admin/finca_formulario.html",

                finca=None,

                codigo=codigo,

                nombre=nombre,

                propietario=propietario,

                ubicacion=ubicacion

            )



        if len(nombre) > 150:

            flash("El nombre no puede exceder los 150 caracteres.", "danger")

            return render_template(

                "admin/finca_formulario.html",

                finca=None,

                codigo=codigo,

                nombre=nombre,

                propietario=propietario,

                ubicacion=ubicacion

            )



        if propietario and len(propietario) > 150:

            flash("El propietario no puede exceder los 150 caracteres.", "danger")

            return render_template(

                "admin/finca_formulario.html",

                finca=None,

                codigo=codigo,

                nombre=nombre,

                propietario=propietario,

                ubicacion=ubicacion

            )



        if ubicacion and len(ubicacion) > 255:

            flash("La ubicación no puede exceder los 255 caracteres.", "danger")

            return render_template(

                "admin/finca_formulario.html",

                finca=None,

                codigo=codigo,

                nombre=nombre,

                propietario=propietario,

                ubicacion=ubicacion

            )



        # Unicidad de código

        finca_existente = Finca.query.filter_by(codigo=codigo).first()

        if finca_existente:

            flash(f"Ya existe una finca con el código '{codigo}'.", "danger")

            return render_template(

                "admin/finca_formulario.html",

                finca=None,

                codigo=codigo,

                nombre=nombre,

                propietario=propietario,

                ubicacion=ubicacion

            )



        # Procesar logo

        archivo_logo = request.files.get("logo")

        nuevo_archivo_guardado = None

        logo_relativo = None



        if archivo_logo and archivo_logo.filename != "":

            logo_relativo, error_logo, nuevo_archivo_guardado = procesar_archivo_logo(archivo_logo)

            if error_logo:

                flash(error_logo, "danger")

                return render_template(

                    "admin/finca_formulario.html",

                    finca=None,

                    codigo=codigo,

                    nombre=nombre,

                    propietario=propietario,

                    ubicacion=ubicacion

                )

        else:

            # Fallback especial para GERLUZ

            if codigo == "GERLUZ":

                logo_relativo = "img/gerluz-isotipo.png"



        try:

            nueva = Finca(

                codigo=codigo,

                nombre=nombre,

                propietario=propietario or None,

                ubicacion=ubicacion or None,

                logo=logo_relativo

            )

            db.session.add(nueva)

            db.session.commit()

            flash(f"Finca '{nombre}' creada exitosamente.", "success")

            return redirect(url_for("admin.fincas"))

        except Exception:

            db.session.rollback()

            if nuevo_archivo_guardado and os.path.exists(nuevo_archivo_guardado):

                try:

                    os.remove(nuevo_archivo_guardado)

                except OSError:

                    pass

            flash("Error al registrar la finca en la base de datos.", "danger")

            return render_template(

                "admin/finca_formulario.html",

                finca=None,

                codigo=codigo,

                nombre=nombre,

                propietario=propietario,

                ubicacion=ubicacion

            )



    return render_template("admin/finca_formulario.html", finca=None)





@admin_bp.route("/fincas/<int:id>/editar", methods=["GET", "POST"])

@login_required

@admin_required

def editar_finca(id):

    finca_obj = Finca.query.get_or_404(id)



    if request.method == "POST":

        if not validar_csrf():

            flash("Error de validación CSRF. Por favor recarga el formulario.", "danger")

            return redirect(url_for("admin.editar_finca", id=id))



        codigo = request.form.get("codigo", "").strip().upper()

        nombre = request.form.get("nombre", "").strip()

        propietario = request.form.get("propietario", "").strip()

        ubicacion = request.form.get("ubicacion", "").strip()



        if not codigo:

            flash("El código de la finca es obligatorio.", "danger")

            return render_template(

                "admin/finca_formulario.html",

                finca=finca_obj,

                codigo=codigo,

                nombre=nombre,

                propietario=propietario,

                ubicacion=ubicacion

            )



        if len(codigo) > 50:

            flash("El código no puede exceder los 50 caracteres.", "danger")

            return render_template(

                "admin/finca_formulario.html",

                finca=finca_obj,

                codigo=codigo,

                nombre=nombre,

                propietario=propietario,

                ubicacion=ubicacion

            )



        if not nombre:

            flash("El nombre de la finca es obligatorio.", "danger")

            return render_template(

                "admin/finca_formulario.html",

                finca=finca_obj,

                codigo=codigo,

                nombre=nombre,

                propietario=propietario,

                ubicacion=ubicacion

            )



        if len(nombre) > 150:

            flash("El nombre no puede exceder los 150 caracteres.", "danger")

            return render_template(

                "admin/finca_formulario.html",

                finca=finca_obj,

                codigo=codigo,

                nombre=nombre,

                propietario=propietario,

                ubicacion=ubicacion

            )



        if propietario and len(propietario) > 150:

            flash("El propietario no puede exceder los 150 caracteres.", "danger")

            return render_template(

                "admin/finca_formulario.html",

                finca=finca_obj,

                codigo=codigo,

                nombre=nombre,

                propietario=propietario,

                ubicacion=ubicacion

            )



        if ubicacion and len(ubicacion) > 255:

            flash("La ubicación no puede exceder los 255 caracteres.", "danger")

            return render_template(

                "admin/finca_formulario.html",

                finca=finca_obj,

                codigo=codigo,

                nombre=nombre,

                propietario=propietario,

                ubicacion=ubicacion

            )



        # Unicidad de código excluyendo la finca actual

        otra_finca = Finca.query.filter(Finca.codigo == codigo, Finca.id != id).first()

        if otra_finca:

            flash(f"Ya existe otra finca con el código '{codigo}'.", "danger")

            return render_template(

                "admin/finca_formulario.html",

                finca=finca_obj,

                codigo=codigo,

                nombre=nombre,

                propietario=propietario,

                ubicacion=ubicacion

            )



        # Procesar logo si se subió un nuevo archivo

        archivo_logo = request.files.get("logo")

        nuevo_archivo_guardado = None

        antiguo_logo = finca_obj.logo

        reemplazo_logo = False



        if archivo_logo and archivo_logo.filename != "":

            logo_relativo, error_logo, nuevo_archivo_guardado = procesar_archivo_logo(archivo_logo)

            if error_logo:

                flash(error_logo, "danger")

                return render_template(

                    "admin/finca_formulario.html",

                    finca=finca_obj,

                    codigo=codigo,

                    nombre=nombre,

                    propietario=propietario,

                    ubicacion=ubicacion

                )

            finca_obj.logo = logo_relativo

            reemplazo_logo = True

        # Si no se subió archivo, se conserva el logo existente (finca_obj.logo no cambia)



        finca_obj.codigo = codigo

        finca_obj.nombre = nombre

        finca_obj.propietario = propietario or None

        finca_obj.ubicacion = ubicacion or None



        try:

            db.session.commit()

            # Si el reemplazo tuvo éxito, eliminar de forma segura el logo anterior si era un upload

            if reemplazo_logo and antiguo_logo:

                eliminar_archivo_logo_anterior(antiguo_logo)



            flash(f"Finca '{nombre}' actualizada exitosamente.", "success")

            return redirect(url_for("admin.fincas"))

        except Exception:

            db.session.rollback()

            if nuevo_archivo_guardado and os.path.exists(nuevo_archivo_guardado):

                try:

                    os.remove(nuevo_archivo_guardado)

                except OSError:

                    pass

            flash("Error al actualizar la finca en la base de datos.", "danger")

            return render_template(

                "admin/finca_formulario.html",

                finca=finca_obj,

                codigo=codigo,

                nombre=nombre,

                propietario=propietario,

                ubicacion=ubicacion

            )



    return render_template("admin/finca_formulario.html", finca=finca_obj)


# Gestión de usuarios operativos: acceso exclusivo del administrador general.
@admin_bp.route("/usuarios")
@login_required
@admin_required
def usuarios():
    usuarios_list = (
        Usuario.query.options(selectinload(Usuario.finca))
        .order_by(Usuario.id)
        .all()
    )
    return render_template("admin/usuarios.html", usuarios=usuarios_list)


@admin_bp.route("/usuarios/nuevo", methods=["GET", "POST"])
@login_required
@admin_required
def nuevo_usuario():
    fincas_list = Finca.query.order_by(Finca.nombre, Finca.id).all()
    datos = {"nombre": "", "email": "", "finca_id": ""}

    if request.method == "GET":
        finca_preseleccionada = request.args.get("finca_id", type=int)
        if any(finca.id == finca_preseleccionada for finca in fincas_list):
            datos["finca_id"] = str(finca_preseleccionada)
        return render_template(
            "admin/usuario_formulario.html", fincas=fincas_list,
            datos=datos, errores=[]
        )

    datos = {
        "nombre": request.form.get("nombre", "").strip(),
        "email": request.form.get("email", "").strip().lower(),
        "finca_id": request.form.get("finca_id", "").strip(),
    }

    def mostrar_error(errores, estado=400):
        # Las contraseñas nunca se envían de vuelta a la plantilla.
        return render_template(
            "admin/usuario_formulario.html", fincas=fincas_list,
            datos=datos, errores=errores
        ), estado

    if not validar_csrf():
        return mostrar_error([
            "El formulario venció o su token no es válido. Recárgalo antes de guardar."
        ])

    errores = []
    nombre = datos["nombre"]
    email = datos["email"]
    password = request.form.get("password", "")
    confirmar = request.form.get("confirmar_password", "")

    if not nombre:
        errores.append("El nombre de usuario es obligatorio.")
    elif len(nombre) > 80:
        errores.append("El nombre de usuario no puede exceder 80 caracteres.")
    elif any(ord(c) < 32 or ord(c) == 127 for c in nombre):
        errores.append("El nombre de usuario contiene caracteres no permitidos.")

    if not email:
        errores.append("El correo electrónico es obligatorio.")
    elif len(email) > 150:
        errores.append("El correo electrónico no puede exceder 150 caracteres.")
    elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        errores.append("Ingresa un correo electrónico válido.")

    if not password or not password.strip():
        errores.append("La contraseña es obligatoria.")
    elif not 8 <= len(password) <= 128:
        errores.append("La contraseña debe tener entre 8 y 128 caracteres.")
    if password != confirmar:
        errores.append("La confirmación de la contraseña no coincide.")

    try:
        finca_id = int(datos["finca_id"])
    except (ValueError, TypeError):
        finca_id = None
    finca_seleccionada = next(
        (finca for finca in fincas_list if finca.id == finca_id), None
    )
    if finca_seleccionada is None:
        errores.append("Selecciona una finca existente para este usuario.")

    if errores:
        return mostrar_error(errores)

    # El login admite nombre O correo. Evitar ambigüedad entre ambas columnas.
    identidades = [nombre.lower(), email.lower()]
    duplicado = Usuario.query.filter(
        or_(
            func.lower(Usuario.nombre).in_(identidades),
            func.lower(Usuario.email).in_(identidades),
        )
    ).first()
    if duplicado:
        return mostrar_error([
            "El nombre o el correo ya está utilizado por otra cuenta."
        ], 409)

    try:
        nuevo = Usuario(
            nombre=nombre,
            email=email,
            finca_id=finca_seleccionada.id,
            is_admin=False,
        )
        # Conserva exactamente la contraseña escrita; nunca se guarda texto plano.
        nuevo.set_password(password)
        db.session.add(nuevo)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return mostrar_error([
            "No se pudo crear la cuenta. Comprueba que nombre y correo estén disponibles y que la finca exista."
        ], 409)
    except Exception:
        db.session.rollback()
        return mostrar_error([
            "No se pudo guardar el usuario. Intenta nuevamente."
        ], 500)

    flash(f"Usuario '{nombre}' creado y asociado a '{finca_seleccionada.nombre}'.", "success")
    return redirect(url_for("admin.usuarios"))
