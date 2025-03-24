Following example of last migration I need to create a new one, make sure you increment needed fields properly when creating new migration :
revision = '0012'
down_revision = '0011'
"""
Add popularity_score column to articles table in all portal schemas

Revision ID: 0014
Revises: 0013
Create Date: 2025-03-19 10:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None

def upgrade():
    connection: Connection = op.get_bind()
    # Retrieve all portal schemas from the public.news_portals table
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Adding popularity_score column to {portal_schema}.articles")
        # Add the popularity_score column with default 0 for the current portal schema
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            ADD COLUMN popularity_score INTEGER DEFAULT 0;
        """))
    print("Upgrade complete: popularity_score column added to all articles tables.")

def downgrade():
    connection: Connection = op.get_bind()
    # Retrieve all portal schemas from the public.news_portals table
    portal_prefixes = connection.execute(text("SELECT portal_prefix FROM public.news_portals")).fetchall()
    print(f"Found {len(portal_prefixes)} portal schemas")
    
    for prefix in portal_prefixes:
        portal_schema = prefix[0]
        print(f"Dropping popularity_score column from {portal_schema}.articles")
        # Drop the popularity_score column for the current portal schema
        op.execute(text(f"""
            ALTER TABLE {portal_schema}.articles 
            DROP COLUMN popularity_score;
        """))
    print("Downgrade complete: popularity_score column dropped from all articles tables.")


New migration should add database field in all article tables in all schemas of the portals like in example. Field name should be: article_html_file_location it should be  text COLLATE pg_catalog."default", this is PostgreSQL table that currently looks like this:

CREATE TABLE IF NOT EXISTS pt_nyt.articles
(
    article_id uuid NOT NULL DEFAULT gen_random_uuid(),
    title text COLLATE pg_catalog."default" NOT NULL,
    url text COLLATE pg_catalog."default" NOT NULL,
    guid text COLLATE pg_catalog."default",
    description text COLLATE pg_catalog."default",
    content text COLLATE pg_catalog."default",
    author text[] COLLATE pg_catalog."default",
    pub_date timestamp with time zone,
    category_id uuid NOT NULL,
    keywords text[] COLLATE pg_catalog."default",
    reading_time_minutes integer,
    language_code character varying(10) COLLATE pg_catalog."default",
    image_url text COLLATE pg_catalog."default",
    sentiment_score double precision,
    share_count integer DEFAULT 0,
    view_count integer DEFAULT 0,
    comment_count integer DEFAULT 0,
    summary text COLLATE pg_catalog."default",
    tldr text COLLATE pg_catalog."default",
    topics jsonb,
    entities jsonb,
    relations jsonb,
    sentiment_label text COLLATE pg_catalog."default",
    nlp_updated_at timestamp with time zone,
    summary_generated_at timestamp with time zone,
    summary_article_gemini_title text COLLATE pg_catalog."default",
    summary_featured_image text COLLATE pg_catalog."default",
    summary_first_paragraph text COLLATE pg_catalog."default",
    popularity_score integer DEFAULT 0,
    CONSTRAINT articles_pkey PRIMARY KEY (article_id),
    CONSTRAINT articles_guid_key UNIQUE (guid),
    CONSTRAINT unique_url UNIQUE (url),
    CONSTRAINT fk_pt_nyt_article_category FOREIGN KEY (category_id)
        REFERENCES pt_nyt.categories (category_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT articles_sentiment_score_check CHECK (sentiment_score >= '-1'::integer::double precision AND sentiment_score <= 1::double precision)
)

Create new migration.  