"""Initial public schema

Revision ID: 0001
Revises: 
Create Date: 2025-02-03 08:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

revision = '0001'
down_revision = None

def upgrade():
    print("Starting upgrade process")
    print("Creating public.news_portals table")
    
    try:
        op.execute(
            """
            CREATE TABLE public.news_portals (
                portal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                portal_prefix VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                base_url TEXT NOT NULL,
                rss_url TEXT,
                scraping_enabled BOOLEAN DEFAULT true,
                portal_language VARCHAR(50),
                timezone VARCHAR(50) DEFAULT 'UTC',
                active_status BOOLEAN DEFAULT true,
                scraping_frequency_minutes INTEGER DEFAULT 60,
                last_scraped_at TIMESTAMPTZ
            );
            """
        )
        print("Successfully created public.news_portals table")
    except Exception as e:
        print(f"Error creating public.news_portals table: {str(e)}")
        raise

    print("Upgrade completed successfully")

def downgrade():
    print("Starting downgrade process")
    print("Dropping public.news_portals table")
    op.execute("DROP TABLE public.news_portals;")
    print("Downgrade completed successfully")