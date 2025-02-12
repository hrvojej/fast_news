"""Add status and status_type columns to article_status table in all portal schemas

Revision ID: 0009
Revises: 0008
Create Date: 2025-02-12 12:00:00
"""
from alembic import op
from sqlalchemy import text
from sqlalchemy.engine import Connection

revision = "0009"
down_revision = "0008"

def upgrade():
    connection: Connection = op.get_bind()
    # Fetch all portal schemas (using portal_prefix from public.news_portals)
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")

    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Adding status and status_type columns to article_status in schema {portal_schema}")
        
        # Add the "status" column (adjust type, default, or nullability as needed)
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.article_status
            ADD COLUMN IF NOT EXISTS status VARCHAR(50);
        """))
        
        # Add the "status_type" column (adjust type, default, or nullability as needed)
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.article_status
            ADD COLUMN IF NOT EXISTS status_type VARCHAR(50);
        """))
    print("Upgrade for status and status_type columns completed.")

def downgrade():
    connection = op.get_bind()
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Dropping status and status_type columns from article_status in schema {portal_schema}")
        
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.article_status
            DROP COLUMN IF EXISTS status;
        """))
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.article_status
            DROP COLUMN IF EXISTS status_type;
        """))
    print("Downgrade for status and status_type columns completed.")
