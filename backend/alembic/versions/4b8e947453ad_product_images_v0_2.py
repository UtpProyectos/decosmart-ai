"""product images v0.2

Revision ID: 4b8e947453ad
Revises: 434706e64cd3
Create Date: 2026-11-18 23:02:52.333112

Columnas nuevas en product_images para imágenes subidas por el admin (doc 04, Ampliación v0.2).
`is_reference` usa server_default false para que las filas existentes (Supabase) queden válidas.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '4b8e947453ad'
down_revision: str | None = '434706e64cd3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('product_images', schema=None) as batch_op:
        batch_op.add_column(sa.Column('storage_key', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('is_reference', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column('width', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('height', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('bytes', sa.Integer(), nullable=True))

    # Paso de datos idempotente: las imágenes seed son la referencia del mueble para la simulación.
    images = sa.table('product_images', sa.column('url', sa.String), sa.column('is_reference', sa.Boolean))
    op.execute(images.update().where(images.c.url.like('/static/products/%')).values(is_reference=sa.true()))


def downgrade() -> None:
    with op.batch_alter_table('product_images', schema=None) as batch_op:
        batch_op.drop_column('bytes')
        batch_op.drop_column('height')
        batch_op.drop_column('width')
        batch_op.drop_column('is_reference')
        batch_op.drop_column('storage_key')
