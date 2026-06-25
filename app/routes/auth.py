from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user

from app.models import Usuario


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth"
)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        nombre_o_email = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")

        if not nombre_o_email or not password:
            flash("Ingresa usuario y contraseña.", "danger")
            return redirect(url_for("auth.login"))

        usuario = (
            Usuario.query
            .filter(
                (Usuario.nombre == nombre_o_email) |
                (Usuario.email == nombre_o_email)
            )
            .first()
        )

        if not usuario or not usuario.check_password(password):
            flash("Usuario o contraseña incorrectos.", "danger")
            return redirect(url_for("auth.login"))

        login_user(usuario)

        flash("Sesión iniciada correctamente.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("auth.login"))