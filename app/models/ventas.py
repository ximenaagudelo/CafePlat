from datetime import date
from decimal import Decimal

from app.extensions import db


class Venta(db.Model):
    __tablename__ = "ventas"

    id = db.Column(db.Integer, primary_key=True)

    finca_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "fincas.id",
            name="fk_ventas_finca_id_fincas"
        ),
        nullable=False
    )

    fecha = db.Column(
        db.Date,
        nullable=False,
        default=date.today
    )

    producto = db.Column(
        db.String(50),
        nullable=False
    )
    # Valores esperados:
    # cafe
    # platano

    tipo_producto = db.Column(
        db.String(80),
        nullable=False
    )
    # Para café:
    # Seco, Mojado, Pasilla
    #
    # Para plátano:
    # Plátano, Banano, Comino

    kilos = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    racimos = db.Column(
        db.Integer,
        nullable=True
    )

    precio_unitario = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )
    # En café: precio por arroba
    # En plátano/banano/comino: precio por kilo

    valor_total = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    observaciones = db.Column(
        db.Text,
        nullable=True
    )

    finca = db.relationship(
        "Finca",
        back_populates="ventas"
    )

    @property
    def arrobas(self):
        if self.producto != "cafe":
            return None

        if not self.kilos:
            return Decimal("0")

        return self.kilos / Decimal("12")

    @property
    def valor_calculado(self):
        if not self.kilos or not self.precio_unitario:
            return Decimal("0")

        if self.producto == "cafe":
            return self.arrobas * self.precio_unitario

        return self.kilos * self.precio_unitario

    @property
    def diferencia_valor(self):
        if not self.valor_total:
            return Decimal("0")

        return self.valor_total - self.valor_calculado

    def __repr__(self):
        return f"<Venta {self.fecha} - {self.tipo_producto} - {self.valor_total}>"