from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)

    finca_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "fincas.id",
            name="fk_usuarios_finca_id_fincas"
        ),
        nullable=False
    )

    nombre = db.Column(
        db.String(80),
        nullable=False,
        unique=True
    )

    email = db.Column(
        db.String(150),
        nullable=True,
        unique=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    finca = db.relationship(
        "Finca",
        back_populates="usuarios"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Usuario {self.nombre}>"