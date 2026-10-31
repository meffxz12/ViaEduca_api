"""nota_capes vira string para aceitar conceito A

Revision ID: 839cdbc2c290
Revises: 4320f41c133b
Create Date: 2026-09-24 14:20:24.270723

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '839cdbc2c290'
down_revision: Union[str, Sequence[str], None] = '4320f41c133b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # remove a trava antiga que só aceitava número 1-7
    op.drop_constraint('ck_nota_capes', 'programas', type_='check')

    # muda o tipo da coluna, convertendo os números existentes pra texto
    op.alter_column(
        'programas', 'nota_capes',
        existing_type=sa.SmallInteger(),
        type_=sa.String(length=2),
        postgresql_using='nota_capes::text',
    )


def downgrade() -> None:
    op.alter_column(
        'programas', 'nota_capes',
        existing_type=sa.String(length=2),
        type_=sa.SmallInteger(),
        postgresql_using="CASE WHEN nota_capes ~ '^[0-9]+$' THEN nota_capes::smallint ELSE NULL END",
    )
    op.create_check_constraint('ck_nota_capes', 'programas', 'nota_capes IS NULL')
