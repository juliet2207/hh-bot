"""add type column to cv

Revision ID: c7f2d32c2a1b
Revises: ab3729d34f0c
Create Date: 2025-02-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7f2d32c2a1b'
down_revision = 'ab3729d34f0c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cv', sa.Column('type', sa.Integer(), server_default='0', nullable=False))
    op.create_index('ix_cv_user_vacancy_type', 'cv', ['user_id', 'vacancy_id', 'type'], unique=False)


def downgrade():
    op.drop_index('ix_cv_user_vacancy_type', table_name='cv')
    op.drop_column('cv', 'type')
