"""
Alertas de la finca: próxima cortada de plátano y próxima cosecha de café.
"""
from datetime import date, timedelta

from app.models import EmbolsadoPlatano, FlorecidaCafe


# Racimos que pasaron su fecha estimada hace pocos días siguen
# mostrándose como "listos para cortar".
DIAS_GRACIA_CORTE = 15


def proximas_cortadas(finca_id, limite=5):
    """Embolsados cuya fecha estimada de corte es próxima o acaba de pasar."""
    hoy = date.today()
    desde = hoy - timedelta(days=DIAS_GRACIA_CORTE)

    embolsados = (
        EmbolsadoPlatano.query
        .filter_by(finca_id=finca_id)
        .all()
    )

    cortadas = []

    for embolsado in embolsados:
        fecha_corte = embolsado.fecha_estimada_corte

        if not fecha_corte or fecha_corte < desde:
            continue

        dias = (fecha_corte - hoy).days

        if dias <= 0:
            estado = "lista"
        elif dias <= 7:
            estado = "pronto"
        else:
            estado = "programada"

        cortadas.append({
            "lote": embolsado.lote,
            "tipo_cultivo": embolsado.tipo_cultivo,
            "racimos": embolsado.racimos_embolsados,
            "fecha_embolsado": embolsado.fecha_embolsado,
            "fecha_corte": fecha_corte,
            "dias": dias,
            "estado": estado,
        })

    cortadas.sort(key=lambda item: item["fecha_corte"])

    return cortadas[:limite]


def proxima_cortada(finca_id):
    cortadas = proximas_cortadas(finca_id, limite=1)

    return cortadas[0] if cortadas else None


def texto_cortada(cortada):
    if not cortada:
        return None

    if cortada["dias"] < 0:
        cuando = f"lista hace {abs(cortada['dias'])} días"
    elif cortada["dias"] == 0:
        cuando = "lista para cortar hoy"
    elif cortada["dias"] == 1:
        cuando = "mañana"
    else:
        cuando = f"en {cortada['dias']} días"

    return f"{cortada['lote']} · {cortada['racimos']} racimos · {cuando}"


def proximas_cosechas_cafe(finca_id, limite=3):
    """Florecidas cuya ventana de cosecha (7 a 9 meses) aún no termina."""
    from app.routes.produccion_cafe import preparar_florecidas

    florecidas = (
        FlorecidaCafe.query
        .filter_by(finca_id=finca_id)
        .order_by(FlorecidaCafe.fecha_florecida.asc())
        .all()
    )

    vigentes = [
        item for item in preparar_florecidas(florecidas)
        if item["estado"] != "Finalizada / revisar"
    ]

    vigentes.sort(key=lambda item: item["fecha_inicio_cosecha"])

    return vigentes[:limite]
