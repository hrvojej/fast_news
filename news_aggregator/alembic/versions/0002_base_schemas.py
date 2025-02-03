"""Create base schemas (events, comments, etc.)

Revision ID: 0002
Revises: 0001
Create Date: 2025-02-03 10:20:00

"""
from alembic import op

revision = '0002'
down_revision = '0001'

def upgrade():
    op.execute("CREATE SCHEMA IF NOT EXISTS events")
    op.execute("CREATE SCHEMA IF NOT EXISTS comments")
    op.execute("CREATE SCHEMA IF NOT EXISTS analysis")
    op.execute("CREATE SCHEMA IF NOT EXISTS topics")
    op.execute("CREATE SCHEMA IF NOT EXISTS social")
    op.execute("CREATE SCHEMA IF NOT EXISTS entities")

def downgrade():
    op.execute("DROP SCHEMA IF EXISTS events CASCADE")
    op.execute("DROP SCHEMA IF EXISTS comments CASCADE")
    op.execute("DROP SCHEMA IF EXISTS analysis CASCADE")
    op.execute("DROP SCHEMA IF EXISTS topics CASCADE")
    op.execute("DROP SCHEMA IF EXISTS social CASCADE")
    op.execute("DROP SCHEMA IF EXISTS entities CASCADE")
