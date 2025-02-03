"""Create tables from SQLAlchemy models

Revision ID: 0003
Revises: 0002
Create Date: 2025-02-03 10:55:00

 Adjusted table order to resolve dependency issues.
"""

from alembic import op
from sqlalchemy import text
from db_scripts.models.models import Base, NewsPortal # Import your Base and any relevant models

revision = '0003'
down_revision = '0002'

def upgrade():
    # Use SQLAlchemy metadata to create tables
    Base.metadata.create_all(op.get_bind(), tables=[
        # Specify tables to create in correct dependency order
        Base.metadata.tables['topics.topic_categories'],
        Base.metadata.tables['topics.topics'],
        Base.metadata.tables['topics.topic_content'],
        Base.metadata.tables['events.events'],
        Base.metadata.tables['events.event_articles'],
        Base.metadata.tables['comments.comments'],
        Base.metadata.tables['analysis.content_analysis'],
        Base.metadata.tables['social.platforms'],
        Base.metadata.tables['social.posts'],
        Base.metadata.tables['entities.entities'],
        Base.metadata.tables['entities.entity_relationships'],
        Base.metadata.tables['entities.entity_mentions'],
        Base.metadata.tables['events.timeline_entries'], 
    ])

def downgrade():
    # Use SQLAlchemy metadata to drop tables in reverse order
    Base.metadata.drop_all(op.get_bind(), tables=[
        Base.metadata.tables['social.platforms'],
        Base.metadata.tables['events.timeline_entries'],
        Base.metadata.tables['entities.entity_mentions'],
        Base.metadata.tables['entities.entity_relationships'],
        Base.metadata.tables['entities.entities'],
        Base.metadata.tables['social.posts'],
        Base.metadata.tables['analysis.content_analysis'],
        Base.metadata.tables['topics.topic_content'],
        Base.metadata.tables['topics.topics'],
        Base.metadata.tables['comments.comments'],
        Base.metadata.tables['events.event_articles'],
    ])
