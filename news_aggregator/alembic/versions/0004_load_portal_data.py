"""Load portal data

Revision ID: 0004
Revises: 0003
Create Date: 2025-02-03 08:01:00

"""
from alembic import op
import json
from pathlib import Path

revision = '0004'
down_revision = '0003'

def upgrade():
    data_path = Path(__file__).parent.parent.parent / 'db_scripts' / 'models' / 'portals.json'
    with open(data_path) as f:
        portals = json.load(f)
    
    for portal in portals:
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

def downgrade():
    op.execute("TRUNCATE TABLE public.news_portals CASCADE")
