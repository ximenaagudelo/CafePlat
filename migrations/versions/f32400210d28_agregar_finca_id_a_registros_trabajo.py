"""agregar finca_id a registros_trabajo

Revision ID: f32400210d28
Revises: 9333587376b3
Create Date: 2026-06-18 13:14:58.831102

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f32400210d28'
down_revision = '9333587376b3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('registros_trabajo', schema=None) as batch_op:
        batch_op.add_column(sa.Column('finca_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_registros_trabajo_finca_id_fincas',
            'fincas',
            ['finca_id'],
            ['id']
        )

def downgrade():
    with op.batch_alter_table('registros_trabajo', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_registros_trabajo_finca_id_fincas',
            type_='foreignkey'
        )
        batch_op.drop_column('finca_id')
