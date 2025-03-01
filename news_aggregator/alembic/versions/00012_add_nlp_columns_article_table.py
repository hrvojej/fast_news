"""
Add NLP columns to articles table in all portal schemas

Revision ID: 0012
Revises: 0011
Create Date: 2025-02-25 15:00:00
"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import text
from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None

def upgrade():
    connection: Connection = op.get_bind()
    # Retrieve all portal schemas from the public.news_portals table
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Adding NLP columns to {portal_schema}.articles")
        # Add each NLP column using ALTER TABLE for the current portal schema
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            ADD COLUMN summary TEXT;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            ADD COLUMN tldr TEXT;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            ADD COLUMN topics JSONB;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            ADD COLUMN entities JSONB;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            ADD COLUMN relations JSONB;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            ADD COLUMN sentiment_label TEXT;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            ADD COLUMN nlp_updated_at TIMESTAMP WITH TIME ZONE;
        """))
    print("Upgrade complete: NLP columns added to all articles tables.")

def downgrade():
    connection: Connection = op.get_bind()
    # Retrieve all portal schemas from the public.news_portals table
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Dropping NLP columns from {portal_schema}.articles")
        # Drop the columns in reverse order for each portal schema
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            DROP COLUMN nlp_updated_at;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            DROP COLUMN sentiment_label;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            DROP COLUMN relations;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            DROP COLUMN entities;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            DROP COLUMN topics;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            DROP COLUMN tldr;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            DROP COLUMN summary;
        """))
    print("Downgrade complete: NLP columns dropped from all articles tables.")
