"""Create portal articles and categories tables

Revision ID: 0004
Revises: 0003
Create Date: 2025-02-03 10:20:00
"""
from alembic import op
from sqlalchemy import text
from sqlalchemy.schema import CreateSchema
from sqlalchemy.engine import Connection
from db_scripts.models.models import create_portal_category_model, create_portal_article_model, Base

revision = "0004"
down_revision = "0003"

def create_portal_schema(connection: Connection, portal_schema: str) -> None:
    print(f"\nProcessing schema: {portal_schema}")
    print(f"Creating schema {portal_schema}")
    connection.execute(CreateSchema(portal_schema))
    print(f"Schema {portal_schema} created successfully")
    
    print(f"Creating models for {portal_schema}")
    category_model = create_portal_category_model(portal_schema)
    article_model = create_portal_article_model(portal_schema)
    print("Models created successfully")
    
    Base.metadata.remove(category_model.__table__)
    Base.metadata.remove(article_model.__table__)
    
    print(f"Creating tables for {portal_schema}")
    category_model.__table__.create(connection)
    print(f"Categories table created for {portal_schema}")
    article_model.__table__.create(connection)
    print(f"Articles table created for {portal_schema}")

def upgrade():
    print("Starting upgrade process")
    connection = op.get_bind()
    print("Got database connection")

    print("Fetching portal prefixes")
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal prefixes")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        try:
            create_portal_schema(connection, portal_schema)
        except Exception as e:
            print(f"Error creating schema {portal_schema}: {str(e)}")
            print(f"Full error details: {e.__class__.__name__}")
            raise

    print("\nUpgrade completed successfully")

def downgrade():
    print("Starting downgrade process")
    connection = op.get_bind()
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal prefixes to remove")

    for prefix in reversed(portal_prefixes):
        portal_schema = prefix[0]
        print(f"\nProcessing schema: {portal_schema}")
        print(f"Dropping schema {portal_schema}")
        op.execute(text(f"DROP SCHEMA IF EXISTS {portal_schema} CASCADE"))
        print(f"Schema {portal_schema} dropped successfully")

    print("\nDowngrade completed successfully")