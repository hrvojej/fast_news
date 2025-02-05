"""Create base schemas (events, comments, etc.)

Revision ID: 0003
Revises: 0002
Create Date: 2025-02-03 10:15:00
"""

from alembic import op
from sqlalchemy import text
from db_scripts.models.models import Base

revision = "0003"
down_revision = "0002"

def upgrade():
    print("Starting upgrade process")
    connection = op.get_bind()
    print("Got database connection")
    
    tables = [
        "social.platforms",
        "events.events",
        "events.event_articles",
        "events.timeline_entries",
        "entities.entities",
        "entities.entity_relationships", 
        "entities.entity_mentions",
        "social.posts",
        "analysis.content_analysis",
        "topics.topics",
        "topics.topic_content",
        "comments.comments",
        "comments.article_comment_stats",
        "social.article_social_metrics",
        "analysis.content_statistics",
        "analysis.sentiment_lexicon",
        "topics.topic_categories"
    ]
    
    print(f"Creating {len(tables)} tables:")
    for table in tables:
        print(f"Creating table: {table}")
        
    Base.metadata.create_all(
        connection,
        tables=[Base.metadata.tables[table] for table in tables]
    )
    print("All tables created successfully")

def downgrade():
    print("Starting downgrade process")
    connection = op.get_bind()
    print("Got database connection")
    
    tables = [
        "social.platforms",
        "events.events", 
        "events.event_articles",
        "events.timeline_entries",
        "entities.entities",
        "entities.entity_relationships",
        "entities.entity_mentions",
        "social.posts",
        "analysis.content_analysis",
        "topics.topics",
        "topics.topic_content", 
        "comments.comments",
        "comments.article_comment_stats",
        "social.article_social_metrics",
        "analysis.content_statistics",
        "analysis.sentiment_lexicon",
        "topics.topic_categories"
    ]
    
    print(f"Dropping {len(tables)} tables:")
    for table in tables:
        print(f"Dropping table: {table}")
        
    Base.metadata.drop_all(
        connection,
        tables=[Base.metadata.tables[table] for table in tables]
    )
    print("All tables dropped successfully")