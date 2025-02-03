#!/usr/bin/env python3
# path: news_dagster-etl/news_aggregator/db_scripts/models/models.py
"""
SQLAlchemy ORM models based on the PostgreSQL 16 schema.
Note:
  - All “created_at” and “updated_at” columns (and their triggers) have been removed.
  - Dynamic per‑portal tables (“categories” and “articles”) are provided via factory functions.
  - Other business rules (checks, foreign keys, indexes, partitioning notes, etc.) are included.
"""

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, Index, UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB, TIMESTAMP, TSVECTOR
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# ────────────────────────────────────────────── Public Schema ──────────────────────────────────────────────

class NewsPortal(Base):
    __tablename__ = 'news_portals'
    __table_args__ = (
        Index('idx_portal_status', 'active_status'),
        Index('idx_portal_prefix', 'portal_prefix'),
        {'schema': 'public'}
    )

    portal_id = sa.Column(UUID(as_uuid=True), primary_key=True,
                          server_default=sa.text("gen_random_uuid()"))
    portal_prefix = sa.Column(sa.String(50), nullable=False, unique=True)
    name = sa.Column(sa.String(255), nullable=False)
    base_url = sa.Column(sa.Text, nullable=False)
    rss_url = sa.Column(sa.Text)
    scraping_enabled = sa.Column(sa.Boolean, server_default=sa.text("true"))
    portal_language = sa.Column(sa.String(50))
    timezone = sa.Column(sa.String(50), server_default=sa.text("'UTC'"))
    active_status = sa.Column(sa.Boolean, server_default=sa.text("true"))
    scraping_frequency_minutes = sa.Column(sa.Integer, server_default=sa.text("60"))
    last_scraped_at = sa.Column(TIMESTAMP(timezone=True))


# ───────────────────────────────────── Dynamic Portal Models (Categories & Articles) ─────────────────────────────

def create_portal_category_model(schema: str):
    """
    Returns a Category model class for the given portal schema.
    (The underlying table is “categories” in the specified schema.)
    """
    class Category(Base):
        __tablename__ = 'categories'
        __table_args__ = (
            UniqueConstraint('slug', 'portal_id', name=f'uq_{schema}_categories_slug_portal_id'),
            Index(f'idx_{schema}_category_path', 'path', postgresql_using='btree'),
            Index(f'idx_{schema}_category_portal', 'portal_id'),
            {'schema': schema}
        )

        category_id = sa.Column(UUID(as_uuid=True), primary_key=True,
                                server_default=sa.text("gen_random_uuid()"))
        name = sa.Column(sa.String(255), nullable=False)
        slug = sa.Column(sa.String(255), nullable=False)
        # Although “portal_id” is a FK to public.news_portals, here we just define it as UUID.
        portal_id = sa.Column(UUID(as_uuid=True), nullable=False)
        # The “ltree” type is not built‐in; here we store it as TEXT (with the understanding that the DB uses ltree).
        path = sa.Column(sa.Text, nullable=False)
        level = sa.Column(sa.Integer, nullable=False)
        description = sa.Column(sa.Text)
        link = sa.Column(sa.Text)
        is_active = sa.Column(sa.Boolean, server_default=sa.text("true"))

    return Category


def create_portal_article_model(schema: str):
    """
    Returns an Article model class for the given portal schema.
    (The underlying table is “articles” in the specified schema.)
    """
    class Article(Base):
        __tablename__ = 'articles'
        __table_args__ = (
            Index(f'idx_{schema}_articles_pub_date', 'pub_date'),
            Index(f'idx_{schema}_articles_category', 'category_id'),
            # Note: The full‑text search index (using to_tsvector) is not represented here.
            {'schema': schema}
        )

        article_id = sa.Column(UUID(as_uuid=True), primary_key=True,
                               server_default=sa.text("gen_random_uuid()"))
        title = sa.Column(sa.Text, nullable=False)
        url = sa.Column(sa.Text, nullable=False)
        guid = sa.Column(sa.Text, unique=True)
        description = sa.Column(sa.Text)
        content = sa.Column(sa.Text)
        author = sa.Column(ARRAY(sa.Text))
        pub_date = sa.Column(TIMESTAMP(timezone=True))
        # FK reference: note that the referenced table is “categories” in the same schema.
        category_id = sa.Column(UUID(as_uuid=True),
                                sa.ForeignKey(f'{schema}.categories.category_id', ondelete='CASCADE'),
                                nullable=False)
        keywords = sa.Column(ARRAY(sa.Text))
        reading_time_minutes = sa.Column(sa.Integer)
        language_code = sa.Column(sa.String(10))
        image_url = sa.Column(sa.Text)
        sentiment_score = sa.Column(sa.Float, CheckConstraint('sentiment_score BETWEEN -1 AND 1'))
        share_count = sa.Column(sa.Integer, server_default=sa.text("0"))
        view_count = sa.Column(sa.Integer, server_default=sa.text("0"))
        comment_count = sa.Column(sa.Integer, server_default=sa.text("0"))

    return Article


# ────────────────────────────────────────────── Events Schema ───────────────────────────────────────────────

class Event(Base):
    __tablename__ = 'events'
    __table_args__ = (
        Index('idx_events_temporal', 'start_time', 'end_time'),
        Index('idx_events_status', 'status'),
        Index('idx_events_type', 'event_type'),
        {'schema': 'events'}
    )

    event_id = sa.Column(UUID(as_uuid=True), primary_key=True,
                         server_default=sa.text("gen_random_uuid()"))
    title = sa.Column(sa.Text, nullable=False)
    description = sa.Column(sa.Text)
    start_time = sa.Column(TIMESTAMP(timezone=True), nullable=False)
    end_time = sa.Column(TIMESTAMP(timezone=True))
    event_type = sa.Column(sa.String(50), nullable=False)
    importance_level = sa.Column(sa.Integer, CheckConstraint('importance_level BETWEEN 1 AND 5'))
    geographic_scope = sa.Column(sa.String(50))
    tags = sa.Column(ARRAY(sa.Text))
    sentiment_score = sa.Column(sa.Float, CheckConstraint('sentiment_score BETWEEN -1 AND 1'))
    status = sa.Column(sa.String(50), nullable=False, server_default=sa.text("'active'"))
    parent_event_id = sa.Column(UUID(as_uuid=True),
                                sa.ForeignKey('events.events.event_id', ondelete='CASCADE'))


class EventArticle(Base):
    __tablename__ = 'event_articles'
    __table_args__ = {'schema': 'events'}

    event_id = sa.Column(UUID(as_uuid=True),
                         sa.ForeignKey('events.events.event_id', ondelete='CASCADE'),
                         primary_key=True)
    article_id = sa.Column(UUID(as_uuid=True), primary_key=True,
                           server_default=sa.text("gen_random_uuid()"))
    portal_id = sa.Column(UUID(as_uuid=True),
                          sa.ForeignKey('public.news_portals.portal_id', ondelete='CASCADE'),
                          primary_key=True)
    similarity_score = sa.Column(sa.Float, CheckConstraint('similarity_score BETWEEN 0 AND 1'))
    context_summary = sa.Column(sa.Text)


class TimelineEntry(Base):
    __tablename__ = 'timeline_entries'
    __table_args__ = (
        PrimaryKeyConstraint('entry_id', 'entry_timestamp'),
        Index('idx_timeline_event', 'event_id'),
        {'schema': 'events'}
    )

    entry_id = sa.Column(UUID(as_uuid=True),
                         server_default=sa.text("gen_random_uuid()"))
    event_id = sa.Column(UUID(as_uuid=True),
                         sa.ForeignKey('events.events.event_id', ondelete='CASCADE'))
    article_id = sa.Column(UUID(as_uuid=True), nullable=False)
    portal_id = sa.Column(UUID(as_uuid=True),
                          sa.ForeignKey('public.news_portals.portal_id', ondelete='CASCADE'))
    entry_timestamp = sa.Column(TIMESTAMP(timezone=True), nullable=False)
    entry_type = sa.Column(sa.String(50), nullable=False)
    summary = sa.Column(sa.Text, nullable=False)
    impact_level = sa.Column(sa.Integer, CheckConstraint('impact_level BETWEEN 1 AND 5'))


# ────────────────────────────────────────────── Comments Schema ───────────────────────────────────────────────

class Comment(Base):
    __tablename__ = 'comments'
    __table_args__ = (
        Index('idx_comments_article', 'article_id', 'portal_id'),
        Index('idx_comments_hierarchy', 'parent_comment_id', 'root_comment_id'),
        Index('idx_comments_path', 'thread_path', postgresql_using='btree'),  
        Index('idx_comments_temporal', 'posted_at'),
        Index('idx_comments_author', 'author_id'),
        {'schema': 'comments'}
    )

    # Assuming “comment_id” is the primary key.
    comment_id = sa.Column(sa.Text, primary_key=True)
    article_id = sa.Column(UUID(as_uuid=True), nullable=False)
    portal_id = sa.Column(UUID(as_uuid=True),
                          sa.ForeignKey('public.news_portals.portal_id', ondelete='CASCADE'))
    content = sa.Column(sa.Text, nullable=False)
    content_html = sa.Column(sa.Text)
    author_id = sa.Column(sa.Text)
    author_name = sa.Column(sa.Text)
    parent_comment_id = sa.Column(sa.Text,
                                  sa.ForeignKey('comments.comments.comment_id', ondelete='CASCADE'))
    root_comment_id = sa.Column(sa.Text)
    reply_level = sa.Column(sa.Integer, server_default=sa.text("0"))
    thread_path = sa.Column(sa.Text)  # Stored as ltree in the DB.
    likes_count = sa.Column(sa.Integer, server_default=sa.text("0"))
    replies_count = sa.Column(sa.Integer, server_default=sa.text("0"))
    sentiment_score = sa.Column(sa.Float, CheckConstraint('sentiment_score BETWEEN -1 AND 1'))
    is_spam = sa.Column(sa.Boolean, server_default=sa.text("false"))
    posted_at = sa.Column(TIMESTAMP(timezone=True), nullable=False)


class ArticleCommentStats(Base):
    __tablename__ = 'article_comment_stats'
    __table_args__ = {'schema': 'comments'}

    article_id = sa.Column(UUID(as_uuid=True), primary_key=True)
    portal_id = sa.Column(UUID(as_uuid=True),
                          sa.ForeignKey('public.news_portals.portal_id', ondelete='CASCADE'),
                          primary_key=True)
    total_comments_count = sa.Column(sa.Integer, server_default=sa.text("0"))
    top_level_comments_count = sa.Column(sa.Integer, server_default=sa.text("0"))
    reply_comments_count = sa.Column(sa.Integer, server_default=sa.text("0"))
    total_likes_count = sa.Column(sa.Integer, server_default=sa.text("0"))
    overall_sentiment_score = sa.Column(sa.Float, CheckConstraint('overall_sentiment_score BETWEEN -1 AND 1'))
    last_comment_at = sa.Column(TIMESTAMP(timezone=True))


# ────────────────────────────────────────────── Topics Schema ───────────────────────────────────────────────

class TopicCategory(Base):
    __tablename__ = 'topic_categories'
    __table_args__ = {'schema': 'topics'}

    category_id = sa.Column(UUID(as_uuid=True), primary_key=True,
                            server_default=sa.text("gen_random_uuid()"))
    name = sa.Column(sa.String(255), nullable=False)
    slug = sa.Column(sa.String(255), nullable=False, unique=True)
    description = sa.Column(sa.Text)
    display_order = sa.Column(sa.Integer)
    status = sa.Column(sa.String(50), nullable=False, server_default=sa.text("'active'"))


class Topic(Base):
    __tablename__ = 'topics'
    __table_args__ = (
        UniqueConstraint('slug', 'path', name='uq_topics_slug_path'),
        CheckConstraint(
            "((parent_topic_id IS NULL AND level = 1) OR (parent_topic_id IS NOT NULL AND level > 1))",
            name="valid_hierarchy"
        ),
        {'schema': 'topics'}
    )

    topic_id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    category_id = sa.Column(UUID(as_uuid=True),
                            sa.ForeignKey('topics.topic_categories.category_id', ondelete='CASCADE'),
                            server_default=sa.text("gen_random_uuid()"))
    name = sa.Column(sa.String(255), nullable=False)
    slug = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.Text)
    parent_topic_id = sa.Column(sa.Integer,
                                sa.ForeignKey('topics.topics.topic_id'))
    path = sa.Column(sa.Text, nullable=False)  # ltree type stored as TEXT.
    level = sa.Column(sa.Integer, nullable=False)
    keywords = sa.Column(ARRAY(sa.Text))
    importance_score = sa.Column(sa.Float, CheckConstraint('importance_score BETWEEN 0 AND 1'))
    article_count = sa.Column(sa.Integer, server_default=sa.text("0"))
    status = sa.Column(sa.String(50), nullable=False, server_default=sa.text("'active'"))


class TopicContent(Base):
    __tablename__ = 'topic_content'
    __table_args__ = (
        UniqueConstraint('topic_id', 'content_type', 'content_id', name='uq_topic_content'),
        Index('idx_topic_content_type', 'content_type'),
        Index('idx_topic_content_relevance', 'relevance_score'),
        {'schema': 'topics'}
    )

    topic_id = sa.Column(sa.Integer,
                         sa.ForeignKey('topics.topics.topic_id', ondelete='CASCADE'),
                         primary_key=True)
    content_type = sa.Column(
        sa.String(50),
        nullable=False,
        info={'check': "content_type IN ('article', 'event', 'comment')"}
    )
    content_id = sa.Column(sa.Text, nullable=False, primary_key=True)
    portal_id = sa.Column(UUID(as_uuid=True),
                          sa.ForeignKey('public.news_portals.portal_id', ondelete='CASCADE'))
    relevance_score = sa.Column(sa.Float, CheckConstraint('relevance_score BETWEEN 0 AND 1'))


# ────────────────────────────────────────────── Analysis Schema ───────────────────────────────────────────────

class SentimentLexicon(Base):
    __tablename__ = 'sentiment_lexicon'
    __table_args__ = (
        UniqueConstraint('word', name='uq_sentiment_lexicon_word'),
        Index('idx_lexicon_word', 'word'),
        Index('idx_lexicon_language', 'language_code'),
        Index('idx_lexicon_score', 'base_score'),
        {'schema': 'analysis'}
    )

    word_id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    word = sa.Column(sa.String(255), nullable=False)
    language_code = sa.Column(sa.String(10), nullable=False, server_default=sa.text("'en'"))
    base_score = sa.Column(sa.Float, CheckConstraint('base_score BETWEEN -1 AND 1'), nullable=False)



class ContentAnalysis(Base):
    __tablename__ = 'content_analysis'
    __table_args__ = (
        UniqueConstraint('source_type', 'source_id', name='uq_content_analysis_source'),
        Index('idx_content_source', 'source_type', 'source_id'),
        Index('idx_content_sentiment', 'overall_sentiment_score'),
        Index('idx_content_temporal', 'analyzed_at'),
        {'schema': 'analysis'}
    )

    content_id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    source_type = sa.Column(
        sa.String(50),
        nullable=False,
        info={'check': "source_type IN ('article', 'comment', 'title', 'summary')"}
    )
    source_id = sa.Column(sa.Text, nullable=False)
    portal_id = sa.Column(UUID(as_uuid=True),
                          sa.ForeignKey('public.news_portals.portal_id', ondelete='CASCADE'))
    content_length = sa.Column(sa.Integer)
    language_code = sa.Column(sa.String(10))
    readability_score = sa.Column(sa.Float)
    overall_sentiment_score = sa.Column(sa.Float, CheckConstraint('overall_sentiment_score BETWEEN -1 AND 1'))
    extracted_keywords = sa.Column(ARRAY(sa.Text))
    main_topics = sa.Column(ARRAY(sa.Text))
    named_entities = sa.Column(JSONB)
    analyzed_at = sa.Column(TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"))


class ContentStatistics(Base):
    __tablename__ = 'content_statistics'
    __table_args__ = (
        UniqueConstraint('source_type', 'source_id', 'time_bucket', name='uq_content_statistics'),
        Index('idx_stats_temporal', 'time_bucket'),
        Index('idx_stats_source', 'source_type', 'source_id'),
        {'schema': 'analysis'}
    )

    stat_id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    source_type = sa.Column(sa.String(50), nullable=False)
    source_id = sa.Column(sa.Text, nullable=False)
    time_bucket = sa.Column(TIMESTAMP(timezone=True), nullable=False)
    word_count = sa.Column(sa.Integer)
    view_count = sa.Column(sa.Integer)
    completion_rate = sa.Column(sa.Float)
    keyword_density = sa.Column(JSONB)


# ────────────────────────────────────────────── Social Schema ───────────────────────────────────────────────

class Platform(Base):
    __tablename__ = 'platforms'
    __table_args__ = {'schema': 'social'}

    platform_id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(50), nullable=False, unique=True)
    enabled = sa.Column(sa.Boolean, server_default=sa.text("true"))
    api_version = sa.Column(sa.String(50))
    rate_limits = sa.Column(JSONB)
    auth_config = sa.Column(JSONB)


class Post(Base):
    __tablename__ = 'posts'
    __table_args__ = (
        Index('idx_posts_article', 'article_id', 'portal_id'),
        Index('idx_posts_platform', 'platform_id', 'posted_at'),
        Index('idx_posts_temporal', 'posted_at'),
        Index('idx_posts_author', 'author_platform_id'),
        {'schema': 'social'}
    )

    post_id = sa.Column(sa.Text, primary_key=True)
    platform_id = sa.Column(sa.Integer,
                            sa.ForeignKey('social.platforms.platform_id', ondelete='CASCADE'))
    article_id = sa.Column(UUID(as_uuid=True), nullable=False)
    portal_id = sa.Column(UUID(as_uuid=True),
                          sa.ForeignKey('public.news_portals.portal_id', ondelete='CASCADE'))
    content = sa.Column(sa.Text, nullable=False)
    content_type = sa.Column(
        sa.String(50),
        info={'check': "content_type IN ('text', 'image', 'video', 'link', 'mixed')"}
    )
    language_code = sa.Column(sa.String(10))
    urls = sa.Column(ARRAY(sa.Text))
    author_platform_id = sa.Column(sa.Text)
    author_username = sa.Column(sa.Text)
    likes_count = sa.Column(sa.Integer, server_default=sa.text("0"))
    shares_count = sa.Column(sa.Integer, server_default=sa.text("0"))
    replies_count = sa.Column(sa.Integer, server_default=sa.text("0"))
    sentiment_score = sa.Column(sa.Float, CheckConstraint('sentiment_score BETWEEN -1 AND 1'))
    posted_at = sa.Column(TIMESTAMP(timezone=True), nullable=False)


class ArticleSocialMetrics(Base):
    __tablename__ = 'article_social_metrics'
    __table_args__ = (
        PrimaryKeyConstraint('article_id', 'portal_id', 'platform_id'),
        Index('idx_metrics_temporal', 'last_activity_at'),
        {'schema': 'social'}
    )

    article_id = sa.Column(UUID(as_uuid=True), nullable=False)
    portal_id = sa.Column(UUID(as_uuid=True),
                          sa.ForeignKey('public.news_portals.portal_id', ondelete='CASCADE'),
                          nullable=False)
    platform_id = sa.Column(sa.Integer,
                            sa.ForeignKey('social.platforms.platform_id', ondelete='CASCADE'),
                            nullable=False)
    total_posts_count = sa.Column(sa.Integer, server_default=sa.text("0"))
    total_likes_count = sa.Column(sa.Integer, server_default=sa.text("0"))
    total_shares_count = sa.Column(sa.Integer, server_default=sa.text("0"))
    total_replies_count = sa.Column(sa.Integer, server_default=sa.text("0"))
    overall_sentiment_score = sa.Column(sa.Float, CheckConstraint('overall_sentiment_score BETWEEN -1 AND 1'))
    first_posted_at = sa.Column(TIMESTAMP(timezone=True))
    last_activity_at = sa.Column(TIMESTAMP(timezone=True))


# ────────────────────────────────────────────── Entities Schema ───────────────────────────────────────────────

class Entity(Base):
    __tablename__ = 'entities'
    __table_args__ = (
        UniqueConstraint('normalized_name', 'entity_type', name='uq_entities_normalized_name_type'),
        Index('idx_entities_type', 'entity_type'),
        Index('idx_entities_status', 'status'),
        Index('idx_entities_normalized_name', 'normalized_name'),
        Index('idx_entities_temporal', 'last_seen_at'),
                {'schema': 'entities'}
    )

    entity_id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(255), nullable=False)
    normalized_name = sa.Column(sa.String(255), nullable=False)
    entity_type = sa.Column(
        sa.String(50),
        nullable=False,
        info={'check': "entity_type IN ('person', 'organization', 'location', 'product', 'event', 'concept')"}
    )
    status = sa.Column(
        sa.String(50),
        nullable=False,
        server_default=sa.text("'active'"),
        info={'check': "status IN ('active', 'inactive', 'merged', 'archived')"}
    )
    description = sa.Column(sa.Text)
    aliases = sa.Column(ARRAY(sa.Text))
    importance_score = sa.Column(sa.Float, CheckConstraint('importance_score BETWEEN 0 AND 1'))
    sentiment_score = sa.Column(sa.Float, CheckConstraint('sentiment_score BETWEEN -1 AND 1'))
    mention_count = sa.Column(sa.Integer, server_default=sa.text("0"))
    first_seen_at = sa.Column(TIMESTAMP(timezone=True))
    last_seen_at = sa.Column(TIMESTAMP(timezone=True))
    search_vector = sa.Column(TSVECTOR)


class EntityRelationship(Base):
    __tablename__ = 'entity_relationships'
    __table_args__ = (
        PrimaryKeyConstraint('source_entity_id', 'target_entity_id', 'relationship_type'),
        CheckConstraint('source_entity_id <> target_entity_id', name='chk_no_self_relationship'),
        Index('idx_entity_relationships_type', 'relationship_type'),
        {'schema': 'entities'}
    )

    source_entity_id = sa.Column(sa.Integer,
                                 sa.ForeignKey('entities.entities.entity_id', ondelete='CASCADE'),
                                 nullable=False)
    target_entity_id = sa.Column(sa.Integer,
                                 sa.ForeignKey('entities.entities.entity_id', ondelete='CASCADE'),
                                 nullable=False)
    relationship_type = sa.Column(
        sa.String(50),
        nullable=False,
        info={'check': "relationship_type IN ('parent_of', 'child_of', 'related_to', 'member_of', 'located_in')"}
    )
    strength = sa.Column(sa.Float, CheckConstraint('strength BETWEEN 0 AND 1'))


class EntityMention(Base):
    __tablename__ = 'entity_mentions'
    __table_args__ = (
        UniqueConstraint('entity_id', 'content_type', 'content_id', name='uq_entity_mentions'),
        Index('idx_entity_mentions_content', 'content_type', 'content_id'),
        {'schema': 'entities'}
    )

    mention_id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    entity_id = sa.Column(sa.Integer,
                          sa.ForeignKey('entities.entities.entity_id', ondelete='CASCADE'),
                          nullable=False)
    content_type = sa.Column(
        sa.String(50),
        nullable=False,
        info={'check': "content_type IN ('article', 'comment')"}
    )
    content_id = sa.Column(sa.Text, nullable=False)
    portal_id = sa.Column(UUID(as_uuid=True),
                          sa.ForeignKey('public.news_portals.portal_id', ondelete='CASCADE'))
    context_snippet = sa.Column(sa.Text)
    sentiment_score = sa.Column(sa.Float, CheckConstraint('sentiment_score BETWEEN -1 AND 1'))


# ────────────────────────────────────────────── Engine Setup Example ─────────────────────────────────────────────

if __name__ == '__main__':
    # Example: create an engine and create all tables (if needed)
    engine = sa.create_engine("postgresql+psycopg2://user:password@localhost:5432/your_database")
    
    Base.metadata.create_all(engine)

    # Example: instantiate dynamic models for a given portal schema (e.g. "portal1")
    Portal1Category = create_portal_category_model("portal1")
    Portal1Article = create_portal_article_model("portal1")
    # Now you can use Portal1Category and Portal1Article as normal ORM classes.
