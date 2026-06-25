document.addEventListener("DOMContentLoaded", function () {
    inicializarSidebarMovil();
    activarMenuActual();
    animarContenido();
    animarTarjetas();
});

function inicializarSidebarMovil() {
    const sidebar = document.getElementById("sidebar");
    const botonAbrir = document.getElementById("sidebarToggle");
    const botonCerrar = document.getElementById("sidebarClose");
    const overlay = document.getElementById("sidebarOverlay");
    const enlacesMenu = document.querySelectorAll(".menu-link");

    if (!sidebar || !botonAbrir || !overlay) {
        return;
    }

    function abrirSidebar() {
        sidebar.classList.add("is-open");
        overlay.classList.add("is-visible");
        document.body.classList.add("sidebar-open");
        botonAbrir.setAttribute("aria-expanded", "true");
    }

    function cerrarSidebar() {
        sidebar.classList.remove("is-open");
        overlay.classList.remove("is-visible");
        document.body.classList.remove("sidebar-open");
        botonAbrir.setAttribute("aria-expanded", "false");
    }

    botonAbrir.addEventListener("click", function () {
        if (sidebar.classList.contains("is-open")) {
            cerrarSidebar();
        } else {
            abrirSidebar();
        }
    });

    if (botonCerrar) {
        botonCerrar.addEventListener("click", cerrarSidebar);
    }

    overlay.addEventListener("click", cerrarSidebar);

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && sidebar.classList.contains("is-open")) {
            cerrarSidebar();
        }
    });

    enlacesMenu.forEach(function (enlace) {
        enlace.addEventListener("click", function () {
            if (window.innerWidth <= 992) {
                cerrarSidebar();
            }
        });
    });

    window.addEventListener("resize", function () {
        if (window.innerWidth > 992) {
            cerrarSidebar();
        }
    });
}

function activarMenuActual() {
    const enlaces = document.querySelectorAll(".menu-link");
    const rutaActual = normalizarRuta(window.location.pathname);

    enlaces.forEach(function (enlace) {
        enlace.classList.remove("active");

        const href = enlace.getAttribute("href");

        if (!href || href === "#") {
            return;
        }

        let rutaEnlace = "";

        try {
            rutaEnlace = normalizarRuta(new URL(href, window.location.origin).pathname);
        } catch (error) {
            rutaEnlace = normalizarRuta(href);
        }

        if (rutaEnlace === "/") {
            if (rutaActual === "/") {
                enlace.classList.add("active");
            }

            return;
        }

        if (rutaActual === rutaEnlace || rutaActual.startsWith(rutaEnlace + "/")) {
            enlace.classList.add("active");
        }
    });
}

function normalizarRuta(ruta) {
    if (!ruta) {
        return "/";
    }

    if (ruta.length > 1 && ruta.endsWith("/")) {
        return ruta.slice(0, -1);
    }

    return ruta;
}

function animarContenido() {
    const contenido = document.querySelector(".content-wrapper");

    if (contenido) {
        contenido.classList.add("animate-in");
    }
}

function animarTarjetas() {
    const elementos = document.querySelectorAll(".card, .stat-card, .panel-card, .mobile-record-card");

    if (!elementos.length) {
        return;
    }

    elementos.forEach(function (elemento, index) {
        elemento.classList.add("reveal");
        elemento.style.transitionDelay = `${index * 45}ms`;
    });

    if (!("IntersectionObserver" in window)) {
        elementos.forEach(function (elemento) {
            elemento.classList.add("visible");
        });

        return;
    }

    const observer = new IntersectionObserver(function (entradas) {
        entradas.forEach(function (entrada) {
            if (entrada.isIntersecting) {
                entrada.target.classList.add("visible");
                observer.unobserve(entrada.target);
            }
        });
    }, {
        threshold: 0.12
    });

    elementos.forEach(function (elemento) {
        observer.observe(elemento);
    });
}