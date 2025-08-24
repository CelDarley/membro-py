"""create membro_historico (manual)

Revision ID: 88a8b1ee3432
Revises: 9a132f54d093
Create Date: 2025-08-24 18:09:53.338441

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '88a8b1ee3432'
down_revision = '9a132f54d093'
branch_labels = None
depends_on = None


def upgrade():
	op.create_table(
		'membro_historico',
		sa.Column('id', mysql.BIGINT(unsigned=True), nullable=False),
		sa.Column('membro_id', mysql.BIGINT(unsigned=True), nullable=False),
		sa.Column('data_movimentacao', sa.Date(), nullable=True),
		sa.Column('unidade_lotacao', sa.String(length=255), nullable=True),
		sa.Column('comarca_lotacao', sa.String(length=255), nullable=True),
		sa.ForeignKeyConstraint(['membro_id'], ['membros.id']),
		sa.PrimaryKeyConstraint('id')
	)
	op.create_index(op.f('ix_membro_historico_membro_id'), 'membro_historico', ['membro_id'], unique=False)
	op.create_index(op.f('ix_membro_historico_data_movimentacao'), 'membro_historico', ['data_movimentacao'], unique=False)


def downgrade():
	op.drop_index(op.f('ix_membro_historico_data_movimentacao'), table_name='membro_historico')
	op.drop_index(op.f('ix_membro_historico_membro_id'), table_name='membro_historico')
	op.drop_table('membro_historico')
