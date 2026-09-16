"""add grande_area_id to areas_avaliacao

Revision ID: 4ef11b4ad973
Revises: af5fe33a1ff3
Create Date: 2026-09-10 16:33:22.108395

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ef11b4ad973'
down_revision: Union[str, Sequence[str], None] = 'af5fe33a1ff3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('areas_avaliacao', sa.Column('grande_area_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'areas_avaliacao_grande_area_id_fkey',
        'areas_avaliacao', 'grandes_areas',
        ['grande_area_id'], ['id'],
    )

def downgrade():
    op.drop_constraint('areas_avaliacao_grande_area_id_fkey', 'areas_avaliacao', type_='foreignkey')
    op.drop_column('areas_avaliacao', 'grande_area_id')