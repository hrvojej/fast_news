"""
Add structured summary JSON columns to articles table in all portal schemas

Revision ID: 0018
Revises: 0017
Create Date: 2026-04-07 14:00:00
"""

from alembic import op
from sqlalchemy import text
from sqlalchemy.engine import Connection


# revision identifiers, used by Alembic.
revision = '0018'
down_revision = '0017'
branch_labels = None
depends_on = None


def upgrade():
    connection: Connection = op.get_bind()
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")

    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Adding structured summary columns to {portal_schema}.articles")
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles
            ADD COLUMN summary_plan_json JSONB,
            ADD COLUMN summary_keywords_json JSONB,
            ADD COLUMN summary_entities_json JSONB,
            ADD COLUMN summary_sections_json JSONB,
            ADD COLUMN summary_facts_json JSONB,
            ADD COLUMN summary_resources_json JSONB,
            ADD COLUMN summary_sentiment_json JSONB,
            ADD COLUMN summary_popularity_json JSONB;
        """))

    print("Upgrade complete: Structured summary columns added to all articles tables.")


def downgrade():
    connection: Connection = op.get_bind()
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")

    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Dropping structured summary columns from {portal_schema}.articles")
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles
            DROP COLUMN summary_popularity_json,
            DROP COLUMN summary_sentiment_json,
            DROP COLUMN summary_resources_json,
            DROP COLUMN summary_facts_json,
            DROP COLUMN summary_sections_json,
            DROP COLUMN summary_entities_json,
            DROP COLUMN summary_keywords_json,
            DROP COLUMN summary_plan_json;
        """))

    print("Downgrade complete: Structured summary columns dropped from all articles tables.")