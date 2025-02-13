"""
Add unique_url constraint to articles table in all portal schemas

Revision ID: 0011
Revises: 0010
Create Date: 2025-02-13 10:00:00
"""

from alembic import op
from sqlalchemy import text
from sqlalchemy.engine import Connection

revision = '0011'
down_revision = '0010'

def upgrade():
    connection: Connection = op.get_bind()
    # Get all portal schemas from public.news_portals
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Adding unique constraint to {portal_schema}.articles")
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            ADD CONSTRAINT unique_url UNIQUE (url);
        """))
    print("Upgrade complete: Unique constraints added to all articles tables.")


def downgrade():
    connection: Connection = op.get_bind()
    # Get all portal schemas from public.news_portals
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Dropping unique constraint from {portal_schema}.articles")
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            DROP CONSTRAINT unique_url;
        """))
    print("Downgrade complete: Unique constraints dropped from all articles tables.")
