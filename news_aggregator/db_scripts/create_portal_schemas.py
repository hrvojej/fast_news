#!/usr/bin/env python3
import json
from sqlalchemy import create_engine, text
from db_scripts.models.models import create_portal_category_model, create_portal_article_model
from sqlalchemy.engine import URL
import os

def create_portal_schemas(connection_url):
    """Create schemas and tables for each portal"""
    engine = create_engine(connection_url)

    # Read portal data
    script_dir = os.path.dirname(os.path.abspath(__file__))
    portals_file = os.path.join(script_dir, 'models', 'portals.json')
    with open(portals_file) as f:
        portals = json.load(f)

    with engine.begin() as conn:
        # Get existing portal prefixes from database
        result = conn.execute(text("SELECT portal_prefix FROM public.news_portals"))
        db_portals = {row[0] for row in result}

        # Create schema and tables for each portal
        for portal in portals:
            prefix = portal['portal_prefix']
            if prefix not in db_portals:
                print(f"Skipping {prefix} - not found in database")
                continue

            print(f"Creating schema and tables for {prefix}")
            
            # Create schema
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {prefix}'))

            # Create tables using SQLAlchemy models
            PortalCategory = create_portal_category_model(prefix)
            PortalArticle = create_portal_article_model(prefix)

            # Create tables
            PortalCategory.__table__.create(conn, checkfirst=True)
            PortalArticle.__table__.create(conn, checkfirst=True)

if __name__ == '__main__':
    # Get database URL from environment or use a default
    db_url = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/your_database')
    create_portal_schemas(db_url)