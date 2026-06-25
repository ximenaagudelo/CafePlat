from datetime import date
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort
)
from flask_login import login_required, current_user
from sqlalchemy import func

from app.extensions import db
from app.models import Inventario, MovimientoInventario


inventario_bp = Blueprint(
    "inventario",
    __name__,
    url_prefix="/inventario"
)


def obtener_finca_activa():
    if not current_user.is_authenticated or not current_user.finca:
        abort(403)

    return current_user.finca


def decimal_form(valor, defecto="0"):
    if valor is None or str(valor).strip() == "":
        valor = defecto

    try:
        return Decimal(str(valor).replace(",", "."))
    except InvalidOperation:
        return Decimal(defecto)


def fecha_form(valor):
    if not valor:
        return date.today()

    try:
        return date.fromisoformat(valor)
    except ValueError:
        return date.today()


@inventario_bp.route("/")
@login_required
def index():
    finca_activa = obtener_finca_activa()

    categoria = request.args.get("categoria", "").strip()
    busqueda = request.args.get("busqueda", "").strip()

    query = Inventario.query.filter_by(finca_id=finca_activa.id)

    if categoria:
        query = query.filter(Inventario.categoria == categoria)

    if busqueda:
        query = query.filter(Inventario.nombre.ilike(f"%{busqueda}%"))

    items = (
        query
        .order_by(Inventario.categoria.asc(), Inventario.nombre.asc())
        .all()
    )

    categorias = [
        "Fertilizantes",
        "Químicos",
        "Herramientas",
        "Empaques",
        "Combustibles",
        "Insumos agrícolas",
        "Mantenimiento",
        "Otros"
    ]

    total_items = len(items)

    total_existencias = sum(
        decimal_form(item.cantidad_disponible)
        for item in items
    )

    valor_estimado_inventario = sum(
        item.valor_estimado
        for item in items
    )

    ultimos_movimientos = (
        MovimientoInventario.query
        .filter_by(finca_id=finca_activa.id)
        .order_by(
            MovimientoInventario.fecha.desc(),
            MovimientoInventario.id.desc()
        )
        .limit(8)
        .all()
    )

    return render_template(
        "inventario/index.html",
        finca_activa=finca_activa,
        items=items,
        categorias=categorias,
        categoria=categoria,
        busqueda=busqueda,
        total_items=total_items,
        total_existencias=total_existencias,
        valor_estimado_inventario=valor_estimado_inventario,
        ultimos_movimientos=ultimos_movimientos
    )


@inventario_bp.route("/crear", methods=["GET", "POST"])
@login_required
def crear():
    finca_activa = obtener_finca_activa()

    categorias = [
        "Fertilizantes",
        "Químicos",
        "Herramientas",
        "Empaques",
        "Combustibles",
        "Insumos agrícolas",
        "Mantenimiento",
        "Otros"
    ]

    unidades = [
        "kg",
        "litros",
        "unidades",
        "bultos",
        "galones",
        "metros",
        "paquetes",
        "cajas",
        "otro"
    ]

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        categoria = request.form.get("categoria", "").strip()
        unidad_medida = request.form.get("unidad_medida", "").strip()

        cantidad_inicial = decimal_form(
            request.form.get("cantidad_inicial")
        )

        costo_unitario = decimal_form(
            request.form.get("costo_unitario")
        )

        proveedor = request.form.get("proveedor", "").strip()
        ubicacion = request.form.get("ubicacion", "").strip()
        observaciones = request.form.get("observaciones", "").strip()

        if not nombre or not categoria or not unidad_medida:
            flash("Nombre, categoría y unidad de medida son obligatorios.", "warning")
            return redirect(url_for("inventario.crear"))

        if cantidad_inicial < 0:
            flash("La cantidad inicial no puede ser negativa.", "warning")
            return redirect(url_for("inventario.crear"))

        item = Inventario(
            finca_id=finca_activa.id,
            nombre=nombre,
            categoria=categoria,
            unidad_medida=unidad_medida,
            cantidad_disponible=cantidad_inicial,
            costo_unitario=costo_unitario,
            proveedor=proveedor or None,
            ubicacion=ubicacion or None,
            observaciones=observaciones or None
        )

        db.session.add(item)
        db.session.flush()

        if cantidad_inicial > 0:
            movimiento = MovimientoInventario(
                finca_id=finca_activa.id,
                inventario_id=item.id,
                fecha=date.today(),
                tipo_movimiento="entrada",
                cantidad=cantidad_inicial,
                costo_unitario=costo_unitario,
                proveedor=proveedor or None,
                motivo="Cantidad inicial",
                observaciones="Registro inicial del inventario"
            )

            db.session.add(movimiento)

        db.session.commit()

        flash("Elemento de inventario creado correctamente.", "success")
        return redirect(url_for("inventario.index"))

    return render_template(
        "inventario/formulario.html",
        item=None,
        categorias=categorias,
        unidades=unidades,
        modo="crear"
    )


@inventario_bp.route("/<int:item_id>/editar", methods=["GET", "POST"])
@login_required
def editar(item_id):
    finca_activa = obtener_finca_activa()

    item = (
        Inventario.query
        .filter_by(id=item_id, finca_id=finca_activa.id)
        .first_or_404()
    )

    categorias = [
        "Fertilizantes",
        "Químicos",
        "Herramientas",
        "Empaques",
        "Combustibles",
        "Insumos agrícolas",
        "Mantenimiento",
        "Otros"
    ]

    unidades = [
        "kg",
        "litros",
        "unidades",
        "bultos",
        "galones",
        "metros",
        "paquetes",
        "cajas",
        "otro"
    ]

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        categoria = request.form.get("categoria", "").strip()
        unidad_medida = request.form.get("unidad_medida", "").strip()

        costo_unitario = decimal_form(
            request.form.get("costo_unitario")
        )

        proveedor = request.form.get("proveedor", "").strip()
        ubicacion = request.form.get("ubicacion", "").strip()
        observaciones = request.form.get("observaciones", "").strip()

        if not nombre or not categoria or not unidad_medida:
            flash("Nombre, categoría y unidad de medida son obligatorios.", "warning")
            return redirect(url_for("inventario.editar", item_id=item.id))

        item.nombre = nombre
        item.categoria = categoria
        item.unidad_medida = unidad_medida
        item.costo_unitario = costo_unitario
        item.proveedor = proveedor or None
        item.ubicacion = ubicacion or None
        item.observaciones = observaciones or None

        db.session.commit()

        flash("Elemento de inventario actualizado correctamente.", "success")
        return redirect(url_for("inventario.index"))

    return render_template(
        "inventario/formulario.html",
        item=item,
        categorias=categorias,
        unidades=unidades,
        modo="editar"
    )


@inventario_bp.route("/<int:item_id>/movimiento", methods=["GET", "POST"])
@login_required
def movimiento(item_id):
    finca_activa = obtener_finca_activa()

    item = (
        Inventario.query
        .filter_by(id=item_id, finca_id=finca_activa.id)
        .first_or_404()
    )

    if request.method == "POST":
        fecha = fecha_form(request.form.get("fecha"))
        tipo_movimiento = request.form.get("tipo_movimiento", "").strip()
        cantidad = decimal_form(request.form.get("cantidad"))
        costo_unitario = decimal_form(
            request.form.get("costo_unitario"),
            defecto=str(item.costo_unitario or 0)
        )
        proveedor = request.form.get("proveedor", "").strip()
        motivo = request.form.get("motivo", "").strip()
        observaciones = request.form.get("observaciones", "").strip()

        if tipo_movimiento not in ["entrada", "salida", "ajuste"]:
            flash("Tipo de movimiento inválido.", "warning")
            return redirect(url_for("inventario.movimiento", item_id=item.id))

        if cantidad < 0:
            flash("La cantidad no puede ser negativa.", "warning")
            return redirect(url_for("inventario.movimiento", item_id=item.id))

        cantidad_actual = decimal_form(item.cantidad_disponible)

        if tipo_movimiento == "entrada":
            item.cantidad_disponible = cantidad_actual + cantidad

        elif tipo_movimiento == "salida":
            if cantidad > cantidad_actual:
                flash("No hay existencias suficientes para registrar esta salida.", "danger")
                return redirect(url_for("inventario.movimiento", item_id=item.id))

            item.cantidad_disponible = cantidad_actual - cantidad

        elif tipo_movimiento == "ajuste":
            item.cantidad_disponible = cantidad

        if costo_unitario >= 0:
            item.costo_unitario = costo_unitario

        movimiento = MovimientoInventario(
            finca_id=finca_activa.id,
            inventario_id=item.id,
            fecha=fecha,
            tipo_movimiento=tipo_movimiento,
            cantidad=cantidad,
            costo_unitario=costo_unitario,
            proveedor=proveedor or None,
            motivo=motivo or None,
            observaciones=observaciones or None
        )

        db.session.add(movimiento)
        db.session.commit()

        flash("Movimiento registrado correctamente.", "success")
        return redirect(url_for("inventario.index"))

    return render_template(
        "inventario/movimiento_formulario.html",
        item=item,
        hoy=date.today()
    )


@inventario_bp.route("/<int:item_id>/eliminar", methods=["POST"])
@login_required
def eliminar(item_id):
    finca_activa = obtener_finca_activa()

    item = (
        Inventario.query
        .filter_by(id=item_id, finca_id=finca_activa.id)
        .first_or_404()
    )

    db.session.delete(item)
    db.session.commit()

    flash("Elemento de inventario eliminado correctamente.", "success")
    return redirect(url_for("inventario.index"))