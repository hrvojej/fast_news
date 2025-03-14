"""
Add summary columns to articles table in all portal schemas

Revision ID: 0013
Revises: 0012
Create Date: 2025-03-14 15:00:00
"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import text
from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None

def upgrade():
    connection: Connection = op.get_bind()
    # Retrieve all portal schemas from the public.news_portals table
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Adding summary columns to {portal_schema}.articles")
        # Add the new summary columns to the articles table in the current portal schema
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            ADD COLUMN summary_generated_at TIMESTAMP WITH TIME ZONE;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            ADD COLUMN summary_article_gemini_title TEXT;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            ADD COLUMN summary_featured_image TEXT;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            ADD COLUMN summary_first_paragraph TEXT;
        """))
    print("Upgrade complete: Summary columns added to all articles tables.")

def downgrade():
    connection: Connection = op.get_bind()
    # Retrieve all portal schemas from the public.news_portals table
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Dropping summary columns from {portal_schema}.articles")
        # Drop the new summary columns in reverse order for each portal schema
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            DROP COLUMN summary_first_paragraph;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            DROP COLUMN summary_featured_image;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            DROP COLUMN summary_article_gemini_title;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            DROP COLUMN summary_generated_at;
        """))
    print("Downgrade complete: Summary columns dropped from all articles tables.")
