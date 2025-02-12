"""Add article_status table to all portal schemas

Revision ID: 0007
Revises: 0006
Create Date: 2025-02-10 14:00:00
"""
from alembic import op
from sqlalchemy import text
from sqlalchemy.engine import Connection
from db_scripts.models.models import create_portal_article_status_model

revision = "0007"
down_revision = "0006"

def upgrade():
    connection: Connection = op.get_bind()
    # Get the list of portal prefixes (which are used as schema names)
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")

    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"\nProcessing portal schema: {portal_schema}")
        try:
            # Build the new model for article_status
            article_status_model = create_portal_article_status_model(portal_schema)
            # Create the new table only if it does not already exist.
            article_status_model.__table__.create(connection, checkfirst=True)
            print(f"Created article_status table in schema {portal_schema}")
        except Exception as e:
            print(f"Error creating article_status table in schema {portal_schema}: {e}")
            raise

    print("\nUpgrade completed successfully")


def downgrade():
    connection = op.get_bind()
    # In downgrade, we only drop the article_status table from each schema
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas for downgrade")

    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"\nDropping article_status table from schema: {portal_schema}")
        # Note: Use CASCADE if there might be dependent objects
        op.execute(text(f"DROP TABLE IF EXISTS {portal_schema}.article_status CASCADE"))
        print(f"Dropped article_status table from schema {portal_schema}")

    print("\nDowngrade completed successfully")
