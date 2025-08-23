"""drop laravel legacy tables

Revision ID: 658ce5763d5f
Revises: b8a24a67ca8a
Create Date: 2025-08-22 06:14:36.350535

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '658ce5763d5f'
down_revision = 'b8a24a67ca8a'
branch_labels = None
depends_on = None


LEGACY_TABLES = [
	'failed_jobs',
	'site_settings',
	'contacts',
	'reports',
	'lookups',
	'password_reset_tokens',
	'personal_access_tokens',
	'migrations',
	'login_history',
]


def upgrade():
	bind = op.get_bind()
	inspector = inspect(bind)
	existing = set(inspector.get_table_names())
	for t in LEGACY_TABLES:
		if t in existing:
			op.drop_table(t)


def downgrade():
	pass
