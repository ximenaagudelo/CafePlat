from sqlalchemy import func
from app.extensions import db


class RegistroTrabajo(db.Model):
    __tablename__ = "registros_trabajo"

    id = db.Column(db.Integer, primary_key=True)

    finca_id = db.Column(
        db.Integer,
        db.ForeignKey("fincas.id"),
        nullable=True
    )

    trabajador_id = db.Column(
        db.Integer,
        db.ForeignKey("trabajadores.id"),
        nullable=False
    )

    fecha = db.Column(db.Date, nullable=False)

    tipo_trabajo = db.Column(db.String(50), nullable=False)

    kilos_cafe = db.Column(db.Numeric(10, 2), nullable=True)

    precio_kilo = db.Column(db.Numeric(12, 2), nullable=True)

    valor_dia = db.Column(db.Numeric(12, 2), nullable=True)

    total_pagar = db.Column(db.Numeric(12, 2), nullable=False)

    pagado = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default="0"
    )

    creado_en = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    finca = db.relationship(
        "Finca",
        back_populates="registros_trabajo"
    )

    trabajador = db.relationship(
        "Trabajador",
        back_populates="registros"
    )

    def __repr__(self):
        return f"<RegistroTrabajo {self.fecha} - {self.total_pagar}>"