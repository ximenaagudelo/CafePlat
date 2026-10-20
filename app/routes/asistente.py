"""
CafePlatIA: asistente que responde preguntas sobre la finca activa.

Usa la API de Claude cuando ANTHROPIC_API_KEY está configurada.
Sin clave, responde con reglas simples a partir de los mismos datos.
"""
import logging
import os
import re
from datetime import date
from decimal import Decimal, InvalidOperation

import anthropic
from flask import Blueprint, abort, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func

from app.models import (
    Gasto,
    ProduccionCafe,
    ProduccionPlatano,
    RegistroTrabajo,
    Trabajador,
    Venta,
)
from app.services import cafe as conversion_cafe
from app.services.alertas import (
    proximas_cortadas,
    proximas_cosechas_cafe,
    texto_cortada,
)


asistente_bp = Blueprint("asistente", __name__, url_prefix="/asistente")

logger = logging.getLogger(__name__)

MODELO = "claude-opus-5-5"
MAX_MENSAJES = 12
MAX_CARACTERES = 1500

INSTRUCCIONES = """Eres CafePlatIA, el asistente de CaféPlat, una aplicación para fincas \
colombianas que registran café y plátano. Hablas con el administrador o dueño de la finca.

Responde en español sencillo de campo, corto y directo: 2 a 6 frases o una lista breve. \
Puedes usar algún emoji (☕ 🍌 🌱) pero sin exagerar. No uses tablas ni Markdown con #; \
usa texto plano con saltos de línea.

Usa solo los datos de la finca que vienen abajo. Si te preguntan algo que no está en los \
datos, dilo y sugiere en qué sección de la app se registra. No inventes cifras.

Reglas de conversión del café en esta finca:
- Una arroba de café cereza (recién cogido) son 60 kg.
- 60 kg de cereza dan 12,5 kg de café pergamino seco, que es una arroba de pergamino.
- Una carga son 10 arrobas de pergamino (125 kg).

Plátano: la fecha estimada de corte es la fecha de embolsado más el ciclo del lote \
(por defecto 90 días). Si hay una cortada próxima, avísala cuando sea relevante."""


def numero(valor, decimales=1):
    valor = Decimal(str(valor or 0))
    texto = f"{valor:,.{decimales}f}"

    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def pesos(valor):
    return "$ " + numero(valor, 0)


def sumar(query, columna):
    return Decimal(str(
        query.with_entities(func.coalesce(func.sum(columna), 0)).scalar() or 0
    ))


def datos_finca(finca):
    """Resumen de la finca que se le entrega al asistente."""
    finca_id = finca.id

    cafe = ProduccionCafe.query.filter_by(finca_id=finca_id)
    resumen = conversion_cafe.resumen_cafe(
        sumar(cafe.filter(ProduccionCafe.tipo_cafe == "cerezo"), ProduccionCafe.kilos_totales),
        sumar(cafe.filter(ProduccionCafe.tipo_cafe == "pergamino"), ProduccionCafe.kilos_totales),
    )

    platano = ProduccionPlatano.query.filter_by(finca_id=finca_id)
    ventas = Venta.query.filter_by(finca_id=finca_id)
    registros = RegistroTrabajo.query.filter_by(finca_id=finca_id)

    ultima_cafe = cafe.order_by(ProduccionCafe.fecha.desc()).first()
    ultima_platano = platano.order_by(ProduccionPlatano.fecha.desc()).first()

    cortadas = proximas_cortadas(finca_id)
    cosechas = proximas_cosechas_cafe(finca_id)

    lineas = [
        f"Finca: {finca.nombre}" + (f" ({finca.ubicacion})" if finca.ubicacion else ""),
        f"Fecha de hoy: {date.today().strftime('%d/%m/%Y')}",
        "",
        "CAFÉ (acumulado)",
        f"- Cereza: {numero(resumen['kilos_cerezo'])} kg = {numero(resumen['arrobas_cerezo'], 2)} arrobas de 60 kg",
        f"- Pergamino: {numero(resumen['kilos_pergamino'])} kg = {numero(resumen['arrobas_pergamino'], 2)} arrobas de 12,5 kg",
        f"- Total equivalente en pergamino seco: {numero(resumen['pergamino_equivalente'])} kg = "
        f"{numero(resumen['arrobas_equivalentes'], 2)} arrobas = {numero(resumen['cargas_equivalentes'], 2)} cargas",
    ]

    if ultima_cafe:
        lineas.append(
            f"- Último registro: {ultima_cafe.fecha.strftime('%d/%m/%Y')}, lote {ultima_cafe.lote}, "
            f"{numero(ultima_cafe.kilos_totales)} kg de {ultima_cafe.tipo_cafe}"
        )

    if cosechas:
        lineas.append("- Próximas cosechas por florecida:")
        for item in cosechas:
            lineas.append(
                f"  · Lote {item['florecida'].lote}: {item['estado'].lower()}, "
                f"del {item['fecha_inicio_cosecha'].strftime('%d/%m/%Y')} "
                f"al {item['fecha_fin_cosecha'].strftime('%d/%m/%Y')}"
            )

    lineas += [
        "",
        "PLÁTANO / BANANO (acumulado)",
        f"- {numero(sumar(platano, ProduccionPlatano.kilos))} kg en "
        f"{numero(sumar(platano, ProduccionPlatano.racimos), 0)} racimos",
    ]

    if ultima_platano:
        lineas.append(
            f"- Último corte registrado: {ultima_platano.fecha.strftime('%d/%m/%Y')}, lote {ultima_platano.lote}"
        )

    if cortadas:
        lineas.append("- Próximas cortadas según embolsado:")
        for cortada in cortadas:
            lineas.append(
                f"  · {texto_cortada(cortada)} (fecha estimada {cortada['fecha_corte'].strftime('%d/%m/%Y')}, "
                f"{cortada['tipo_cultivo']})"
            )
    else:
        lineas.append("- No hay embolsados con cortada próxima registrada.")

    lineas += [
        "",
        "DINERO (acumulado)",
        f"- Ventas de café: {pesos(sumar(ventas.filter(Venta.producto == 'cafe'), Venta.valor_total))}",
        f"- Ventas de plátano y otros: {pesos(sumar(ventas.filter(Venta.producto != 'cafe'), Venta.valor_total))}",
        f"- Gastos e insumos: {pesos(sumar(Gasto.query.filter_by(finca_id=finca_id), Gasto.valor))}",
        f"- Mano de obra total: {pesos(sumar(registros, RegistroTrabajo.total_pagar))}",
        f"- Pendiente por pagar a trabajadores: "
        f"{pesos(sumar(registros.filter(RegistroTrabajo.pagado.is_(False)), RegistroTrabajo.total_pagar))}",
        f"- Trabajadores registrados: {Trabajador.query.filter_by(finca_id=finca_id).count()}",
    ]

    return "\n".join(lineas), cortadas, cosechas, resumen


def limpiar_historial(mensajes):
    historial = []

    for mensaje in (mensajes or [])[-MAX_MENSAJES:]:
        if not isinstance(mensaje, dict):
            continue

        rol = mensaje.get("role")
        texto = str(mensaje.get("content") or "").strip()[:MAX_CARACTERES]

        if rol in ("user", "assistant") and texto:
            historial.append({"role": rol, "content": texto})

    # La conversación debe empezar con el usuario.
    while historial and historial[0]["role"] != "user":
        historial.pop(0)

    return historial


def preguntar_a_claude(datos, historial):
    cliente = anthropic.Anthropic(timeout=60.0, max_retries=1)

    respuesta = cliente.beta.messages.create(
        model=MODELO,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low"},
        system=f"{INSTRUCCIONES}\n\nDATOS DE LA FINCA\n{datos}",
        messages=historial,
    )

    if respuesta.stop_reason == "refusal":
        return "No puedo ayudar con esa pregunta. Pregúntame por la producción, las ventas o las cortadas de la finca."

    texto = "".join(
        bloque.text for bloque in respuesta.content if bloque.type == "text"
    ).strip()

    return texto or "No tengo una respuesta para eso. Intenta preguntarlo de otra forma."


def extraer_kilos(texto):
    encontrado = re.search(r"(\d+(?:[.,]\d+)?)", texto)

    if not encontrado:
        return None

    try:
        return Decimal(encontrado.group(1).replace(",", "."))
    except InvalidOperation:
        return None


def respuesta_local(pregunta, cortadas, cosechas, resumen):
    """Respuestas básicas cuando la IA no está configurada o falla."""
    texto = pregunta.lower()

    if any(palabra in texto for palabra in ("cort", "plátano", "platano", "racimo", "embols")):
        if not cortadas:
            return "🍌 No hay cortadas próximas. Registra los embolsados en Plátano para que pueda avisarte."

        lineas = ["🍌 Próximas cortadas:"]
        lineas += [
            f"· {texto_cortada(c)} ({c['fecha_corte'].strftime('%d/%m/%Y')})"
            for c in cortadas
        ]
        return "\n".join(lineas)

    if any(palabra in texto for palabra in ("cereza", "pergamino", "arroba", "convert", "carga")):
        kilos = extraer_kilos(texto)

        if kilos and "cereza" in texto:
            pergamino = conversion_cafe.kilos_a_pergamino(kilos, "cerezo")
            return (
                f"☕ {numero(kilos)} kg de cereza son {numero(kilos / conversion_cafe.KG_ARROBA_CEREZA, 2)} arrobas "
                f"y dan unos {numero(pergamino)} kg de pergamino seco "
                f"({numero(pergamino / conversion_cafe.KG_ARROBA_PERGAMINO, 2)} arrobas)."
            )

        return (
            "☕ 60 kg de café cereza son una arroba recién cogida y dan 12,5 kg de pergamino seco, "
            "que es una arroba de pergamino. Una carga son 10 arrobas (125 kg).\n"
            f"Llevas {numero(resumen['pergamino_equivalente'])} kg equivalentes en pergamino "
            f"({numero(resumen['arrobas_equivalentes'], 2)} arrobas)."
        )

    if any(palabra in texto for palabra in ("cosecha", "florec", "café", "cafe")):
        if cosechas:
            item = cosechas[0]
            return (
                f"🌸 La próxima cosecha es del lote {item['florecida'].lote}: "
                f"del {item['fecha_inicio_cosecha'].strftime('%d/%m/%Y')} "
                f"al {item['fecha_fin_cosecha'].strftime('%d/%m/%Y')}."
            )

        return (
            f"☕ Llevas {numero(resumen['arrobas_equivalentes'], 2)} arrobas de café en pergamino "
            "(equivalente). Registra las florecidas para estimar la próxima cosecha."
        )

    return (
        "Puedo contarte la próxima cortada de plátano, convertir café cereza a pergamino "
        "o decirte cuándo viene la cosecha. Las respuestas completas con IA se activan "
        "cuando el administrador configura ANTHROPIC_API_KEY."
    )


@asistente_bp.post("/preguntar")
@login_required
def preguntar():
    if current_user.is_admin or not current_user.finca:
        abort(403)

    cuerpo = request.get_json(silent=True) or {}
    historial = limpiar_historial(cuerpo.get("mensajes"))

    if not historial or historial[-1]["role"] != "user":
        return jsonify({"error": "Escribe una pregunta."}), 400

    datos, cortadas, cosechas, resumen = datos_finca(current_user.finca)
    pregunta = historial[-1]["content"]

    if not os.getenv("ANTHROPIC_API_KEY"):
        return jsonify({
            "respuesta": respuesta_local(pregunta, cortadas, cosechas, resumen),
            "modo": "basico",
        })

    try:
        return jsonify({"respuesta": preguntar_a_claude(datos, historial), "modo": "ia"})
    except anthropic.RateLimitError:
        mensaje = "Hay muchas preguntas en este momento. Intenta de nuevo en un minuto."
    except anthropic.AuthenticationError:
        logger.error("CafePlatIA: ANTHROPIC_API_KEY inválida.")
        mensaje = "La clave de la IA no es válida. Avísale al administrador."
    except anthropic.APIStatusError as error:
        logger.error("CafePlatIA: error %s de la API: %s", error.status_code, error.message)
        mensaje = "La IA no respondió bien esta vez."
    except anthropic.APIConnectionError:
        logger.error("CafePlatIA: sin conexión con la API.")
        mensaje = "No hay conexión con la IA."

    return jsonify({
        "respuesta": f"{mensaje}\n\n{respuesta_local(pregunta, cortadas, cosechas, resumen)}",
        "modo": "basico",
    })
