"""
Conversiones de café usadas en toda la aplicación.

Cuando se coge el café, una arroba de café cereza son 60 kg.
Esos 60 kg de cereza, ya beneficiados y secos, dan 12,5 kg de pergamino,
que es una arroba de café pergamino. Una carga son 10 arrobas (125 kg pergamino).
"""
from decimal import Decimal


KG_ARROBA_CEREZA = Decimal("60")
KG_ARROBA_PERGAMINO = Decimal("12.5")
ARROBAS_POR_CARGA = Decimal("10")


def _decimal(valor):
    if valor is None:
        return Decimal("0")

    return Decimal(str(valor))


def kilos_a_pergamino(kilos, tipo_cafe):
    """Kilos equivalentes en pergamino seco."""
    kilos = _decimal(kilos)

    if tipo_cafe == "cerezo":
        # Multiplicar antes de dividir evita perder décimas (240 kg -> 50 kg exactos).
        return kilos * KG_ARROBA_PERGAMINO / KG_ARROBA_CEREZA

    return kilos


def arrobas(kilos, tipo_cafe):
    """Arrobas según el estado del café: 60 kg en cereza, 12,5 kg en pergamino."""
    kilos = _decimal(kilos)

    if tipo_cafe == "cerezo":
        return kilos / KG_ARROBA_CEREZA

    return kilos / KG_ARROBA_PERGAMINO


def cargas(kilos, tipo_cafe):
    return arrobas(kilos, tipo_cafe) / ARROBAS_POR_CARGA


def resumen_cafe(kilos_cerezo, kilos_pergamino):
    """Totales de café sin mezclar kilos de cereza con kilos de pergamino."""
    kilos_cerezo = _decimal(kilos_cerezo)
    kilos_pergamino = _decimal(kilos_pergamino)

    pergamino_equivalente = (
        kilos_a_pergamino(kilos_cerezo, "cerezo") + kilos_pergamino
    )
    arrobas_equivalentes = pergamino_equivalente / KG_ARROBA_PERGAMINO

    return {
        "kilos_cerezo": kilos_cerezo,
        "kilos_pergamino": kilos_pergamino,
        "arrobas_cerezo": arrobas(kilos_cerezo, "cerezo"),
        "arrobas_pergamino": arrobas(kilos_pergamino, "pergamino"),
        "pergamino_equivalente": pergamino_equivalente,
        "arrobas_equivalentes": arrobas_equivalentes,
        "cargas_equivalentes": arrobas_equivalentes / ARROBAS_POR_CARGA,
    }
