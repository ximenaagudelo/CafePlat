from datetime import datetime, date, timedelta
from decimal import Decimal

from app.extensions import db


class ProduccionPlatano(db.Model):
    __tablename__ = "producciones_platano"

    id = db.Column(db.Integer, primary_key=True)

    finca_id = db.Column(
        db.Integer,
        db.ForeignKey("fincas.id"),
        nullable=False,
        index=True
    )

    fecha = db.Column(db.Date, nullable=False, default=date.today)

    lote = db.Column(db.String(120), nullable=False)

    tipo_cultivo = db.Column(db.String(50), nullable=False)
    # Valores esperados:
    # platano
    # banano
    # comino
    # otro

    racimos = db.Column(db.Integer, nullable=False)

    kilos = db.Column(db.Numeric(12, 2), nullable=False)

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
        backref=db.backref("producciones_platano", lazy=True)
    )

    @property
    def kilos_por_racimo(self):
        if not self.racimos or self.racimos <= 0:
            return Decimal("0")

        return Decimal(self.kilos or 0) / Decimal(self.racimos)


class EmbolsadoPlatano(db.Model):
    __tablename__ = "embolsados_platano"

    id = db.Column(db.Integer, primary_key=True)

    finca_id = db.Column(
        db.Integer,
        db.ForeignKey("fincas.id"),
        nullable=False,
        index=True
    )

    fecha_embolsado = db.Column(db.Date, nullable=False)

    lote = db.Column(db.String(120), nullable=False)

    tipo_cultivo = db.Column(db.String(50), nullable=False)
    # Valores esperados:
    # platano
    # banano
    # comino
    # otro

    racimos_embolsados = db.Column(db.Integer, nullable=False)

    ciclo_estimado_dias = db.Column(db.Integer, nullable=False, default=90)

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
        backref=db.backref("embolsados_platano", lazy=True)
    )

    @property
    def fecha_estimada_corte(self):
        if not self.fecha_embolsado:
            return None

        return self.fecha_embolsado + timedelta(days=self.ciclo_estimado_dias or 90)

    @property
    def dias_faltantes_corte(self):
        if not self.fecha_estimada_corte:
            return 0

        dias = (self.fecha_estimada_corte - date.today()).days

        if dias < 0:
            return 0

        return dias