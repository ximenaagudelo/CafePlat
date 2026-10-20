document.addEventListener("DOMContentLoaded", function () {
    inicializarHojas();
    inicializarAsistente();
    animarTarjetas();
});

/* =========================
   Hoja inferior "Más"
   ========================= */
function inicializarHojas() {
    const overlay = document.querySelector(".hoja-overlay");
    let hojaAbierta = null;
    let botonOrigen = null;

    function abrir(hoja, boton) {
        hojaAbierta = hoja;
        botonOrigen = boton;
        hoja.hidden = false;
        overlay.hidden = false;
        boton.setAttribute("aria-expanded", "true");
        requestAnimationFrame(function () {
            hoja.classList.add("abierta");
            overlay.classList.add("visible");
        });
        const primero = hoja.querySelector("a, button");
        if (primero) primero.focus();
    }

    function cerrar() {
        if (!hojaAbierta) return;
        const hoja = hojaAbierta;
        hoja.classList.remove("abierta");
        overlay.classList.remove("visible");
        botonOrigen.setAttribute("aria-expanded", "false");
        botonOrigen.focus();
        setTimeout(function () {
            hoja.hidden = true;
            overlay.hidden = true;
        }, 200);
        hojaAbierta = null;
    }

    document.querySelectorAll("[data-abrir-hoja]").forEach(function (boton) {
        boton.setAttribute("aria-expanded", "false");
        boton.addEventListener("click", function () {
            const hoja = document.getElementById(boton.dataset.abrirHoja);
            if (!hoja) return;
            hojaAbierta === hoja ? cerrar() : abrir(hoja, boton);
        });
    });

    if (overlay) overlay.addEventListener("click", cerrar);

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") cerrar();
    });
}

/* =========================
   CafePlatIA
   ========================= */
function inicializarAsistente() {
    const panel = document.getElementById("iaPanel");
    const abrir = document.getElementById("iaAbrir");
    if (!panel || !abrir) return;

    const cerrar = document.getElementById("iaCerrar");
    const form = document.getElementById("iaForm");
    const input = document.getElementById("iaTexto");
    const lista = document.getElementById("iaMensajes");
    const sugerencias = document.getElementById("iaSugerencias");
    const clave = "cafeplatia." + panel.dataset.finca;

    let historial = [];
    let enviando = false;

    try {
        historial = JSON.parse(sessionStorage.getItem(clave) || "[]");
    } catch (_) {
        historial = [];
    }

    historial.forEach(function (mensaje) {
        pintar(mensaje.role, mensaje.content);
    });
    if (historial.length) sugerencias.hidden = true;

    function guardar() {
        try {
            sessionStorage.setItem(clave, JSON.stringify(historial.slice(-12)));
        } catch (_) {}
    }

    function pintar(rol, texto) {
        const burbuja = document.createElement("div");
        burbuja.className = "ia-msg " + rol;
        burbuja.textContent = texto;
        lista.appendChild(burbuja);
        lista.scrollTop = lista.scrollHeight;
        return burbuja;
    }

    function mostrar(visible) {
        panel.hidden = !visible;
        abrir.setAttribute("aria-expanded", String(visible));
        document.body.classList.toggle("ia-abierta", visible);
        if (visible) {
            lista.scrollTop = lista.scrollHeight;
            input.focus();
        } else {
            abrir.focus();
        }
    }

    abrir.addEventListener("click", function () {
        mostrar(panel.hidden);
    });
    cerrar.addEventListener("click", function () {
        mostrar(false);
    });
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !panel.hidden) mostrar(false);
    });

    async function enviar(texto) {
        texto = texto.trim();
        if (!texto || enviando) return;

        enviando = true;
        sugerencias.hidden = true;
        input.value = "";

        historial.push({ role: "user", content: texto });
        pintar("user", texto);
        const pensando = pintar("assistant pensando", "Pensando…");

        try {
            const respuesta = await fetch(panel.dataset.url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mensajes: historial })
            });
            const datos = await respuesta.json();
            const contenido = datos.respuesta || datos.error || "No pude responder.";

            pensando.remove();
            pintar("assistant", contenido);

            if (datos.respuesta) {
                historial.push({ role: "assistant", content: contenido });
            } else {
                historial.pop();
            }
        } catch (_) {
            pensando.remove();
            pintar("assistant", "No hay conexión. Revisa el internet e intenta de nuevo.");
            historial.pop();
        }

        guardar();
        enviando = false;
        input.focus();
    }

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        enviar(input.value);
    });

    sugerencias.querySelectorAll("button").forEach(function (boton) {
        boton.addEventListener("click", function () {
            enviar(boton.textContent);
        });
    });
}

/* =========================
   Aparición suave de tarjetas
   (animación CSS: si el JS falla, todo sigue visible)
   ========================= */
function animarTarjetas() {
    document.querySelectorAll(
        ".stat-card, .panel-card, .dashboard-kpi-card, .alerta-card, .hero-finca, .balance-card"
    ).forEach(function (elemento, index) {
        elemento.style.animationDelay = Math.min(index * 45, 360) + "ms";
        elemento.classList.add("reveal");
    });
}
