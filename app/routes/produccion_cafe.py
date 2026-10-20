from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_DOWN

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import func

from app.extensions import db
from app.models import ProduccionCafe, FlorecidaCafe
from app.services import cafe as conversion_cafe


produccion_cafe_bp = Blueprint(
    "produccion_cafe",
    __name__,
    url_prefix="/produccion-cafe"
)


def obtener_finca_activa():
    """
    Obtiene la finca asociada al usuario autenticado.

    CaféPlat es multi-finca. Por eso toda consulta del módulo de café
    debe estar filtrada por la finca activa del usuario actual.
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


def truncar_decimal(valor, decimales=2):
    """
    Trunca decimales sin redondear.
    Ejemplo: 20.839 -> 20.83
    """
    if valor is None:
        valor = Decimal("0")

    valor = Decimal(valor)
    cuantizador = Decimal("1").scaleb(-decimales)

    return valor.quantize(cuantizador, rounding=ROUND_DOWN)


@produccion_cafe_bp.app_template_filter("decimal_cafe")
def decimal_cafe(valor, decimales=2):
    """
    Formatea decimales para visualización en español:
    1234.56 -> 1.234,56
    """
    valor_truncado = truncar_decimal(valor, decimales)
    texto = f"{valor_truncado:,.{decimales}f}"

    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def sumar_meses(fecha_base, meses):
    """
    Suma meses a una fecha usando solo librería estándar.
    Si el día no existe en el mes destino, usa el último día disponible.
    """
    mes_total = fecha_base.month - 1 + meses
    anio = fecha_base.year + mes_total // 12
    mes = mes_total % 12 + 1
    dia = min(fecha_base.day, monthrange(anio, mes)[1])

    return date(anio, mes, dia)


def preparar_florecidas(florecidas):
    hoy = date.today()
    resultado = []

    for florecida in florecidas:
        fecha_inicio_cosecha = sumar_meses(florecida.fecha_florecida, 7)
        fecha_fin_cosecha = sumar_meses(florecida.fecha_florecida, 9)

        dias_faltantes = (fecha_inicio_cosecha - hoy).days

        if hoy < fecha_inicio_cosecha:
            estado = "Pendiente"
            badge = "bg-warning text-dark"
        elif fecha_inicio_cosecha <= hoy <= fecha_fin_cosecha:
            estado = "En ventana de cosecha"
            badge = "bg-success"
            dias_faltantes = 0
        else:
            estado = "Finalizada / revisar"
            badge = "bg-secondary"
            dias_faltantes = 0

        resultado.append({
            "florecida": florecida,
            "fecha_inicio_cosecha": fecha_inicio_cosecha,
            "fecha_fin_cosecha": fecha_fin_cosecha,
            "dias_faltantes": dias_faltantes,
            "estado": estado,
            "badge": badge
        })

    return resultado


def procesar_datos_produccion(produccion, finca_activa):
    fecha_texto = request.form.get("fecha")
    lote = request.form.get("lote", "").strip()
    tipo_cafe = request.form.get("tipo_cafe", "").strip()
    kilos_totales = convertir_decimal(request.form.get("kilos_totales"))
    observaciones = request.form.get("observaciones", "").strip() or None

    if not fecha_texto or not lote or not tipo_cafe:
        raise ValueError("Fecha, lote y tipo de café son obligatorios.")

    if tipo_cafe not in ["cerezo", "pergamino"]:
        raise ValueError("El tipo de café seleccionado no es válido.")

    if kilos_totales is None or kilos_totales <= 0:
        raise ValueError("La cantidad en kilogramos debe ser mayor a cero.")

    produccion.finca_id = finca_activa.id
    produccion.fecha = datetime.strptime(fecha_texto, "%Y-%m-%d").date()
    produccion.lote = lote
    produccion.tipo_cafe = tipo_cafe
    produccion.kilos_totales = kilos_totales
    produccion.observaciones = observaciones

    return produccion


@produccion_cafe_bp.route("/")
@login_required
def index():
    finca_activa = obtener_finca_activa()

    tipo_cafe = request.args.get("tipo_cafe", "")
    lote = request.args.get("lote", "").strip()
    fecha_inicio = request.args.get("fecha_inicio", "")
    fecha_fin = request.args.get("fecha_fin", "")

    producciones_query = (
        ProduccionCafe.query
        .filter_by(finca_id=finca_activa.id)
    )

    if tipo_cafe:
        producciones_query = producciones_query.filter(ProduccionCafe.tipo_cafe == tipo_cafe)

    if lote:
        producciones_query = producciones_query.filter(ProduccionCafe.lote.ilike(f"%{lote}%"))

    if fecha_inicio:
        fecha_inicio_obj = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        producciones_query = producciones_query.filter(ProduccionCafe.fecha >= fecha_inicio_obj)

    if fecha_fin:
        fecha_fin_obj = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        producciones_query = producciones_query.filter(ProduccionCafe.fecha <= fecha_fin_obj)

    total_cerezo = (
        producciones_query
        .with_entities(func.coalesce(func.sum(ProduccionCafe.kilos_totales), 0))
        .filter(ProduccionCafe.tipo_cafe == "cerezo")
        .scalar()
    )

    total_pergamino = (
        producciones_query
        .with_entities(func.coalesce(func.sum(ProduccionCafe.kilos_totales), 0))
        .filter(ProduccionCafe.tipo_cafe == "pergamino")
        .scalar()
    )

    resumen = conversion_cafe.resumen_cafe(total_cerezo, total_pergamino)

    producciones = (
        producciones_query
        .order_by(ProduccionCafe.fecha.desc(), ProduccionCafe.id.desc())
        .all()
    )

    florecidas = (
        FlorecidaCafe.query
        .filter_by(finca_id=finca_activa.id)
        .order_by(FlorecidaCafe.fecha_florecida.desc(), FlorecidaCafe.id.desc())
        .all()
    )

    florecidas_estimadas = preparar_florecidas(florecidas)

    filtros = {
        "tipo_cafe": tipo_cafe,
        "lote": lote,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin
    }

    return render_template(
        "produccion_cafe/index.html",
        finca_activa=finca_activa,
        producciones=producciones,
        florecidas_estimadas=florecidas_estimadas,
        resumen=resumen,
        filtros=filtros
    )


@produccion_cafe_bp.route("/nueva", methods=["GET", "POST"])
@login_required
def nueva_produccion():
    finca_activa = obtener_finca_activa()

    if request.method == "POST":
        try:
            produccion = ProduccionCafe()
            produccion = procesar_datos_produccion(produccion, finca_activa)

            db.session.add(produccion)
            db.session.commit()

            flash("Producción de café registrada correctamente.", "success")
            return redirect(url_for("produccion_cafe.index"))

        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
            return redirect(url_for("produccion_cafe.nueva_produccion"))

    return render_template(
        "produccion_cafe/formulario.html",
        finca_activa=finca_activa,
        produccion=None,
        accion="Registrar producción de café",
        hoy=date.today().isoformat()
    )


@produccion_cafe_bp.route("/<int:produccion_id>/editar", methods=["GET", "POST"])
@login_required
def editar_produccion(produccion_id):
    finca_activa = obtener_finca_activa()

    produccion = (
        ProduccionCafe.query
        .filter_by(id=produccion_id, finca_id=finca_activa.id)
        .first_or_404()
    )

    if request.method == "POST":
        try:
            produccion = procesar_datos_produccion(produccion, finca_activa)

            db.session.commit()

            flash("Producción de café actualizada correctamente.", "success")
            return redirect(url_for("produccion_cafe.index"))

        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
            return redirect(url_for("produccion_cafe.editar_produccion", produccion_id=produccion.id))

    return render_template(
        "produccion_cafe/formulario.html",
        finca_activa=finca_activa,
        produccion=produccion,
        accion="Editar producción de café",
        hoy=date.today().isoformat()
    )


@produccion_cafe_bp.route("/<int:produccion_id>/eliminar", methods=["POST"])
@login_required
def eliminar_produccion(produccion_id):
    finca_activa = obtener_finca_activa()

    produccion = (
        ProduccionCafe.query
        .filter_by(id=produccion_id, finca_id=finca_activa.id)
        .first_or_404()
    )

    db.session.delete(produccion)
    db.session.commit()

    flash("Producción de café eliminada correctamente.", "success")
    return redirect(url_for("produccion_cafe.index"))


@produccion_cafe_bp.route("/florecidas/nueva", methods=["GET", "POST"])
@login_required
def nueva_florecida():
    finca_activa = obtener_finca_activa()

    if request.method == "POST":
        fecha_texto = request.form.get("fecha_florecida")
        lote = request.form.get("lote", "").strip()
        observaciones = request.form.get("observaciones", "").strip() or None

        if not fecha_texto or not lote:
            flash("Fecha de florecida y lote son obligatorios.", "danger")
            return redirect(url_for("produccion_cafe.nueva_florecida"))

        florecida = FlorecidaCafe(
            finca_id=finca_activa.id,
            fecha_florecida=datetime.strptime(fecha_texto, "%Y-%m-%d").date(),
            lote=lote,
            observaciones=observaciones
        )

        db.session.add(florecida)
        db.session.commit()

        flash("Florecida registrada correctamente.", "success")
        return redirect(url_for("produccion_cafe.index"))

    return render_template(
        "produccion_cafe/florecida_formulario.html",
        finca_activa=finca_activa,
        florecida=None,
        accion="Registrar florecida",
        hoy=date.today().isoformat()
    )


@produccion_cafe_bp.route("/florecidas/<int:florecida_id>/editar", methods=["GET", "POST"])
@login_required
def editar_florecida(florecida_id):
    finca_activa = obtener_finca_activa()

    florecida = (
        FlorecidaCafe.query
        .filter_by(id=florecida_id, finca_id=finca_activa.id)
        .first_or_404()
    )

    if request.method == "POST":
        fecha_texto = request.form.get("fecha_florecida")
        lote = request.form.get("lote", "").strip()
        observaciones = request.form.get("observaciones", "").strip() or None

        if not fecha_texto or not lote:
            flash("Fecha de florecida y lote son obligatorios.", "danger")
            return redirect(url_for("produccion_cafe.editar_florecida", florecida_id=florecida.id))

        florecida.fecha_florecida = datetime.strptime(fecha_texto, "%Y-%m-%d").date()
        florecida.lote = lote
        florecida.observaciones = observaciones

        db.session.commit()

        flash("Florecida actualizada correctamente.", "success")
        return redirect(url_for("produccion_cafe.index"))

    return render_template(
        "produccion_cafe/florecida_formulario.html",
        finca_activa=finca_activa,
        florecida=florecida,
        accion="Editar florecida",
        hoy=date.today().isoformat()
    )


@produccion_cafe_bp.route("/florecidas/<int:florecida_id>/eliminar", methods=["POST"])
@login_required
def eliminar_florecida(florecida_id):
    finca_activa = obtener_finca_activa()

    florecida = (
        FlorecidaCafe.query
        .filter_by(id=florecida_id, finca_id=finca_activa.id)
        .first_or_404()
    )

    db.session.delete(florecida)
    db.session.commit()

    flash("Florecida eliminada correctamente.", "success")
    return redirect(url_for("produccion_cafe.index"))
