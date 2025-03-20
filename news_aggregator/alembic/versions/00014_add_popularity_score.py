"""
Add popularity_score column to articles table in all portal schemas

Revision ID: 0014
Revises: 0013
Create Date: 2025-03-19 10:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None

def upgrade():
    connection: Connection = op.get_bind()
    # Retrieve all portal schemas from the public.news_portals table
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Adding popularity_score column to {portal_schema}.articles")
        # Add the popularity_score column with default 0 for the current portal schema
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            ADD COLUMN popularity_score INTEGER DEFAULT 0;
        """))
    print("Upgrade complete: popularity_score column added to all articles tables.")

def downgrade():
    connection: Connection = op.get_bind()
    # Retrieve all portal schemas from the public.news_portals table
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Dropping popularity_score column from {portal_schema}.articles")
        # Drop the popularity_score column for the current portal schema
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            DROP COLUMN popularity_score;
        """))
    print("Downgrade complete: popularity_score column dropped from all articles tables.")
