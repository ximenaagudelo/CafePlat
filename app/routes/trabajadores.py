from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import func

from app.extensions import db
from app.models import Trabajador, RegistroTrabajo


trabajadores_bp = Blueprint(
    "trabajadores",
    __name__,
    url_prefix="/trabajadores"
)


def obtener_finca_activa():
    """
    Obtiene la finca asociada al usuario autenticado.

    Desde el Paso 14, CaféPlat ya no debe usar una finca fija temporal.
    Cada usuario debe trabajar únicamente con la finca que tiene asociada.
    """
    if not current_user.is_authenticated or not current_user.finca:
        abort(403)

    return current_user.finca


def convertir_decimal(valor):
    if valor is None or valor == "":
        return None

    try:
        return Decimal(valor)
    except InvalidOperation:
        raise ValueError("El valor ingresado no es válido.")


def procesar_datos_registro(registro, finca_activa):
    trabajador_id = request.form.get("trabajador_id")
    fecha_texto = request.form.get("fecha")
    tipo_trabajo = request.form.get("tipo_trabajo")

    if not trabajador_id or not fecha_texto or not tipo_trabajo:
        raise ValueError("Trabajador, fecha y tipo de trabajo son obligatorios.")

    trabajador = (
        Trabajador.query
        .filter_by(id=int(trabajador_id), finca_id=finca_activa.id)
        .first()
    )

    if not trabajador:
        raise ValueError("El trabajador seleccionado no pertenece a la finca activa.")

    fecha = datetime.strptime(fecha_texto, "%Y-%m-%d").date()

    kilos_cafe = convertir_decimal(request.form.get("kilos_cafe"))
    precio_kilo = convertir_decimal(request.form.get("precio_kilo"))
    valor_dia = convertir_decimal(request.form.get("valor_dia"))

    if tipo_trabajo == "recoleccion_cafe":
        if kilos_cafe is None or precio_kilo is None:
            raise ValueError("Para recolección de café debes ingresar kilos y precio por kilo.")

        total_pagar = kilos_cafe * precio_kilo
        valor_dia = None
    else:
        if valor_dia is None:
            raise ValueError("Para este trabajo debes ingresar el valor del día.")

        total_pagar = valor_dia
        kilos_cafe = None
        precio_kilo = None

    pagado = request.form.get("pagado") == "on"

    registro.finca_id = finca_activa.id
    registro.trabajador_id = trabajador.id
    registro.fecha = fecha
    registro.tipo_trabajo = tipo_trabajo
    registro.kilos_cafe = kilos_cafe
    registro.precio_kilo = precio_kilo
    registro.valor_dia = valor_dia
    registro.total_pagar = total_pagar
    registro.pagado = pagado

    return registro


@trabajadores_bp.route("/")
@login_required
def index():
    finca_activa = obtener_finca_activa()

    trabajadores = (
        Trabajador.query
        .filter_by(finca_id=finca_activa.id)
        .order_by(Trabajador.nombre.asc())
        .all()
    )

    trabajador_id = request.args.get("trabajador_id", "")
    fecha_inicio = request.args.get("fecha_inicio", "")
    fecha_fin = request.args.get("fecha_fin", "")
    estado_pago = request.args.get("estado_pago", "")

    registros_query = (
        RegistroTrabajo.query
        .filter_by(finca_id=finca_activa.id)
        .join(Trabajador)
    )

    if trabajador_id:
        registros_query = registros_query.filter(
            RegistroTrabajo.trabajador_id == int(trabajador_id)
        )

    if fecha_inicio:
        fecha_inicio_obj = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        registros_query = registros_query.filter(
            RegistroTrabajo.fecha >= fecha_inicio_obj
        )

    if fecha_fin:
        fecha_fin_obj = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        registros_query = registros_query.filter(
            RegistroTrabajo.fecha <= fecha_fin_obj
        )

    if estado_pago == "pagado":
        registros_query = registros_query.filter(RegistroTrabajo.pagado == True)

    if estado_pago == "pendiente":
        registros_query = registros_query.filter(RegistroTrabajo.pagado == False)

    total_pendiente = (
        registros_query
        .with_entities(func.coalesce(func.sum(RegistroTrabajo.total_pagar), 0))
        .filter(RegistroTrabajo.pagado == False)
        .scalar()
    )

    total_pagado = (
        registros_query
        .with_entities(func.coalesce(func.sum(RegistroTrabajo.total_pagar), 0))
        .filter(RegistroTrabajo.pagado == True)
        .scalar()
    )

    total_general = (
        registros_query
        .with_entities(func.coalesce(func.sum(RegistroTrabajo.total_pagar), 0))
        .scalar()
    )

    total_kilos_cafe = (
        registros_query
        .with_entities(func.coalesce(func.sum(RegistroTrabajo.kilos_cafe), 0))
        .filter(RegistroTrabajo.tipo_trabajo == "recoleccion_cafe")
        .scalar()
    )

    registros = (
        registros_query
        .order_by(RegistroTrabajo.fecha.desc(), RegistroTrabajo.id.desc())
        .all()
    )

    filtros = {
        "trabajador_id": trabajador_id,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "estado_pago": estado_pago
    }

    return render_template(
        "trabajadores/index.html",
        trabajadores=trabajadores,
        registros=registros,
        total_pendiente=total_pendiente,
        total_pagado=total_pagado,
        total_general=total_general,
        total_kilos_cafe=total_kilos_cafe,
        filtros=filtros,
        finca_activa=finca_activa
    )


@trabajadores_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
def nuevo():
    finca_activa = obtener_finca_activa()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()

        if not nombre:
            flash("El nombre del trabajador es obligatorio.", "danger")
            return redirect(url_for("trabajadores.nuevo"))

        trabajador = Trabajador(
            finca_id=finca_activa.id,
            nombre=nombre,
            estado="activo"
        )

        db.session.add(trabajador)
        db.session.commit()

        flash("Trabajador creado correctamente.", "success")
        return redirect(url_for("trabajadores.index"))

    return render_template(
        "trabajadores/formulario.html",
        trabajador=None,
        accion="Crear trabajador",
        finca_activa=finca_activa
    )


@trabajadores_bp.route("/<int:trabajador_id>/editar", methods=["GET", "POST"])
@login_required
def editar(trabajador_id):
    finca_activa = obtener_finca_activa()

    trabajador = (
        Trabajador.query
        .filter_by(id=trabajador_id, finca_id=finca_activa.id)
        .first_or_404()
    )

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        estado = request.form.get("estado", "activo")

        if not nombre:
            flash("El nombre del trabajador es obligatorio.", "danger")
            return redirect(url_for("trabajadores.editar", trabajador_id=trabajador.id))

        trabajador.nombre = nombre
        trabajador.estado = estado

        db.session.commit()

        flash("Trabajador actualizado correctamente.", "success")
        return redirect(url_for("trabajadores.index"))

    return render_template(
        "trabajadores/formulario.html",
        trabajador=trabajador,
        accion="Editar trabajador",
        finca_activa=finca_activa
    )


@trabajadores_bp.route("/trabajos/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_registro():
    finca_activa = obtener_finca_activa()

    trabajadores = (
        Trabajador.query
        .filter_by(estado="activo", finca_id=finca_activa.id)
        .order_by(Trabajador.nombre.asc())
        .all()
    )

    if request.method == "POST":
        try:
            registro = RegistroTrabajo()
            registro = procesar_datos_registro(registro, finca_activa)

            db.session.add(registro)
            db.session.commit()

            flash("Trabajo registrado correctamente.", "success")
            return redirect(url_for("trabajadores.index"))

        except ValueError as error:
            flash(str(error), "danger")
            return redirect(url_for("trabajadores.nuevo_registro"))

    return render_template(
        "trabajadores/registro_formulario.html",
        trabajadores=trabajadores,
        registro=None,
        accion="Registrar trabajo diario",
        hoy=date.today().isoformat(),
        finca_activa=finca_activa
    )


@trabajadores_bp.route("/trabajos/<int:registro_id>/editar", methods=["GET", "POST"])
@login_required
def editar_registro(registro_id):
    finca_activa = obtener_finca_activa()

    registro = (
        RegistroTrabajo.query
        .filter_by(id=registro_id, finca_id=finca_activa.id)
        .first_or_404()
    )

    trabajadores = (
        Trabajador.query
        .filter_by(estado="activo", finca_id=finca_activa.id)
        .order_by(Trabajador.nombre.asc())
        .all()
    )

    if request.method == "POST":
        try:
            registro = procesar_datos_registro(registro, finca_activa)

            db.session.commit()

            flash("Registro de trabajo actualizado correctamente.", "success")
            return redirect(url_for("trabajadores.index"))

        except ValueError as error:
            flash(str(error), "danger")
            return redirect(url_for("trabajadores.editar_registro", registro_id=registro.id))

    return render_template(
        "trabajadores/registro_formulario.html",
        trabajadores=trabajadores,
        registro=registro,
        accion="Editar registro de trabajo",
        hoy=date.today().isoformat(),
        finca_activa=finca_activa
    )


@trabajadores_bp.route("/trabajos/<int:registro_id>/pago", methods=["POST"])
@login_required
def cambiar_pago(registro_id):
    finca_activa = obtener_finca_activa()

    registro = (
        RegistroTrabajo.query
        .filter_by(id=registro_id, finca_id=finca_activa.id)
        .first_or_404()
    )

    registro.pagado = not registro.pagado
    db.session.commit()

    flash("Estado de pago actualizado.", "success")
    return redirect(url_for("trabajadores.index"))


@trabajadores_bp.route("/trabajos/<int:registro_id>/eliminar", methods=["POST"])
@login_required
def eliminar_registro(registro_id):
    finca_activa = obtener_finca_activa()

    registro = (
        RegistroTrabajo.query
        .filter_by(id=registro_id, finca_id=finca_activa.id)
        .first_or_404()
    )

    db.session.delete(registro)
    db.session.commit()

    flash("Registro de trabajo eliminado correctamente.", "success")
    return redirect(url_for("trabajadores.index"))
