# path: news_dagster-etl/news_aggregator/alembic/versions/0006_add_missing_fts_indexes.py
"""Add missing full-text search indexes

Revision ID: 0006
Revises: 0005
Create Date: 2025-02-04 01:44:00

"""
from alembic import op
from sqlalchemy import text

revision = '0006'
down_revision = '0005'

def upgrade():
    # Get list of portal schemas
    portal_schemas = op.get_bind().execute(
        text("SELECT nspname FROM pg_namespace WHERE nspname LIKE 'pt_%';")
    ).fetchall()
    
    # Create full-text search index for each portal's articles table
    for schema in portal_schemas:
        portal_schema = schema[0]
        op.execute(
            text(f"""
            CREATE INDEX idx_{portal_schema}_articles_fts 
            ON {portal_schema}.articles 
            USING GIN (to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(description, '') || ' ' || COALESCE(content, '')));
            """)
        )

def downgrade():
    # Get list of portal schemas
    portal_schemas = op.get_bind().execute(
        text("SELECT nspname FROM pg_namespace WHERE nspname LIKE 'pt_%';")
    ).fetchall()
    
    # Drop the full-text search indexes
    for schema in portal_schemas:
        portal_schema = schema[0]
        op.execute(
            text(f"DROP INDEX IF EXISTS {portal_schema}.idx_{portal_schema}_articles_fts;")
        )