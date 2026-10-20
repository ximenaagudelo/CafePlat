from datetime import datetime, date

from app.extensions import db
from app.services import cafe as conversion_cafe


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
        """Arroba de 60 kg en cereza o de 12,5 kg en pergamino."""
        return conversion_cafe.arrobas(self.kilos_totales, self.tipo_cafe)

    @property
    def cargas(self):
        return conversion_cafe.cargas(self.kilos_totales, self.tipo_cafe)

    @property
    def kilos_pergamino(self):
        """Kilos equivalentes en pergamino seco (60 kg cereza = 12,5 kg)."""
        return conversion_cafe.kilos_a_pergamino(self.kilos_totales, self.tipo_cafe)


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
