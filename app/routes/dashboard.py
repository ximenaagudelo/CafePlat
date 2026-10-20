from datetime import date
from decimal import Decimal

from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from sqlalchemy import func

from app.models import (
    Trabajador,
    RegistroTrabajo,
    ProduccionCafe,
    ProduccionPlatano,
    Gasto,
    Venta
)
from app.services import cafe as conversion_cafe
from app.services.alertas import proximas_cortadas, proximas_cosechas_cafe


dashboard_bp = Blueprint("dashboard", __name__)


def obtener_finca_activa():
    if not current_user.is_authenticated or not current_user.finca:
        abort(403)

    return current_user.finca


def decimal_seguro(valor):
    if valor is None:
        return Decimal("0")

    return Decimal(str(valor))


def sumar_decimal(query, columna):
    return decimal_seguro(
        query
        .with_entities(func.coalesce(func.sum(columna), 0))
        .scalar()
    )


def obtener_rango_mes_actual():
    hoy = date.today()
    inicio_mes = date(hoy.year, hoy.month, 1)

    if hoy.month == 12:
        inicio_mes_siguiente = date(hoy.year + 1, 1, 1)
    else:
        inicio_mes_siguiente = date(hoy.year, hoy.month + 1, 1)

    return hoy, inicio_mes, inicio_mes_siguiente


@dashboard_bp.route("/")
@login_required
def index():
    finca_activa = obtener_finca_activa()
    finca_id = finca_activa.id

    hoy, inicio_mes, inicio_mes_siguiente = obtener_rango_mes_actual()

    # =========================
    # Trabajadores / mano de obra
    # =========================
    total_trabajadores = (
        Trabajador.query
        .filter_by(finca_id=finca_id)
        .count()
    )

    registros_query = (
        RegistroTrabajo.query
        .filter_by(finca_id=finca_id)
    )

    total_trabajos_realizados = registros_query.count()

    trabajos_pendientes_pago = (
        RegistroTrabajo.query
        .filter_by(finca_id=finca_id, pagado=False)
        .count()
    )

    trabajos_pagados = (
        RegistroTrabajo.query
        .filter_by(finca_id=finca_id, pagado=True)
        .count()
    )

    total_pendiente = sumar_decimal(
        RegistroTrabajo.query.filter_by(finca_id=finca_id, pagado=False),
        RegistroTrabajo.total_pagar
    )

    total_pagado = sumar_decimal(
        RegistroTrabajo.query.filter_by(finca_id=finca_id, pagado=True),
        RegistroTrabajo.total_pagar
    )

    total_mano_obra = sumar_decimal(
        registros_query,
        RegistroTrabajo.total_pagar
    )

    total_kilos_cafe_trabajos = sumar_decimal(
        RegistroTrabajo.query.filter_by(
            finca_id=finca_id,
            tipo_trabajo="recoleccion_cafe"
        ),
        RegistroTrabajo.kilos_cafe
    )

    ultimos_trabajos = (
        RegistroTrabajo.query
        .filter_by(finca_id=finca_id)
        .order_by(RegistroTrabajo.fecha.desc(), RegistroTrabajo.id.desc())
        .limit(5)
        .all()
    )

    # =========================
    # Producción de café
    # =========================
    produccion_cafe_query = (
        ProduccionCafe.query
        .filter_by(finca_id=finca_id)
    )

    produccion_cafe_total = sumar_decimal(
        produccion_cafe_query,
        ProduccionCafe.kilos_totales
    )

    produccion_cafe_cerezo = sumar_decimal(
        ProduccionCafe.query.filter_by(
            finca_id=finca_id,
            tipo_cafe="cerezo"
        ),
        ProduccionCafe.kilos_totales
    )

    produccion_cafe_pergamino = sumar_decimal(
        ProduccionCafe.query.filter_by(
            finca_id=finca_id,
            tipo_cafe="pergamino"
        ),
        ProduccionCafe.kilos_totales
    )

    resumen_cafe = conversion_cafe.resumen_cafe(
        produccion_cafe_cerezo,
        produccion_cafe_pergamino
    )

    # =========================
    # Producción plátano / banano / comino
    # =========================
    produccion_platano_query = (
        ProduccionPlatano.query
        .filter_by(finca_id=finca_id)
    )

    produccion_platano_kilos = sumar_decimal(
        produccion_platano_query,
        ProduccionPlatano.kilos
    )

    produccion_platano_racimos = sumar_decimal(
        produccion_platano_query,
        ProduccionPlatano.racimos
    )

    produccion_solo_platano_kilos = sumar_decimal(
        ProduccionPlatano.query.filter_by(
            finca_id=finca_id,
            tipo_cultivo="platano"
        ),
        ProduccionPlatano.kilos
    )

    produccion_banano_kilos = sumar_decimal(
        ProduccionPlatano.query.filter_by(
            finca_id=finca_id,
            tipo_cultivo="banano"
        ),
        ProduccionPlatano.kilos
    )

    produccion_comino_kilos = sumar_decimal(
        ProduccionPlatano.query.filter_by(
            finca_id=finca_id,
            tipo_cultivo="comino"
        ),
        ProduccionPlatano.kilos
    )

    kg_promedio_racimo = (
        produccion_platano_kilos / produccion_platano_racimos
        if produccion_platano_racimos > 0
        else Decimal("0")
    )

    # =========================
    # Gastos e insumos
    # =========================
    gastos_query = (
        Gasto.query
        .filter_by(finca_id=finca_id)
    )

    total_gastos = sumar_decimal(
        gastos_query,
        Gasto.valor
    )

    gastos_mes = sumar_decimal(
        Gasto.query
        .filter_by(finca_id=finca_id)
        .filter(
            Gasto.fecha >= inicio_mes,
            Gasto.fecha < inicio_mes_siguiente
        ),
        Gasto.valor
    )

    total_insumos_agricolas = sumar_decimal(
        Gasto.query
        .filter_by(finca_id=finca_id)
        .filter(Gasto.tipo == "Insumo agrícola"),
        Gasto.valor
    )

    ultimos_gastos = (
        Gasto.query
        .filter_by(finca_id=finca_id)
        .order_by(Gasto.fecha.desc(), Gasto.id.desc())
        .limit(5)
        .all()
    )

    # =========================
    # Ventas
    # =========================
    ventas_query = (
        Venta.query
        .filter_by(finca_id=finca_id)
    )

    ventas_cafe_query = (
        Venta.query
        .filter_by(finca_id=finca_id, producto="cafe")
    )

    ventas_no_cafe_query = (
        Venta.query
        .filter_by(finca_id=finca_id)
        .filter(Venta.producto != "cafe")
    )

    total_ventas = sumar_decimal(
        ventas_query,
        Venta.valor_total
    )

    ventas_mes = sumar_decimal(
        Venta.query
        .filter_by(finca_id=finca_id)
        .filter(
            Venta.fecha >= inicio_mes,
            Venta.fecha < inicio_mes_siguiente
        ),
        Venta.valor_total
    )

    ventas_cafe = sumar_decimal(
        ventas_cafe_query,
        Venta.valor_total
    )

    # Conserva el nombre ventas_platano porque ya lo usa el HTML,
    # pero realmente representa plátano / banano / comino.
    ventas_platano = sumar_decimal(
        ventas_no_cafe_query,
        Venta.valor_total
    )

    kilos_cafe_vendidos = sumar_decimal(
        ventas_cafe_query,
        Venta.kilos
    )

    kilos_platano_vendidos = sumar_decimal(
        ventas_no_cafe_query,
        Venta.kilos
    )

    arrobas_cafe_vendidas = kilos_cafe_vendidos / conversion_cafe.KG_ARROBA_PERGAMINO

    ultimas_ventas = (
        Venta.query
        .filter_by(finca_id=finca_id)
        .order_by(Venta.fecha.desc(), Venta.id.desc())
        .limit(5)
        .all()
    )

    # =========================
    # Resumen financiero
    # =========================
    costos_registrados = total_gastos + total_mano_obra
    balance_estimado = total_ventas - costos_registrados

    return render_template(
        "dashboard/index.html",
        finca_activa=finca_activa,
        hoy=hoy,

        total_trabajadores=total_trabajadores,
        total_trabajos_realizados=total_trabajos_realizados,
        trabajos_pendientes_pago=trabajos_pendientes_pago,
        trabajos_pagados=trabajos_pagados,
        total_pendiente=total_pendiente,
        total_pagado=total_pagado,
        total_mano_obra=total_mano_obra,
        total_general=total_mano_obra,
        total_kilos_cafe=total_kilos_cafe_trabajos,
        ultimos_trabajos=ultimos_trabajos,

        produccion_cafe_total=produccion_cafe_total,
        produccion_cafe_cerezo=produccion_cafe_cerezo,
        produccion_cafe_pergamino=produccion_cafe_pergamino,
        resumen_cafe=resumen_cafe,
        cortadas=proximas_cortadas(finca_id, limite=4),
        cosechas_cafe=proximas_cosechas_cafe(finca_id),

        produccion_platano_kilos=produccion_platano_kilos,
        produccion_platano_racimos=produccion_platano_racimos,
        produccion_solo_platano_kilos=produccion_solo_platano_kilos,
        produccion_banano_kilos=produccion_banano_kilos,
        produccion_comino_kilos=produccion_comino_kilos,
        kg_promedio_racimo=kg_promedio_racimo,

        total_gastos=total_gastos,
        gastos_mes=gastos_mes,
        total_insumos_agricolas=total_insumos_agricolas,
        ultimos_gastos=ultimos_gastos,

        total_ventas=total_ventas,
        ventas_mes=ventas_mes,
        ventas_cafe=ventas_cafe,
        ventas_platano=ventas_platano,
        kilos_cafe_vendidos=kilos_cafe_vendidos,
        kilos_platano_vendidos=kilos_platano_vendidos,
        arrobas_cafe_vendidas=arrobas_cafe_vendidas,
        ultimas_ventas=ultimas_ventas,

        costos_registrados=costos_registrados,
        balance_estimado=balance_estimado
    )