"""Load portal data

Revision ID: 0002
Revises: 0001
Create Date: 2025-02-03 08:01:00

"""
from alembic import op
import json
from pathlib import Path

revision = '0002'
down_revision = '0001'

def upgrade():
    print("Starting upgrade process")
    
    print("Truncating news_portals table")
    op.execute("TRUNCATE TABLE public.news_portals CASCADE")
    
    data_path = Path(__file__).parent.parent.parent / 'db_scripts' / 'models' / 'portals.json'
    print(f"Reading portal data from: {data_path}")
    
    with open(data_path) as f:
        portals = json.load(f)
    print(f"Loaded {len(portals)} portals from JSON")
    
    for i, portal in enumerate(portals, 1):
        print(f"\nInserting portal {i}/{len(portals)}: {portal['name']}")
        try:
            op.execute(f"""
                INSERT INTO public.news_portals (
                    portal_id, portal_prefix, name, base_url, rss_url,
                    scraping_enabled, portal_language, timezone,
                    active_status, scraping_frequency_minutes
                ) VALUES (
                    gen_random_uuid(),
                    '{portal["portal_prefix"]}',
                    '{portal["name"]}',
                    '{portal["base_url"]}',
                    '{portal["rss_url"]}',
                    {portal["scraping_enabled"]},
                    '{portal["portal_language"]}',
                    '{portal["timezone"]}',
                    {portal["active_status"]},
                    {portal["scraping_frequency_minutes"]}
                )
            """)
            print(f"Successfully inserted portal: {portal['name']}")
        except Exception as e:
            print(f"Error inserting portal {portal['name']}: {str(e)}")
            raise

    print("\nUpgrade completed successfully")

def downgrade():
    print("Starting downgrade process")
    print("Truncating news_portals table")
    op.execute("TRUNCATE TABLE public.news_portals CASCADE")
    print("Downgrade completed successfully")