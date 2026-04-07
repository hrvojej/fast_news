"""
Add opinion_analysis_json JSONB column to articles table in all portal schemas.

Revision ID: 0019
Revises: 0018
Create Date: 2026-04-07 20:00:00
"""

from alembic import op
from sqlalchemy import text
from sqlalchemy.engine import Connection


# revision identifiers, used by Alembic.
revision = '0019'
down_revision = '0018'
branch_labels = None
depends_on = None


def upgrade():
    connection: Connection = op.get_bind()
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")

    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Adding opinion_analysis_json to {portal_schema}.articles")
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles
            ADD COLUMN IF NOT EXISTS opinion_analysis_json JSONB;
        """))

    print("Upgrade complete: opinion_analysis_json column added to all articles tables.")


def downgrade():
    connection: Connection = op.get_bind()
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")

    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Dropping opinion_analysis_json from {portal_schema}.articles")
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles
            DROP COLUMN IF EXISTS opinion_analysis_json;
        """))

    print("Downgrade complete: opinion_analysis_json column dropped from all articles tables.")
