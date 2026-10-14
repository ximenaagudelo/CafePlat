import os
from pathlib import Path

from flask import Flask

from config import Config
from app.extensions import db, migrate, login_manager


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_object(Config)

    if os.getenv("RENDER"):
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
        )
        app.config["SESSION_COOKIE_SECURE"] = True
        app.config["SESSION_COOKIE_HTTPONLY"] = True
        app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
        app.config["PREFERRED_URL_SCHEME"] = "https"

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Debes iniciar sesión para acceder a CaféPlat."
    login_manager.login_message_category = "warning"

    from app import models
    from app.models import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.routes.trabajadores import trabajadores_bp
    app.register_blueprint(trabajadores_bp)

    from app.routes.produccion_cafe import produccion_cafe_bp
    app.register_blueprint(produccion_cafe_bp)

    from app.routes.produccion_platano import produccion_platano_bp
    app.register_blueprint(produccion_platano_bp)

    from app.routes.gastos import gastos_bp
    app.register_blueprint(gastos_bp)

    from app.routes.ventas import ventas_bp
    app.register_blueprint(ventas_bp)

    from app.routes.inventario import inventario_bp
    app.register_blueprint(inventario_bp)

    from app.routes.reportes import reportes_bp
    app.register_blueprint(reportes_bp)

    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp)



    return app
