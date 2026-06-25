from datetime import date
from decimal import Decimal

from app.extensions import db


class Inventario(db.Model):
    __tablename__ = "inventario"

    id = db.Column(db.Integer, primary_key=True)

    finca_id = db.Column(
        db.Integer,
        db.ForeignKey("fincas.id"),
        nullable=False,
        index=True
    )

    nombre = db.Column(db.String(120), nullable=False)
    categoria = db.Column(db.String(80), nullable=False)
    unidad_medida = db.Column(db.String(40), nullable=False)

    cantidad_disponible = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0
    )

    costo_unitario = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0
    )

    proveedor = db.Column(db.String(120), nullable=True)
    ubicacion = db.Column(db.String(120), nullable=True)
    observaciones = db.Column(db.Text, nullable=True)

    movimientos = db.relationship(
        "MovimientoInventario",
        backref="item",
        lazy=True,
        cascade="all, delete-orphan"
    )

    @property
    def valor_estimado(self):
        cantidad = self.cantidad_disponible or Decimal("0")
        costo = self.costo_unitario or Decimal("0")
        return cantidad * costo

    def __repr__(self):
        return f"<Inventario {self.nombre}>"


class MovimientoInventario(db.Model):
    __tablename__ = "movimiento_inventario"

    id = db.Column(db.Integer, primary_key=True)

    finca_id = db.Column(
        db.Integer,
        db.ForeignKey("fincas.id"),
        nullable=False,
        index=True
    )

    inventario_id = db.Column(
        db.Integer,
        db.ForeignKey("inventario.id"),
        nullable=False,
        index=True
    )

    fecha = db.Column(db.Date, nullable=False, default=date.today)

    # entrada, salida, ajuste
    tipo_movimiento = db.Column(db.String(30), nullable=False)

    cantidad = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0
    )

    costo_unitario = db.Column(
        db.Numeric(12, 2),
        nullable=True
    )

    proveedor = db.Column(db.String(120), nullable=True)
    motivo = db.Column(db.String(150), nullable=True)
    observaciones = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<MovimientoInventario {self.tipo_movimiento} {self.cantidad}>"