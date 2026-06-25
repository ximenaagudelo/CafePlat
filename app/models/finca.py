from app.extensions import db


class Finca(db.Model):
    __tablename__ = "fincas"

    id = db.Column(db.Integer, primary_key=True)

    codigo = db.Column(
        db.String(50),
        nullable=False,
        unique=True
    )

    nombre = db.Column(
        db.String(150),
        nullable=False
    )

    propietario = db.Column(
        db.String(150),
        nullable=True
    )

    logo = db.Column(
        db.String(255),
        nullable=True
    )

    ubicacion = db.Column(
        db.String(255),
        nullable=True
    )

    usuarios = db.relationship(
        "Usuario",
        back_populates="finca"
    )

    trabajadores = db.relationship(
        "Trabajador",
        back_populates="finca"
    )

    registros_trabajo = db.relationship(
        "RegistroTrabajo",
        back_populates="finca"
    )
    gastos = db.relationship(
        "Gasto",
        back_populates="finca"
    )

    ventas = db.relationship(
        "Venta",
        back_populates="finca"
    )

    def __repr__(self):
        return f"<Finca {self.codigo} - {self.nombre}>"