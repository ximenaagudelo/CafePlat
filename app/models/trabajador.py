from sqlalchemy import func
from app.extensions import db


class Trabajador(db.Model):
    __tablename__ = "trabajadores"

    id = db.Column(db.Integer, primary_key=True)

    finca_id = db.Column(
        db.Integer,
        db.ForeignKey("fincas.id"),
        nullable=True
    )

    nombre = db.Column(db.String(150), nullable=False)

    estado = db.Column(
        db.String(20),
        nullable=False,
        default="activo",
        server_default="activo"
    )

    creado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    finca = db.relationship(
        "Finca",
        back_populates="trabajadores"
    )

    registros = db.relationship(
        "RegistroTrabajo",
        back_populates="trabajador",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.CheckConstraint(
            "estado IN ('activo', 'inactivo')",
            name="ck_trabajadores_estado"
        ),
    )

    def __repr__(self):
        return f"<Trabajador {self.nombre}>"