"""
Add html_processing_status column to article_status table in all portal schemas

Revision ID: 0017
Revises: 0016
Create Date: 2025-04-13 10:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = '0017'
down_revision = '0016'
branch_labels = None
depends_on = None

def upgrade():
    connection: Connection = op.get_bind()
    # Retrieve all portal schemas from the public.news_portals table
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Adding html_processing_status column to {portal_schema}.article_status")
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.article_status 
            ADD COLUMN html_processing_status boolean NOT NULL DEFAULT false;
        """))
    print("Upgrade complete: html_processing_status column added to all article_status tables.")

def downgrade():
    connection: Connection = op.get_bind()
    # Retrieve all portal schemas from the public.news_portals table
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Dropping html_processing_status column from {portal_schema}.article_status")
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.article_status 
            DROP COLUMN html_processing_status;
        """))
    print("Downgrade complete: html_processing_status column dropped from all article_status tables.")
