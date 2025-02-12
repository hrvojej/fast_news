Currently, I am filling in articles table in database with this script:

"""
ABC RSS Articles Parser
Fetches and stores ABC RSS feed articles using SQLAlchemy ORM.
"""

import sys
import os
from datetime import datetime
from typing import Dict, List
from uuid import UUID
import requests
from bs4 import BeautifulSoup
import argparse
from sqlalchemy import text

# New imports for keyword extraction:
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
import nltk

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Import the dynamic model factory functions for categories and articles
from db_scripts.models.models import create_portal_category_model, create_portal_article_model

# Create the dynamic models for the ABC portal (portal prefix: pt_abc)
ABCCategory = create_portal_category_model("pt_abc")
ABCArticle = create_portal_article_model("pt_abc")


def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
    """Fetches the portal_id from the news_portals table."""
    from db_scripts.db_context import DatabaseContext
    db_context = DatabaseContext.get_instance(env)
    with db_context.session() as session:
        result = session.execute(
            text("SELECT portal_id FROM public.news_portals WHERE portal_prefix = :prefix"),
            {'prefix': portal_prefix}
        ).fetchone()
        if result:
            return result[0]
        raise Exception(f"Portal with prefix '{portal_prefix}' not found.")


class KeywordExtractor:
    """
    Uses a SentenceTransformer model to extract keywords from text.
    """
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        try:
            self.stop_words = set(stopwords.words('english'))
        except LookupError:
            nltk.download('stopwords')
            self.stop_words = set(stopwords.words('english'))
            
    def extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        if not text:
            return []
        
        # Split text into individual words (chunks)
        chunks = text.split()
        if not chunks:
            return []
            
        text_embedding = self.model.encode([text])
        chunk_embeddings = self.model.encode(chunks)
        
        similarities = cosine_similarity(text_embedding, chunk_embeddings).flatten()
        scored_chunks = sorted(
            [(chunks[i], score) for i, score in enumerate(similarities)],
            key=lambda x: x[1],
            reverse=True
        )
        
        keywords = []
        seen = set()
        for word, _ in scored_chunks:
            word = word.lower()
            if word not in self.stop_words and word not in seen and len(word) > 2:
                keywords.append(word)
                seen.add(word)
            if len(keywords) >= max_keywords:
                break
        return keywords


class ABCRSSArticlesParser:
    """Parser for ABC RSS feed articles."""

    def __init__(self, portal_id: UUID, env: str = 'dev', article_model=None):
        self.portal_id = portal_id
        self.env = env
        self.ABCArticle = article_model
        # Instantiate the keyword extractor (SentenceTransformer based)
        self.keyword_extractor = KeywordExtractor()

    def get_session(self):
        """Obtain a database session from the DatabaseContext."""
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        return db_context.session().__enter__()

    def parse_article(self, item: BeautifulSoup, category_id: UUID) -> Dict:
        """Parse a single ABC RSS <item> element."""
        # Required fields
        title_tag = item.find('title')
        title = title_tag.text.strip() if title_tag else 'Untitled'

        link_tag = item.find('link')
        link = link_tag.text.strip() if link_tag else 'https://abcnews.go.com'

        guid_tag = item.find('guid')
        guid = guid_tag.text.strip() if guid_tag else link  # Use link as fallback GUID

        # Optional fields
        description_tag = item.find('description')
        description = description_tag.text.strip() if description_tag else None

        # In this case, we use description as a fallback for content
        content = description

        # Process pubDate: if not present, leave as None (do not insert current timestamp)
        pub_date_tag = item.find('pubDate')
        pub_date = None
        if pub_date_tag:
            pub_date_str = pub_date_tag.text.strip()
            try:
                pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
            except Exception as e:
                print(f"Error parsing pubDate '{pub_date_str}': {e}")
                pub_date = None

        # Authors: ABC feed does not provide an explicit author field, so we leave it empty.
        authors = []

        # ----------------------------
        # NEW: Keyword extraction
        # Instead of relying solely on <category> or media:keywords tags,
        # we now extract keywords from the title using our KeywordExtractor.
        keywords = self.keyword_extractor.extract_keywords(title) if title else []
        # ----------------------------

        # Get image URL from <media:thumbnail> elements.
        image_url = None
        media_thumbnails = item.find_all('media:thumbnail')
        if media_thumbnails:
            valid_thumbnails = []
            for thumb in media_thumbnails:
                url = thumb.get('url')
                width = thumb.get('width')
                if url and width and width.isdigit():
                    valid_thumbnails.append((url, int(width)))
            if valid_thumbnails:
                image_url = max(valid_thumbnails, key=lambda x: x[1])[0]

        # Calculate reading time (estimate: 200 words per minute)
        text_content = f"{title} {description or ''} {content or ''}"
        word_count = len(text_content.split())
        reading_time = max(1, round(word_count / 200)) if word_count > 0 else 1

        return {
            # Required fields
            'title': title,
            'url': link,
            'guid': guid,
            'category_id': category_id,

            # Optional fields
            'description': description,
            'content': content,
            'author': authors,
            'pub_date': pub_date,
            'keywords': keywords,
            'reading_time_minutes': reading_time,
            'language_code': 'en',
            'image_url': image_url,
            'sentiment_score': 0.0,  # Neutral sentiment by default
            'share_count': 0,
            'view_count': 0,
            'comment_count': 0
        }

    def fetch_and_store_articles(self):
        """Fetch and store articles from all ABC RSS feeds."""
        print("Starting fetch_and_store_articles for ABC...")
        session = self.get_session()
        print("Executing categories query...")
        try:
            # Select all active categories that have an atom_link defined
            categories = session.execute(
                text("""
                    SELECT category_id, atom_link 
                    FROM pt_abc.categories 
                    WHERE is_active = true AND atom_link IS NOT NULL
                """)
            ).fetchall()
            print(f"Found {len(categories)} categories.")

            for category_id, atom_link in categories:
                print(f"Processing category: {category_id} with feed URL: {atom_link}")
                try:
                    response = requests.get(atom_link, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'xml')

                    for item in soup.find_all('item'):
                        article_data = self.parse_article(item, category_id)
                        # Check for duplicate based on guid
                        existing = session.query(self.ABCArticle).filter(
                            self.ABCArticle.guid == article_data['guid']
                        ).first()

                        if not existing:
                            article = self.ABCArticle(**article_data)
                            session.add(article)
                            print(f"Added new article: {article_data['title']}")
                        else:
                            # If needed, update the existing record (e.g., if pub_date has changed)
                            if existing.pub_date != article_data['pub_date']:
                                for key, value in article_data.items():
                                    setattr(existing, key, value)
                                print(f"Updated article: {article_data['title']}")

                    session.commit()
                    print(f"Finished processing feed: {atom_link}")

                except Exception as e:
                    print(f"Error processing feed {atom_link}: {e}")
                    session.rollback()
                    continue

        except Exception as e:
            print(f"Error in fetch_and_store_articles: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def run(self):
        """Main method to fetch and store ABC articles."""
        try:
            self.fetch_and_store_articles()
            print("ABC article processing completed successfully.")
        except Exception as e:
            print(f"Error processing ABC articles: {e}")
            raise


def main():
    """Script entry point."""
    argparser = argparse.ArgumentParser(description="ABC RSS Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    try:
        portal_id = fetch_portal_id_by_prefix("pt_abc", env=args.env)
        parser = ABCRSSArticlesParser(portal_id=portal_id, env=args.env, article_model=ABCArticle)
        parser.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()


# Model file don't forget to use new model - create_portal_article_status_model ###########
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
    return type(
        f'Category_{schema}',
        (Base,),
        {
            '__tablename__': 'categories',
            '__table_args__': (
                UniqueConstraint('slug', 'portal_id', name=f'uq_{schema}_categories_slug_portal_id'),
                Index(f'idx_{schema}_category_path', 'path', postgresql_using='btree'),
                Index(f'idx_{schema}_category_portal', 'portal_id'),
                {'schema': schema}
            ),
            'category_id': sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            'name': sa.Column(sa.String(255), nullable=False),
            'slug': sa.Column(sa.String(255), nullable=False),
            'portal_id': sa.Column(UUID(as_uuid=True), nullable=False),
            'path': sa.Column(sa.Text, nullable=False),
            'level': sa.Column(sa.Integer, nullable=False),
            'description': sa.Column(sa.Text),
            'link': sa.Column(sa.Text),
            'atom_link': sa.Column(sa.Text),
            'is_active': sa.Column(sa.Boolean, server_default=sa.text("true"))
        }
    )

def create_portal_article_model(schema: str):
    return type(
        f'Article_{schema}',
        (Base,),
        {
            '__tablename__': 'articles',
           '__table_args__': (
                Index(f'idx_{schema}_articles_pub_date', 'pub_date'),
                Index(f'idx_{schema}_articles_category', 'category_id'),
                sa.ForeignKeyConstraint(
                    ['category_id'], 
                    [f'{schema}.categories.category_id'],
                    name=f'fk_{schema}_article_category'
                ),
                {'schema': schema}
            ),
            'article_id': sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            'title': sa.Column(sa.Text, nullable=False),
            'url': sa.Column(sa.Text, nullable=False),
            'guid': sa.Column(sa.Text, unique=True),
            'description': sa.Column(sa.Text),
            'content': sa.Column(sa.Text),
            'author': sa.Column(ARRAY(sa.Text)),
            'pub_date': sa.Column(TIMESTAMP(timezone=True)),            
            'category_id': sa.Column(UUID(as_uuid=True), nullable=False),            
            'keywords': sa.Column(ARRAY(sa.Text)),
            'reading_time_minutes': sa.Column(sa.Integer),
            'language_code': sa.Column(sa.String(10)),
            'image_url': sa.Column(sa.Text),
            'sentiment_score': sa.Column(sa.Float, CheckConstraint('sentiment_score BETWEEN -1 AND 1')),
            'share_count': sa.Column(sa.Integer, server_default=sa.text("0")),
            'view_count': sa.Column(sa.Integer, server_default=sa.text("0")),
            'comment_count': sa.Column(sa.Integer, server_default=sa.text("0"))
        }
    )
    
# ────────────────────────────────────────────── Dynamic Portal Model (Article Status) ───────────────────────────────────────────────

def create_portal_article_status_model(schema: str):
    return type(
        f'ArticleStatus_{schema}',
        (Base,),
        {
            '__tablename__': 'article_status',
            '__table_args__': (
                Index(f'idx_{schema}_article_status_url', 'url'),
                {'schema': schema}
            ),
            # Primary key (UUID for consistency with your other models)
            'status_id': sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            # Article URL to be tracked; uniqueness ensures that you don’t re‑fetch the same URL
            'url': sa.Column(sa.Text, nullable=False, unique=True),
            # Timestamp when the HTML was successfully fetched
            'fetched_at': sa.Column(TIMESTAMP(timezone=True), nullable=False),
            # Optionally, record when the article has been parsed.
            # If this remains NULL then the article’s content is not yet processed.
            'parsed_at': sa.Column(TIMESTAMP(timezone=True)),
            # New field to track publication date, similar to the articles table.
            'pub_date': sa.Column(TIMESTAMP(timezone=True))
        }
    )



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

#### Rules for processing

Now I  need new script, which uses similar elements like above script (db connection, same model etc..) that will overwrite current content of "content" field in table pt_abc.articles and replace it with content fetched from HTML page which should be fetched from "link" field. 

# Procedure on how to define what links should be fetched

Compar that list with what is already fetched and parsed  which is stored in status table for each schema - those urls should be skipped:

CREATE TABLE IF NOT EXISTS pt_abc.article_status
(
    status_id uuid NOT NULL DEFAULT gen_random_uuid(),
    url text COLLATE pg_catalog."default" NOT NULL,
    fetched_at timestamp with time zone NOT NULL,
    parsed_at timestamp with time zone,
    pub_date timestamp with time zone,
    CONSTRAINT article_status_pkey PRIMARY KEY (status_id),
    CONSTRAINT article_status_url_key UNIQUE (url)
)


And this is articles table:
-- Table: pt_abc.articles

-- DROP TABLE IF EXISTS pt_abc.articles;

CREATE TABLE IF NOT EXISTS pt_abc.articles
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
    CONSTRAINT articles_pkey PRIMARY KEY (article_id),
    CONSTRAINT articles_guid_key UNIQUE (guid),
    CONSTRAINT fk_pt_abc_article_category FOREIGN KEY (category_id)
        REFERENCES pt_abc.categories (category_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT articles_sentiment_score_check CHECK (sentiment_score >= '-1'::integer::double precision AND sentiment_score <= 1::double precision)
)

So, Script needs to select urls in 
SELECT url, pub_date FROM pt_abc.articles;
And than from
SELECT status_id, url, pub_date, fetched_at, parsed_at FROM pt_abc.article_status;

If url and pub_date is same in both tables and fetched_at and parsed_at exist - do nothing.
If url and pub_date is same in both table but fetched_at does not exits or parsed_at does not exists -  fetch and parse table again (add url in list for parsing).
If url exists but pub_date is different -  fetch and parse table again (add url in list for parsing).
Initially article_status is empty. Generally - if there is no record for link in article_status that means that link needs to be fetched. 


for each url that needs to be fetched and parsed; open url page, find content which is in:

<div class="xvlfx ZRifP TKoO eaKKC EcdEg bOdfO qXhdi NFNeu UyHES " data-testid="prism-article-body"><p class="EkqkG IGXmU nlgHS yuUao MvWXB TjIXL aGjvy ebVHC "><span class="oyrPY qlwaB AGxeB  ">NEW ORLEANS -- </span>As a student, <a class="zZygg UbGlr iFzkS qdXbA WCDhQ DbOXS tqUtK GpWVU iJYzE " data-testid="prism-linkbase" href="https://apnews.com/hub/donald-trump">Donald Trump</a> played high school football. As a business baron, he <a class="zZygg UbGlr iFzkS qdXbA WCDhQ DbOXS tqUtK GpWVU iJYzE " data-testid="prism-linkbase" href="https://apnews.com/events-united-states-presidential-election-dbbed546a30048798c3377c66cd50f4f">owned a team</a> in an upstart rival to the NFL and then sued the established league. As president, he <a class="zZygg UbGlr iFzkS qdXbA WCDhQ DbOXS tqUtK GpWVU iJYzE " data-testid="prism-linkbase" href="https://apnews.com/article/7e3fcc1d5c2446098652affae9e6322a">denigrated pros</a> who took a knee during the national anthem as part of a social justice movement.</p><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">He added to that complicated history with the sport on Sunday by becoming the <a class="zZygg UbGlr iFzkS qdXbA WCDhQ DbOXS tqUtK GpWVU iJYzE " data-testid="prism-linkbase" href="https://apnews.com/article/trump-attends-super-bowl-ae879e4f0a905b103e9059245f2887e2">first president in office to attend a Super Bowl.</a></p><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">After flying from Florida to New Orleans, the Republican president met with participants in the honorary coin toss after he arrived at the Superdome, including relatives of victims of a deadly <a class="zZygg UbGlr iFzkS qdXbA WCDhQ DbOXS tqUtK GpWVU iJYzE " data-testid="prism-linkbase" href="https://apnews.com/article/new-orleans-car-bourbon-street-63a1b43d615af365cb8ba6f5f0583eca">New Year’s Day terrorist attack</a> in the historic French Quarter, members of the police department and emergency personnel.</p><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">Trump’s appearance at the Caesars Superdome to see the two-time defending champion Kansas City Chiefs take on the Philadelphia Eagles follows the NFL’s decision to <a class="zZygg UbGlr iFzkS qdXbA WCDhQ DbOXS tqUtK GpWVU iJYzE " data-testid="prism-linkbase" href="https://apnews.com/article/super-bowl-end-zone-message-2cd0272f27fd1836ddd016eb2ff297f2">remove the “End Racism” slogans</a> that have been stenciled on the end zones since 2021. </p><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">Trump recently ordered the cancellation of programs that encourage <a class="zZygg UbGlr iFzkS qdXbA WCDhQ DbOXS tqUtK GpWVU iJYzE " data-testid="prism-linkbase" href="https://apnews.com/article/trump-dei-executive-order-diversity-inclusion-f67ea86032986084dd71c5aa0c6b8d1d">diversity, equity and inclusion</a> across the federal government and some critics see the league's decision as a response to the Republican president's action. But NFL Commissioner Roger Goodell said the league's <a class="zZygg UbGlr iFzkS qdXbA WCDhQ DbOXS tqUtK GpWVU iJYzE " data-testid="prism-linkbase" href="https://apnews.com/article/super-bowl-goodell-dei-bfd90306b728a28fdef43fabfb882e75">diversity policies</a> are not in conflict with the Trump administration’s efforts to end the federal government's DEI programs.</p><div class="oLzSq QrHMO GbsKS pvsTF EhJPu vPlOC zNYgW OsTsW AMhAA daRVX ISNQ sKyCY eRftA acPPc ebfE nFwaT MCnQE mEeeY SmBjI xegrY VvTxJ iulOd NIuqO zzscu lzDCc aHUBM hbvnu OjMNy eQqcx SVqKB GQmdz jaoD iShaE ONJdw vrZxD OnRTz gbbfF roDbV kRoBe oMlSS gfNzt oJhud eXZcf zhVlX "><div data-testid="prism-ad-wrapper" style="transition: min-height 0.3s linear 1s; min-height: 0px;" data-ad-placeholder="true"><div data-box-type="fitt-adbox-fitt-article-inline-outstream" data-testid="prism-ad"><div class="Ad fitt-article-inline-outstream  ad-slot  " data-slot-type="fitt-article-inline-outstream" data-slot-kvps="pos=fitt-article-inline-outstream-1"></div></div></div></div><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">Trump, who attended the Super Bowl in 1992, thinks the Chiefs will win, with Kansas City quarterback Patrick Mahomes the difference-maker.</p><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">“I guess you have to say that when a quarterback wins as much as he’s won, I have to go with Kansas City,” Trump said in a taped interview with Fox News Channel's Bret Baier that aired during the pregame show. Trump said Mahomes “really knows how to win. He’s a great, great quarterback.”</p><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">The president played football as a student at the New York Military Academy. As a New York businessman in the early 1980s, he <a class="zZygg UbGlr iFzkS qdXbA WCDhQ DbOXS tqUtK GpWVU iJYzE " data-testid="prism-linkbase" href="https://apnews.com/events-united-states-presidential-election-dbbed546a30048798c3377c66cd50f4f">owned the New Jersey Generals</a> of the United States Football League. Trump had sued to force a merger of the USFL and the NFL. The USFL eventually folded. </p><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">Friction existed between Trump and the NFL during his first term as president.</p><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy "><a class="zZygg UbGlr iFzkS qdXbA WCDhQ DbOXS tqUtK GpWVU iJYzE " data-testid="prism-linkbase" href="https://apnews.com/article/7e3fcc1d5c2446098652affae9e6322a">Trump took issue with players kneeling</a> during the national anthem to protest social or racial injustice. That movement began in 2016 with then-San Francisco 49ers quarterback Colin Kaepernick taking a knee during “The Star-Spangled Banner” during an exhibition game in Denver.</p><div class="oLzSq QrHMO GbsKS pvsTF EhJPu vPlOC zNYgW OsTsW AMhAA daRVX ISNQ sKyCY eRftA acPPc ebfE nFwaT MCnQE mEeeY SmBjI xegrY VvTxJ iulOd NIuqO zzscu lzDCc aHUBM hbvnu OjMNy eQqcx SVqKB GQmdz jaoD iShaE ONJdw vrZxD OnRTz gbbfF roDbV kRoBe oMlSS gfNzt oJhud eXZcf zhVlX "><div data-testid="prism-ad-wrapper" style="min-height:250px;transition:min-height 0.3s linear 0s" data-ad-placeholder="true"><div data-box-type="fitt-adbox-fitt-article-inline-box" data-testid="prism-ad"><div class="Ad fitt-article-inline-box  ad-slot  " data-slot-type="fitt-article-inline-box" data-slot-kvps="pos=fitt-article-inline-box"></div></div></div></div><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">Trump, through social media and other public comments, insisted that players stand for the national anthem and he called on team owners to fire anyone who took a knee. </p><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">“Wouldn’t you love to see one of these NFL owners, when somebody disrespects our flag, you’d say, ’Get that son of a bitch off the field right now. Out! He’s fired,'” Trump said to loud applause at a rally in Hunstville, Alabama, in 2017. </p><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">Trump watched Sunday's game from a suite after flying in with a group of some of his closest Republican allies in Congress, including Sens. Lindsey Graham and Tim Scott of South Carolina. House Speaker Mike Johnson, R-La., had said he'd also be in the suite with the president. Trump saluted when the national anthem was sung. Mahomes' family stopped by to visit with him. </p><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">His interest in sports extends beyond football. Trump is an avid golfer who owns multiple golf courses and has hosted tournaments. He sponsored boxing matches at his former casinos in Atlantic City, New Jersey, and <a class="zZygg UbGlr iFzkS qdXbA WCDhQ DbOXS tqUtK GpWVU iJYzE " data-testid="prism-linkbase" href="https://apnews.com/article/trump-ufc-match-new-york-8d5bfbccd32c1115cf2f6b54b8c58a0e">attended a UFC match</a> at Madison Square Garden weeks after winning a second term. </p><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">Trump played golf with Tiger Woods on Sunday in Florida, the White House said.</p><div class="oLzSq QrHMO GbsKS pvsTF EhJPu vPlOC zNYgW OsTsW AMhAA daRVX ISNQ sKyCY eRftA acPPc ebfE nFwaT MCnQE mEeeY SmBjI xegrY VvTxJ iulOd NIuqO zzscu lzDCc aHUBM hbvnu OjMNy eQqcx SVqKB GQmdz jaoD iShaE ONJdw vrZxD OnRTz gbbfF roDbV kRoBe oMlSS gfNzt oJhud eXZcf zhVlX "><div data-testid="prism-ad-wrapper" style="transition: min-height 0.3s linear 1s; min-height: 0px;" data-ad-placeholder="true"><div data-box-type="fitt-adbox-fitt-article-inline-outstream" data-testid="prism-ad"><div class="Ad fitt-article-inline-outstream  ad-slot  " data-slot-type="fitt-article-inline-outstream" data-slot-kvps="pos=fitt-article-inline-outstream-2"></div></div></div></div><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">Some NFL team owners have donated to his campaigns and Trump maintains friendships with Herschel Walker and Doug Flutie, who played for the Generals. <a class="zZygg UbGlr iFzkS qdXbA WCDhQ DbOXS tqUtK GpWVU iJYzE " data-testid="prism-linkbase" href="https://apnews.com/article/sports-college-football-georgia-senate-elections-herschel-walker-068e1edc1dbf75638a75c35bdc54eb33">Trump endorsed Walker's unsuccessful bid</a> as the Republican candidate for a U.S. Senate seat from Georgia in 2022, and has tapped him to become <a class="zZygg UbGlr iFzkS qdXbA WCDhQ DbOXS tqUtK GpWVU iJYzE " data-testid="prism-linkbase" href="https://apnews.com/article/herschel-walker-donald-trump-bahamas-92937a9d0b5409b0c91a22082e80d6a2">ambassador to the Bahamas</a>. </p><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">Trump signed an order last week that is intended to <a class="zZygg UbGlr iFzkS qdXbA WCDhQ DbOXS tqUtK GpWVU iJYzE " data-testid="prism-linkbase" href="https://apnews.com/article/donald-trump-transgender-athletes-3606411fc12efffec95a893351624e1b">block transgender women and girls from competing in women's sports</a> by targeting federal funding for schools that fail to comply.</p><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">In a statement before the game, Trump said the coaches, players and staff for the Chiefs and Eagles “represent the hopes and dreams of our Nation’s young athletes as we restore safety and fairness in sports and equal opportunities among their teams.”</p><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">Alvin Tillery, a politics professor and diversity expert at Northwestern University, said in an interview that the NFL's decision to remove “End Racism” slogans was “shameful” given that the league “makes tens of billions of dollars largely on the bodies of Black men.” </p><p class="EkqkG IGXmU nlgHS yuUao lqtkC TjIXL aGjvy ">He said the NFL should explain who it was aiming to please. The NFL said it was stenciling “Choose Love” in one of the end zones for the Super Bowl to encourage the country after a series of tragedies so far this year, including a New Year's Day truck attack in the host city of New Orleans that killed 14 people and injured dozens more. </p><div class="oLzSq QrHMO GbsKS pvsTF EhJPu vPlOC zNYgW OsTsW AMhAA daRVX ISNQ sKyCY eRftA acPPc ebfE nFwaT MCnQE mEeeY SmBjI xegrY VvTxJ iulOd NIuqO zzscu lzDCc aHUBM hbvnu OjMNy eQqcx SVqKB GQmdz jaoD iShaE ONJdw vrZxD OnRTz gbbfF roDbV kRoBe oMlSS gfNzt oJhud eXZcf zhVlX "><div data-testid="prism-ad-wrapper" style="transition: min-height 0.3s linear 1s; min-height: 0px;" data-ad-placeholder="true"><div data-box-type="fitt-adbox-fitt-article-inline-outstream" data-testid="prism-ad"><div class="Ad fitt-article-inline-outstream  ad-slot  " data-slot-type="fitt-article-inline-outstream" data-slot-kvps="pos=fitt-article-inline-outstream-3"></div></div></div></div><p class="EkqkG IGXmU nlgHS yuUao lqtkC eTIW sUzSN ">Tillery wasn't convinced. “I think they removed it because Trump's coming," he said.</p></div>

take out just text , remove all other html, css and js code. 

use that text to replace what is currenlty in "content" field:
SELECT content FROM pt_abc.articles
If you have any questions ask- do not assume.

Make sure you add some normal random time sleep between attempts to get HTML of the url. 
maybe 4-7 seconds. 

In case something is not clear you need to ask, do not assume. 

================================================================0
I’d like to clarify a few points before I produce the final script:

Updating the Status Table:

When a URL needs to be fetched (because there’s no matching record in article_status or the existing record has a different pub_date or is missing either fetched_at or parsed_at), should the script update or insert a record in the pt_abc.article_status table with the new fetch details (for example, setting fetched_at and parsed_at to the current timestamp)?
Yes, but fetched_at is added when HTML is fetched, parsed_at is added when article is succesfully written to database table. 
If so, should the script update the pub_date in that table as well?
Yes


Handling Missing Records:

If an article’s URL from pt_abc.articles is not found in pt_abc.article_status, should the script treat it as “not yet fetched and parsed” and then proceed to fetch, update the article’s content, and also insert a new status record?
No, just skip it, but this should not happen. 
You should report on the end with print statements:
"Number of articles: feched, parsed, updated, articles without url..
In general put print statements everywhere so I know what is going on. 


Content Extraction:

The target HTML container is identified by
html
Kopiraj
<div class="xvlfx ZRifP TKoO eaKKC EcdEg bOdfO qXhdi NFNeu UyHES " data-testid="prism-article-body">
Is it safe to assume that this data-testid attribute is always present and unique on the page?
Should we simply extract all the text (using something like BeautifulSoup’s .get_text() with appropriate separators) and update the article’s content field with that text?
Yes I guess that should be fine. 
data-testid="prism-article-body" - this is unique value for data-testid that holds articles content, otherwise data-testid is showing elsewhere too.

Error Handling and Retries:

In case a URL fetch fails (e.g. due to network issues or a non-200 response), should the script log the error and skip that article, or would you like to have a retry mechanism?
We should have retry mechanism but check error - if its 403 forbidded on 404 not existing or 5xx than there is no point in retrying but reporting on them. Skip to next url. 
If more than 3 consecutive URLs show 403 than abort and report on this. 

Sleep Timing:

You mentioned “normal random time sleep between attempts to get HTML of the url, maybe 4-7 seconds.” Should the sleep occur between each URL fetch attempt (i.e. after processing one article, wait 4–7 seconds before the next), or only when an error occurs?
After each error and each sucessfull fecth too. 



# ### database context - you need to use database handling like previous script
# db_context.py
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator
import sqlalchemy as sa
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from db_scripts.db_utils import load_db_config

class DatabaseContext:
    _instances: Dict[str, 'DatabaseContext'] = {}
    
    def __init__(self, env: str = 'dev'):
        """Initialize database context with environment-specific configuration"""
        self.env = env
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._setup_engine()
    
    @classmethod
    def get_instance(cls, env: str = 'dev') -> 'DatabaseContext':
        """Get or create a DatabaseContext instance for the specified environment"""
        if env not in cls._instances:
            cls._instances[env] = cls(env)
        return cls._instances[env]
    
    def _setup_engine(self) -> None:
        """Set up SQLAlchemy engine with proper pooling configuration"""
        db_config = load_db_config()
        if not db_config or self.env not in db_config:
            raise ValueError(f"No database configuration found for environment: {self.env}")
        
        params = db_config[self.env]
        shared_config = db_config.get('shared', {})
        
        # Construct connection URL
        url = f"postgresql://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{params['name']}"
        
        # Configure pooling
        pool_config = params.get('pool', {})
        pooling_args = {
            'poolclass': QueuePool,
            'pool_size': pool_config.get('max_connections', 10),
            'max_overflow': 5,
            'pool_timeout': 30,
            'pool_recycle': pool_config.get('idle_timeout', 300),
            'pool_pre_ping': True,
        }
        
        # Configure connection arguments
        connect_args = {
            'application_name': shared_config.get('application_name', 'news_aggregator'),
            'connect_timeout': shared_config.get('connect_timeout', 10),
            'options': f"-c statement_timeout={shared_config.get('statement_timeout', 30000)}",
        }
        
        if shared_config.get('ssl_mode'):
            connect_args['sslmode'] = shared_config['ssl_mode']
        
        self._engine = sa.create_engine(
            url,
            **pooling_args,
            connect_args=connect_args,
            echo=False  # Set to True for SQL query logging
        )
        
        self._session_factory = sessionmaker(
            bind=self._engine,
            expire_on_commit=False
        )
    
    @property
    def engine(self) -> Engine:
        """Get SQLAlchemy engine instance"""
        if not self._engine:
            self._setup_engine()
        return self._engine
    
    def get_connection_string(self) -> str:
        """Get database connection string for SQLAlchemy"""
        db_config = load_db_config()
        if not db_config or self.env not in db_config:
            raise ValueError(f"No database configuration found for environment: {self.env}")
        
        params = db_config[self.env]
        return f"postgresql://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{params['name']}"
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Get a database session context manager
        
        Returns:
            Generator[Session, None, None]: A context manager that yields a SQLAlchemy Session
        """
        if not self._session_factory:
            self._setup_engine()
            
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @contextmanager
    def connection(self) -> Generator[Connection, None, None]:
        """Get a raw connection context manager
        
        Returns:
            Generator[Connection, None, None]: A context manager that yields a SQLAlchemy Connection
        """
        with self.engine.connect() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    
    def dispose(self) -> None:
        """Dispose of the engine and all connections"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
    
    def __enter__(self) -> 'DatabaseContext':
        return self
    
    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]) -> None:
        self.dispose()