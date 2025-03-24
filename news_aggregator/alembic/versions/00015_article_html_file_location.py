"""
Add article_html_file_location column to articles table in all portal schemas

Revision ID: 0015
Revises: 0014
Create Date: 2025-03-19 10:05:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = '0015'
down_revision = '0014'
branch_labels = None
depends_on = None

def upgrade():
    connection: Connection = op.get_bind()
    # Retrieve all portal schemas from the public.news_portals table
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Adding article_html_file_location column to {portal_schema}.articles")
        # Add the article_html_file_location column with type text and specified collation
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            ADD COLUMN article_html_file_location text COLLATE pg_catalog."default";
        """))
    print("Upgrade complete: article_html_file_location column added to all articles tables.")

def downgrade():
    connection: Connection = op.get_bind()
    # Retrieve all portal schemas from the public.news_portals table
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Dropping article_html_file_location column from {portal_schema}.articles")
        # Drop the article_html_file_location column for the current portal schema
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            DROP COLUMN article_html_file_location;
        """))
    print("Downgrade complete: article_html_file_location column dropped from all articles tables.")
