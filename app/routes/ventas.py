from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Venta
from app.services.cafe import KG_ARROBA_PERGAMINO


ventas_bp = Blueprint(
    "ventas",
    __name__,
    url_prefix="/ventas"
)


PRODUCTOS = [
    ("cafe", "Café"),
    ("platano", "Plátano / Banano / Comino")
]


TIPOS_CAFE = [
    "Seco",
    "Mojado",
    "Pasilla"
]


TIPOS_PLATANO = [
    "Plátano",
    "Banano",
    "Comino"
]


def convertir_fecha(valor):
    if not valor:
        return None

    try:
        return date.fromisoformat(valor)
    except ValueError:
        return None


def convertir_decimal(valor):
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


def convertir_entero(valor):
    if not valor:
        return None

    try:
        return int(valor)
    except ValueError:
        return None


def obtener_venta_finca(venta_id):
    return Venta.query.filter_by(
        id=venta_id,
        finca_id=current_user.finca_id
    ).first_or_404()


def validar_venta(producto, tipo_producto, kilos, racimos, precio_unitario, valor_total):
    if producto not in ["cafe", "platano"]:
        return "Debes seleccionar un producto válido."

    if producto == "cafe" and tipo_producto not in TIPOS_CAFE:
        return "Debes seleccionar un tipo de café válido."

    if producto == "platano" and tipo_producto not in TIPOS_PLATANO:
        return "Debes seleccionar Plátano, Banano o Comino."

    if kilos is None or kilos <= 0:
        return "Debes ingresar kilos válidos mayores a cero."

    if producto == "platano" and (racimos is None or racimos <= 0):
        return "Debes ingresar la cantidad de racimos vendidos."

    if precio_unitario is None or precio_unitario <= 0:
        return "Debes ingresar un precio unitario válido."

    if valor_total is None or valor_total <= 0:
        return "Debes ingresar el valor total recibido."

    return None


@ventas_bp.route("/")
@login_required
def index():
    producto = request.args.get("producto", "").strip()
    tipo_producto = request.args.get("tipo_producto", "").strip()
    fecha_inicio_texto = request.args.get("fecha_inicio", "").strip()
    fecha_fin_texto = request.args.get("fecha_fin", "").strip()

    consulta = Venta.query.filter_by(
        finca_id=current_user.finca_id
    )

    if producto:
        consulta = consulta.filter(Venta.producto == producto)

    if tipo_producto:
        consulta = consulta.filter(Venta.tipo_producto == tipo_producto)

    fecha_inicio = convertir_fecha(fecha_inicio_texto)
    fecha_fin = convertir_fecha(fecha_fin_texto)

    if fecha_inicio:
        consulta = consulta.filter(Venta.fecha >= fecha_inicio)

    if fecha_fin:
        consulta = consulta.filter(Venta.fecha <= fecha_fin)

    ventas = consulta.order_by(
        Venta.fecha.desc(),
        Venta.id.desc()
    ).all()

    total_ventas = sum(
        venta.valor_total or Decimal("0")
        for venta in ventas
    )

    total_cafe = sum(
        venta.valor_total or Decimal("0")
        for venta in ventas
        if venta.producto == "cafe"
    )

    total_platano = sum(
        venta.valor_total or Decimal("0")
        for venta in ventas
        if venta.producto == "platano"
    )

    kilos_cafe = sum(
        venta.kilos or Decimal("0")
        for venta in ventas
        if venta.producto == "cafe"
    )

    arrobas_cafe = kilos_cafe / KG_ARROBA_PERGAMINO if kilos_cafe else Decimal("0")

    kilos_platano = sum(
        venta.kilos or Decimal("0")
        for venta in ventas
        if venta.producto == "platano"
    )

    racimos_platano = sum(
        venta.racimos or 0
        for venta in ventas
        if venta.producto == "platano"
    )

    filtros = {
        "producto": producto,
        "tipo_producto": tipo_producto,
        "fecha_inicio": fecha_inicio_texto,
        "fecha_fin": fecha_fin_texto
    }

    return render_template(
        "ventas/index.html",
        ventas=ventas,
        productos=PRODUCTOS,
        tipos_cafe=TIPOS_CAFE,
        tipos_platano=TIPOS_PLATANO,
        filtros=filtros,
        total_ventas=total_ventas,
        total_cafe=total_cafe,
        total_platano=total_platano,
        kilos_cafe=kilos_cafe,
        arrobas_cafe=arrobas_cafe,
        kilos_platano=kilos_platano,
        racimos_platano=racimos_platano,
        total_registros=len(ventas)
    )


@ventas_bp.route("/nueva", methods=["GET", "POST"])
@login_required
def nueva():
    if request.method == "POST":
        fecha = convertir_fecha(request.form.get("fecha"))
        producto = request.form.get("producto", "").strip()
        tipo_producto = request.form.get("tipo_producto", "").strip()
        kilos = convertir_decimal(request.form.get("kilos"))
        racimos = convertir_entero(request.form.get("racimos"))
        precio_unitario = convertir_decimal(request.form.get("precio_unitario"))
        valor_total = convertir_decimal(request.form.get("valor_total"))
        observaciones = request.form.get("observaciones", "").strip()

        if not fecha:
            flash("Debes ingresar una fecha válida.", "warning")
            return redirect(url_for("ventas.nueva"))

        error = validar_venta(
            producto,
            tipo_producto,
            kilos,
            racimos,
            precio_unitario,
            valor_total
        )

        if error:
            flash(error, "warning")
            return redirect(url_for("ventas.nueva"))

        venta = Venta(
            finca_id=current_user.finca_id,
            fecha=fecha,
            producto=producto,
            tipo_producto=tipo_producto,
            kilos=kilos,
            racimos=racimos if producto == "platano" else None,
            precio_unitario=precio_unitario,
            valor_total=valor_total,
            observaciones=observaciones or None
        )

        db.session.add(venta)
        db.session.commit()

        flash("Venta registrada correctamente.", "success")
        return redirect(url_for("ventas.index"))

    return render_template(
        "ventas/formulario.html",
        venta=None,
        productos=PRODUCTOS,
        tipos_cafe=TIPOS_CAFE,
        tipos_platano=TIPOS_PLATANO,
        fecha_hoy=date.today().isoformat(),
        titulo="Nueva venta",
        texto_boton="Guardar venta"
    )


@ventas_bp.route("/<int:venta_id>/editar", methods=["GET", "POST"])
@login_required
def editar(venta_id):
    venta = obtener_venta_finca(venta_id)

    if request.method == "POST":
        fecha = convertir_fecha(request.form.get("fecha"))
        producto = request.form.get("producto", "").strip()
        tipo_producto = request.form.get("tipo_producto", "").strip()
        kilos = convertir_decimal(request.form.get("kilos"))
        racimos = convertir_entero(request.form.get("racimos"))
        precio_unitario = convertir_decimal(request.form.get("precio_unitario"))
        valor_total = convertir_decimal(request.form.get("valor_total"))
        observaciones = request.form.get("observaciones", "").strip()

        if not fecha:
            flash("Debes ingresar una fecha válida.", "warning")
            return redirect(url_for("ventas.editar", venta_id=venta.id))

        error = validar_venta(
            producto,
            tipo_producto,
            kilos,
            racimos,
            precio_unitario,
            valor_total
        )

        if error:
            flash(error, "warning")
            return redirect(url_for("ventas.editar", venta_id=venta.id))

        venta.fecha = fecha
        venta.producto = producto
        venta.tipo_producto = tipo_producto
        venta.kilos = kilos
        venta.racimos = racimos if producto == "platano" else None
        venta.precio_unitario = precio_unitario
        venta.valor_total = valor_total
        venta.observaciones = observaciones or None

        db.session.commit()

        flash("Venta actualizada correctamente.", "success")
        return redirect(url_for("ventas.index"))

    return render_template(
        "ventas/formulario.html",
        venta=venta,
        productos=PRODUCTOS,
        tipos_cafe=TIPOS_CAFE,
        tipos_platano=TIPOS_PLATANO,
        fecha_hoy=date.today().isoformat(),
        titulo="Editar venta",
        texto_boton="Actualizar venta"
    )


@ventas_bp.route("/<int:venta_id>/eliminar", methods=["POST"])
@login_required
def eliminar(venta_id):
    venta = obtener_venta_finca(venta_id)

    db.session.delete(venta)
    db.session.commit()

    flash("Venta eliminada correctamente.", "success")
    return redirect(url_for("ventas.index"))