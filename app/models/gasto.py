from datetime import date

from app.extensions import db


class Gasto(db.Model):
    __tablename__ = "gastos"

    id = db.Column(db.Integer, primary_key=True)

    finca_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "fincas.id",
            name="fk_gastos_finca_id_fincas"
        ),
        nullable=False
    )

    fecha = db.Column(
        db.Date,
        nullable=False,
        default=date.today
    )

    categoria = db.Column(
        db.String(100),
        nullable=False
    )

    descripcion = db.Column(
        db.String(255),
        nullable=False
    )

    proveedor = db.Column(
        db.String(150),
        nullable=True
    )

    valor = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    metodo_pago = db.Column(
        db.String(80),
        nullable=True
    )

    tipo = db.Column(
        db.String(80),
        nullable=False,
        default="Gasto operativo"
    )

    observaciones = db.Column(
        db.Text,
        nullable=True
    )

    finca = db.relationship(
        "Finca",
        back_populates="gastos"
    )

    def __repr__(self):
        return f"<Gasto {self.fecha} - {self.categoria} - {self.valor}>"