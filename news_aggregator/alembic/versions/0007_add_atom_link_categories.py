"""Add atom_link column to categories tables in all portal schemas

Revision ID: 0007
Revises: 0006
Create Date: 2025-02-05 12:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    # Get all portal prefixes (schemas) from the news_portals table
    portal_prefixes = connection.execute(
        text("SELECT portal_prefix FROM public.news_portals")
    ).fetchall()

    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Altering schema: {portal_schema}")
        # Use batch_alter_table for safety (especially if there are constraints)
        with op.batch_alter_table('categories', schema=portal_schema) as batch_op:
            batch_op.add_column(sa.Column('atom_link', sa.Text(), nullable=True))
        print(f"Added column 'atom_link' to {portal_schema}.categories")


def downgrade():
    connection = op.get_bind()
    portal_prefixes = connection.execute(
        text("SELECT portal_prefix FROM public.news_portals")
    ).fetchall()

    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Reverting schema: {portal_schema}")
        with op.batch_alter_table('categories', schema=portal_schema) as batch_op:
            batch_op.drop_column('atom_link')
        print(f"Dropped column 'atom_link' from {portal_schema}.categories")
