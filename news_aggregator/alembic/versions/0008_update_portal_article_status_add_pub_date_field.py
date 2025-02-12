"""Add pub_date column to article_status table in all portal schemas

Revision ID: 0008
Revises: 0007
Create Date: 2025-02-11 12:00:00
"""
from alembic import op
from sqlalchemy import text
from sqlalchemy.engine import Connection

revision = "0008"
down_revision = "0007"

def upgrade():
    connection: Connection = op.get_bind()
    # Fetch all portal schemas (using portal_prefix from public.news_portals)
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")

    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Adding pub_date column to article_status in schema {portal_schema}")
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.article_status
            ADD COLUMN IF NOT EXISTS pub_date TIMESTAMP WITH TIME ZONE;
        """))
    print("Upgrade for pub_date column completed.")

def downgrade():
    connection = op.get_bind()
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Dropping pub_date column from article_status in schema {portal_schema}")
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.article_status
            DROP COLUMN IF EXISTS pub_date;
        """))
    print("Downgrade for pub_date column completed.")
