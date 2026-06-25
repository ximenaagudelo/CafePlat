from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_DOWN

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import func

from app.extensions import db
from app.models import ProduccionPlatano, EmbolsadoPlatano


produccion_platano_bp = Blueprint(
    "produccion_platano",
    __name__,
    url_prefix="/produccion-platano"
)


TIPOS_CULTIVO = {
    "platano": "Plátano",
    "banano": "Banano",
    "comino": "Comino",
    "otro": "Otro"
}


def obtener_finca_activa():
    """
    Obtiene la finca asociada al usuario autenticado.

    CampoSuite es multi-finca. Por eso toda consulta del módulo de plátano
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


def convertir_entero(valor, mensaje_error):
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise ValueError(mensaje_error)

    if numero <= 0:
        raise ValueError(mensaje_error)

    return numero


def truncar_decimal(valor, decimales=2):
    """
    Trunca decimales sin redondear.
    """
    if valor is None:
        valor = Decimal("0")

    valor = Decimal(valor)
    cuantizador = Decimal("1").scaleb(-decimales)

    return valor.quantize(cuantizador, rounding=ROUND_DOWN)


@produccion_platano_bp.app_template_filter("decimal_platano")
def decimal_platano(valor, decimales=2):
    """
    Formatea decimales para visualización en español:
    1234.56 -> 1.234,56
    """
    valor_truncado = truncar_decimal(valor, decimales)
    texto = f"{valor_truncado:,.{decimales}f}"

    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


@produccion_platano_bp.app_template_filter("entero_platano")
def entero_platano(valor):
    if valor is None:
        valor = 0

    texto = f"{int(valor):,}"
    return texto.replace(",", ".")


def etiqueta_tipo_cultivo(tipo_cultivo):
    return TIPOS_CULTIVO.get(tipo_cultivo, "Otro")


def preparar_embolsados(embolsados):
    hoy = date.today()
    resultado = []

    for embolsado in embolsados:
        fecha_corte = embolsado.fecha_estimada_corte
        dias_faltantes = embolsado.dias_faltantes_corte

        if fecha_corte and hoy < fecha_corte:
            estado = "Pendiente"
            badge = "bg-warning text-dark"
        elif fecha_corte and hoy == fecha_corte:
            estado = "Lista para corte"
            badge = "bg-success"
        else:
            estado = "Revisar corte"
            badge = "bg-secondary"

        resultado.append({
            "embolsado": embolsado,
            "fecha_corte": fecha_corte,
            "dias_faltantes": dias_faltantes,
            "estado": estado,
            "badge": badge
        })

    return resultado


def procesar_datos_produccion(produccion, finca_activa):
    fecha_texto = request.form.get("fecha")
    lote = request.form.get("lote", "").strip()
    tipo_cultivo = request.form.get("tipo_cultivo", "").strip()
    racimos = convertir_entero(
        request.form.get("racimos"),
        "La cantidad de racimos debe ser mayor a cero."
    )
    kilos = convertir_decimal(request.form.get("kilos"))
    observaciones = request.form.get("observaciones", "").strip() or None

    if not fecha_texto or not lote or not tipo_cultivo:
        raise ValueError("Fecha, lote y tipo de cultivo son obligatorios.")

    if tipo_cultivo not in TIPOS_CULTIVO:
        raise ValueError("El tipo de cultivo seleccionado no es válido.")

    if kilos is None or kilos <= 0:
        raise ValueError("El equivalente en kilogramos debe ser mayor a cero.")

    produccion.finca_id = finca_activa.id
    produccion.fecha = datetime.strptime(fecha_texto, "%Y-%m-%d").date()
    produccion.lote = lote
    produccion.tipo_cultivo = tipo_cultivo
    produccion.racimos = racimos
    produccion.kilos = kilos
    produccion.observaciones = observaciones

    return produccion


def procesar_datos_embolsado(embolsado, finca_activa):
    fecha_texto = request.form.get("fecha_embolsado")
    lote = request.form.get("lote", "").strip()
    tipo_cultivo = request.form.get("tipo_cultivo", "").strip()
    racimos_embolsados = convertir_entero(
        request.form.get("racimos_embolsados"),
        "La cantidad de racimos embolsados debe ser mayor a cero."
    )
    ciclo_estimado_dias = convertir_entero(
        request.form.get("ciclo_estimado_dias", "90"),
        "El ciclo estimado debe ser mayor a cero."
    )
    observaciones = request.form.get("observaciones", "").strip() or None

    if not fecha_texto or not lote or not tipo_cultivo:
        raise ValueError("Fecha de embolsado, lote y tipo de cultivo son obligatorios.")

    if tipo_cultivo not in TIPOS_CULTIVO:
        raise ValueError("El tipo de cultivo seleccionado no es válido.")

    embolsado.finca_id = finca_activa.id
    embolsado.fecha_embolsado = datetime.strptime(fecha_texto, "%Y-%m-%d").date()
    embolsado.lote = lote
    embolsado.tipo_cultivo = tipo_cultivo
    embolsado.racimos_embolsados = racimos_embolsados
    embolsado.ciclo_estimado_dias = ciclo_estimado_dias
    embolsado.observaciones = observaciones

    return embolsado


@produccion_platano_bp.route("/")
@login_required
def index():
    finca_activa = obtener_finca_activa()

    tipo_cultivo = request.args.get("tipo_cultivo", "")
    lote = request.args.get("lote", "").strip()
    fecha_inicio = request.args.get("fecha_inicio", "")
    fecha_fin = request.args.get("fecha_fin", "")

    producciones_query = (
        ProduccionPlatano.query
        .filter_by(finca_id=finca_activa.id)
    )

    if tipo_cultivo:
        producciones_query = producciones_query.filter(
            ProduccionPlatano.tipo_cultivo == tipo_cultivo
        )

    if lote:
        producciones_query = producciones_query.filter(
            ProduccionPlatano.lote.ilike(f"%{lote}%")
        )

    if fecha_inicio:
        fecha_inicio_obj = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        producciones_query = producciones_query.filter(
            ProduccionPlatano.fecha >= fecha_inicio_obj
        )

    if fecha_fin:
        fecha_fin_obj = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        producciones_query = producciones_query.filter(
            ProduccionPlatano.fecha <= fecha_fin_obj
        )

    total_racimos = (
        producciones_query
        .with_entities(func.coalesce(func.sum(ProduccionPlatano.racimos), 0))
        .scalar()
    )

    total_kilos = (
        producciones_query
        .with_entities(func.coalesce(func.sum(ProduccionPlatano.kilos), 0))
        .scalar()
    )

    total_producciones = producciones_query.count()

    total_embolsados = (
        EmbolsadoPlatano.query
        .filter_by(finca_id=finca_activa.id)
        .with_entities(func.coalesce(func.sum(EmbolsadoPlatano.racimos_embolsados), 0))
        .scalar()
    )

    kilos_por_racimo_promedio = Decimal("0")

    if total_racimos and total_racimos > 0:
        kilos_por_racimo_promedio = Decimal(total_kilos or 0) / Decimal(total_racimos)

    producciones = (
        producciones_query
        .order_by(ProduccionPlatano.fecha.desc(), ProduccionPlatano.id.desc())
        .all()
    )

    embolsados = (
        EmbolsadoPlatano.query
        .filter_by(finca_id=finca_activa.id)
        .order_by(EmbolsadoPlatano.fecha_embolsado.desc(), EmbolsadoPlatano.id.desc())
        .all()
    )

    embolsados_estimados = preparar_embolsados(embolsados)

    filtros = {
        "tipo_cultivo": tipo_cultivo,
        "lote": lote,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin
    }

    return render_template(
        "produccion_platano/index.html",
        finca_activa=finca_activa,
        producciones=producciones,
        embolsados_estimados=embolsados_estimados,
        total_racimos=total_racimos,
        total_kilos=total_kilos,
        total_producciones=total_producciones,
        total_embolsados=total_embolsados,
        kilos_por_racimo_promedio=kilos_por_racimo_promedio,
        filtros=filtros,
        tipos_cultivo=TIPOS_CULTIVO,
        etiqueta_tipo_cultivo=etiqueta_tipo_cultivo
    )


@produccion_platano_bp.route("/nueva", methods=["GET", "POST"])
@login_required
def nueva_produccion():
    finca_activa = obtener_finca_activa()

    if request.method == "POST":
        try:
            produccion = ProduccionPlatano()
            produccion = procesar_datos_produccion(produccion, finca_activa)

            db.session.add(produccion)
            db.session.commit()

            flash("Producción registrada correctamente.", "success")
            return redirect(url_for("produccion_platano.index"))

        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
            return redirect(url_for("produccion_platano.nueva_produccion"))

    return render_template(
        "produccion_platano/formulario.html",
        finca_activa=finca_activa,
        produccion=None,
        accion="Registrar producción",
        hoy=date.today().isoformat(),
        tipos_cultivo=TIPOS_CULTIVO
    )


@produccion_platano_bp.route("/<int:produccion_id>/editar", methods=["GET", "POST"])
@login_required
def editar_produccion(produccion_id):
    finca_activa = obtener_finca_activa()

    produccion = (
        ProduccionPlatano.query
        .filter_by(id=produccion_id, finca_id=finca_activa.id)
        .first_or_404()
    )

    if request.method == "POST":
        try:
            produccion = procesar_datos_produccion(produccion, finca_activa)

            db.session.commit()

            flash("Producción actualizada correctamente.", "success")
            return redirect(url_for("produccion_platano.index"))

        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
            return redirect(url_for("produccion_platano.editar_produccion", produccion_id=produccion.id))

    return render_template(
        "produccion_platano/formulario.html",
        finca_activa=finca_activa,
        produccion=produccion,
        accion="Editar producción",
        hoy=date.today().isoformat(),
        tipos_cultivo=TIPOS_CULTIVO
    )


@produccion_platano_bp.route("/<int:produccion_id>/eliminar", methods=["POST"])
@login_required
def eliminar_produccion(produccion_id):
    finca_activa = obtener_finca_activa()

    produccion = (
        ProduccionPlatano.query
        .filter_by(id=produccion_id, finca_id=finca_activa.id)
        .first_or_404()
    )

    db.session.delete(produccion)
    db.session.commit()

    flash("Producción eliminada correctamente.", "success")
    return redirect(url_for("produccion_platano.index"))


@produccion_platano_bp.route("/embolsados/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_embolsado():
    finca_activa = obtener_finca_activa()

    if request.method == "POST":
        try:
            embolsado = EmbolsadoPlatano()
            embolsado = procesar_datos_embolsado(embolsado, finca_activa)

            db.session.add(embolsado)
            db.session.commit()

            flash("Embolsado registrado correctamente.", "success")
            return redirect(url_for("produccion_platano.index"))

        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
            return redirect(url_for("produccion_platano.nuevo_embolsado"))

    return render_template(
        "produccion_platano/embolsado_formulario.html",
        finca_activa=finca_activa,
        embolsado=None,
        accion="Registrar embolsado",
        hoy=date.today().isoformat(),
        tipos_cultivo=TIPOS_CULTIVO
    )


@produccion_platano_bp.route("/embolsados/<int:embolsado_id>/editar", methods=["GET", "POST"])
@login_required
def editar_embolsado(embolsado_id):
    finca_activa = obtener_finca_activa()

    embolsado = (
        EmbolsadoPlatano.query
        .filter_by(id=embolsado_id, finca_id=finca_activa.id)
        .first_or_404()
    )

    if request.method == "POST":
        try:
            embolsado = procesar_datos_embolsado(embolsado, finca_activa)

            db.session.commit()

            flash("Embolsado actualizado correctamente.", "success")
            return redirect(url_for("produccion_platano.index"))

        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
            return redirect(url_for("produccion_platano.editar_embolsado", embolsado_id=embolsado.id))

    return render_template(
        "produccion_platano/embolsado_formulario.html",
        finca_activa=finca_activa,
        embolsado=embolsado,
        accion="Editar embolsado",
        hoy=date.today().isoformat(),
        tipos_cultivo=TIPOS_CULTIVO
    )


@produccion_platano_bp.route("/embolsados/<int:embolsado_id>/eliminar", methods=["POST"])
@login_required
def eliminar_embolsado(embolsado_id):
    finca_activa = obtener_finca_activa()

    embolsado = (
        EmbolsadoPlatano.query
        .filter_by(id=embolsado_id, finca_id=finca_activa.id)
        .first_or_404()
    )

    db.session.delete(embolsado)
    db.session.commit()

    flash("Embolsado eliminado correctamente.", "success")
    return redirect(url_for("produccion_platano.index"))
