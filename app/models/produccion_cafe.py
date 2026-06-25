from datetime import datetime, date
from decimal import Decimal

from app.extensions import db


class ProduccionCafe(db.Model):
    __tablename__ = "producciones_cafe"

    id = db.Column(db.Integer, primary_key=True)

    finca_id = db.Column(
        db.Integer,
        db.ForeignKey("fincas.id"),
        nullable=False,
        index=True
    )

    fecha = db.Column(db.Date, nullable=False, default=date.today)

    lote = db.Column(db.String(120), nullable=False)

    tipo_cafe = db.Column(db.String(30), nullable=False)
    # Valores esperados:
    # cerezo
    # pergamino

    kilos_totales = db.Column(db.Numeric(12, 2), nullable=False)

    observaciones = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    finca = db.relationship(
        "Finca",
        backref=db.backref("producciones_cafe", lazy=True)
    )

    @property
    def arrobas(self):
        if self.kilos_totales is None:
            return Decimal("0")

        return Decimal(self.kilos_totales) / Decimal("12")

    @property
    def cargas(self):
        if self.kilos_totales is None:
            return Decimal("0")

        return Decimal(self.kilos_totales) / Decimal("120")


class FlorecidaCafe(db.Model):
    __tablename__ = "florecidas_cafe"

    id = db.Column(db.Integer, primary_key=True)

    finca_id = db.Column(
        db.Integer,
        db.ForeignKey("fincas.id"),
        nullable=False,
        index=True
    )

    fecha_florecida = db.Column(db.Date, nullable=False)

    lote = db.Column(db.String(120), nullable=False)

    observaciones = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    finca = db.relationship(
        "Finca",
        backref=db.backref("florecidas_cafe", lazy=True)
    )
