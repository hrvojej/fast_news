"""Create tables from SQLAlchemy models

Revision ID: 0003
Revises: 0002
Create Date: 2025-02-03 10:55:00

 Adjusted table order to resolve dependency issues.
"""

from alembic import op
from sqlalchemy import text
from db_scripts.models.models import Base, NewsPortal, create_portal_category_model, create_portal_article_model

revision = '0003'
down_revision = '0002'

def upgrade():
    # Create static tables first
    Base.metadata.create_all(op.get_bind(), tables=[
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

    # Get list of available portal schemas
    portal_schemas = op.get_bind().execute(
        text("SELECT nspname FROM pg_namespace WHERE nspname LIKE 'portal%';")
    ).fetchall()

    # Create dynamic category and article tables for each portal schema
    for schema in portal_schemas:
        portal_schema = schema[0]
        PortalCategory = create_portal_category_model(portal_schema)
        PortalArticle = create_portal_article_model(portal_schema)

        PortalCategory.__table__.create(op.get_bind(), checkfirst=True)
        op.create_index('idx_' + portal_schema + '_category_path',
                        PortalCategory.__table__.c.path,
                        postgresql_using='btree')

        PortalArticle.__table__.create(op.get_bind(), checkfirst=True)
        op.create_index('idx_' + portal_schema + '_articles_pub_date',
                        PortalArticle.__table__.c.pub_date)
        op.create_index('idx_' + portal_schema + '_articles_category',
                        PortalArticle.__table__.c.category_id)
        op.execute(
            text(f"CREATE INDEX ON {portal_schema}.articles USING GIN (to_tsvector('english', title || ' ' || description || ' ' || content))")
        )

def downgrade():
    # Drop dynamic tables first
    portal_schemas = op.get_bind().execute(
        text("SELECT nspname FROM pg_namespace WHERE nspname LIKE 'portal%';")
    ).fetchall()
    
    for schema in reversed(portal_schemas):
        portal_schema = schema[0]
        op.drop_table(portal_schema + '.articles')
        op.drop_table(portal_schema + '.categories')

    # Drop static tables
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
