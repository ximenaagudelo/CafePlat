from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Gasto


gastos_bp = Blueprint(
    "gastos",
    __name__,
    url_prefix="/gastos"
)


CATEGORIAS_GASTO = [
    "Mano de obra",
    "Fertilizantes",
    "Insumos agrícolas",
    "Herramientas",
    "Transporte",
    "Mantenimiento",
    "Servicios",
    "Alimentación",
    "Combustible",
    "Otros"
]


TIPOS_GASTO = [
    "Gasto operativo",
    "Insumo agrícola",
    "Herramienta / equipo",
    "Servicio",
    "Otro"
]


METODOS_PAGO = [
    "Efectivo",
    "Transferencia",
    "Nequi",
    "Daviplata",
    "Tarjeta",
    "Crédito",
    "Otro"
]


def convertir_fecha(valor):
    if not valor:
        return None

    try:
        return date.fromisoformat(valor)
    except ValueError:
        return None


def convertir_valor(valor):
    if not valor:
        return None

    try:
        valor_limpio = (
            valor.replace("$", "")
            .replace(".", "")
            .replace(",", ".")
            .strip()
        )
        return Decimal(valor_limpio)
    except (InvalidOperation, AttributeError):
        return None


def obtener_gasto_finca(gasto_id):
    return Gasto.query.filter_by(
        id=gasto_id,
        finca_id=current_user.finca_id
    ).first_or_404()


@gastos_bp.route("/")
@login_required
def index():
    categoria = request.args.get("categoria", "").strip()
    tipo = request.args.get("tipo", "").strip()
    fecha_inicio_texto = request.args.get("fecha_inicio", "").strip()
    fecha_fin_texto = request.args.get("fecha_fin", "").strip()

    consulta = Gasto.query.filter_by(
        finca_id=current_user.finca_id
    )

    if categoria:
        consulta = consulta.filter(Gasto.categoria == categoria)

    if tipo:
        consulta = consulta.filter(Gasto.tipo == tipo)

    fecha_inicio = convertir_fecha(fecha_inicio_texto)
    fecha_fin = convertir_fecha(fecha_fin_texto)

    if fecha_inicio:
        consulta = consulta.filter(Gasto.fecha >= fecha_inicio)

    if fecha_fin:
        consulta = consulta.filter(Gasto.fecha <= fecha_fin)

    gastos = consulta.order_by(
        Gasto.fecha.desc(),
        Gasto.id.desc()
    ).all()

    total_general = sum(
        gasto.valor or Decimal("0")
        for gasto in gastos
    )

    total_insumos = sum(
        gasto.valor or Decimal("0")
        for gasto in gastos
        if gasto.tipo == "Insumo agrícola"
    )

    total_mano_obra = sum(
        gasto.valor or Decimal("0")
        for gasto in gastos
        if gasto.categoria == "Mano de obra"
    )

    filtros = {
        "categoria": categoria,
        "tipo": tipo,
        "fecha_inicio": fecha_inicio_texto,
        "fecha_fin": fecha_fin_texto
    }

    return render_template(
        "gastos/index.html",
        gastos=gastos,
        categorias=CATEGORIAS_GASTO,
        tipos=TIPOS_GASTO,
        filtros=filtros,
        total_general=total_general,
        total_insumos=total_insumos,
        total_mano_obra=total_mano_obra,
        total_registros=len(gastos)
    )


@gastos_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
def nuevo():
    if request.method == "POST":
        fecha = convertir_fecha(request.form.get("fecha"))
        categoria = request.form.get("categoria", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        proveedor = request.form.get("proveedor", "").strip()
        valor = convertir_valor(request.form.get("valor"))
        metodo_pago = request.form.get("metodo_pago", "").strip()
        tipo = request.form.get("tipo", "").strip()
        observaciones = request.form.get("observaciones", "").strip()

        if not fecha:
            flash("Debes ingresar una fecha válida.", "warning")
            return redirect(url_for("gastos.nuevo"))

        if not categoria:
            flash("Debes seleccionar una categoría.", "warning")
            return redirect(url_for("gastos.nuevo"))

        if not descripcion:
            flash("Debes ingresar una descripción.", "warning")
            return redirect(url_for("gastos.nuevo"))

        if valor is None or valor <= 0:
            flash("Debes ingresar un valor válido mayor a cero.", "warning")
            return redirect(url_for("gastos.nuevo"))

        if not tipo:
            flash("Debes seleccionar el tipo de gasto o insumo.", "warning")
            return redirect(url_for("gastos.nuevo"))

        gasto = Gasto(
            finca_id=current_user.finca_id,
            fecha=fecha,
            categoria=categoria,
            descripcion=descripcion,
            proveedor=proveedor or None,
            valor=valor,
            metodo_pago=metodo_pago or None,
            tipo=tipo,
            observaciones=observaciones or None
        )

        db.session.add(gasto)
        db.session.commit()

        flash("Gasto registrado correctamente.", "success")
        return redirect(url_for("gastos.index"))

    return render_template(
        "gastos/formulario.html",
        gasto=None,
        categorias=CATEGORIAS_GASTO,
        tipos=TIPOS_GASTO,
        metodos_pago=METODOS_PAGO,
        fecha_hoy=date.today().isoformat(),
        titulo="Nuevo gasto o insumo",
        texto_boton="Guardar registro"
    )


@gastos_bp.route("/<int:gasto_id>/editar", methods=["GET", "POST"])
@login_required
def editar(gasto_id):
    gasto = obtener_gasto_finca(gasto_id)

    if request.method == "POST":
        fecha = convertir_fecha(request.form.get("fecha"))
        categoria = request.form.get("categoria", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        proveedor = request.form.get("proveedor", "").strip()
        valor = convertir_valor(request.form.get("valor"))
        metodo_pago = request.form.get("metodo_pago", "").strip()
        tipo = request.form.get("tipo", "").strip()
        observaciones = request.form.get("observaciones", "").strip()

        if not fecha:
            flash("Debes ingresar una fecha válida.", "warning")
            return redirect(url_for("gastos.editar", gasto_id=gasto.id))

        if not categoria:
            flash("Debes seleccionar una categoría.", "warning")
            return redirect(url_for("gastos.editar", gasto_id=gasto.id))

        if not descripcion:
            flash("Debes ingresar una descripción.", "warning")
            return redirect(url_for("gastos.editar", gasto_id=gasto.id))

        if valor is None or valor <= 0:
            flash("Debes ingresar un valor válido mayor a cero.", "warning")
            return redirect(url_for("gastos.editar", gasto_id=gasto.id))

        if not tipo:
            flash("Debes seleccionar el tipo de gasto o insumo.", "warning")
            return redirect(url_for("gastos.editar", gasto_id=gasto.id))

        gasto.fecha = fecha
        gasto.categoria = categoria
        gasto.descripcion = descripcion
        gasto.proveedor = proveedor or None
        gasto.valor = valor
        gasto.metodo_pago = metodo_pago or None
        gasto.tipo = tipo
        gasto.observaciones = observaciones or None

        db.session.commit()

        flash("Gasto actualizado correctamente.", "success")
        return redirect(url_for("gastos.index"))

    return render_template(
        "gastos/formulario.html",
        gasto=gasto,
        categorias=CATEGORIAS_GASTO,
        tipos=TIPOS_GASTO,
        metodos_pago=METODOS_PAGO,
        fecha_hoy=date.today().isoformat(),
        titulo="Editar gasto o insumo",
        texto_boton="Actualizar registro"
    )


@gastos_bp.route("/<int:gasto_id>/eliminar", methods=["POST"])
@login_required
def eliminar(gasto_id):
    gasto = obtener_gasto_finca(gasto_id)

    db.session.delete(gasto)
    db.session.commit()

    flash("Gasto eliminado correctamente.", "success")
    return redirect(url_for("gastos.index"))