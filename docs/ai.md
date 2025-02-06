# Categories question
Take logic from this dev ________________ category parser script and refactore it following nyt category parser example.
Make sure you use all fields from model.py :
def create_portal_categorymodel(schema: str):
    return type(
        f'Category{schema}',
        (Base,),
        {
            'tablename': 'categories',
            'table_args': (
                UniqueConstraint('slug', 'portalid', name=f'uq{schema}_categories_slug_portalid'),
                Index(f'idx{schema}_category_path', 'path', postgresqlusing='btree'),
                Index(f'idx{schema}_category_portal', 'portal_id'),
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

Did you use all fields from create_portal_categorymodel?
In case script is run several times it should not make dupes , just insert new records if there is need for that.

NYT Category Parser:
# path: news_dagster-etl/news_aggregator/portals/nyt/rss_categories_parser.py
"""
NYT RSS Categories Parser
Fetches and stores NYT RSS feed categories using SQLAlchemy ORM.
"""

import sys
import os

# Add the package root (news_aggregator) to sys.path.
current_dir = os.path.dirname(os.path.abspath(__file__))
# news_aggregator is two directories up from portals/nyt/
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

import argparse
import requests
from bs4 import BeautifulSoup
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import re
from typing import List, Dict
from uuid import UUID
from sqlalchemy import text

# Import the dynamic model factory from your models file.
from db_scripts.models.models import create_portal_category_model

# Create the dynamic category model for the NYT portal.
# Here the schema is "pt_nyt" as used in your queries.
NYTCategory = create_portal_category_model("pt_nyt")


def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
    """
    Fetches the portal_id from the news_portals table for the given portal_prefix.

    Args:
        portal_prefix: The prefix of the portal (e.g., 'pt_nyt')
        env: The environment to use ('dev' or 'prod')

    Returns:
        The UUID of the portal.

    Raises:
        Exception: If no portal with the given prefix is found.
    """
    # Import DatabaseContext from your db_context module.
    from db_scripts.db_context import DatabaseContext
    db_context = DatabaseContext.get_instance(env)
    with db_context.session() as session:
        result = session.execute(
            text("SELECT portal_id FROM public.news_portals WHERE portal_prefix = :prefix"),
            {'prefix': portal_prefix}
        ).fetchone()
        if result:
            return result[0]
        else:
            raise Exception(f"Portal with prefix '{portal_prefix}' not found.")


class NYTRSSCategoriesParser:
    """Parser for NYT RSS feed categories"""

    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=None):
        """
        Initialize the parser

        Args:
            portal_id: UUID of the NYT portal in news_portals table
            env: Environment to use (dev/prod)
            category_model: SQLAlchemy ORM model for categories (if applicable)
        """
        self.portal_id = portal_id
        self.env = env
        self.base_url = "https://www.nytimes.com/rss"
        self.NYTCategory = category_model

    def get_session(self):
        """
        Obtain a database session from the DatabaseContext.
        """
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        # Directly enter the session context to get a session object.
        return db_context.session().__enter__()

    @staticmethod
    def clean_ltree(value: str) -> str:
        """
        Convert category title into valid ltree path.
        """
        if not value:
            return "unknown"

        # Replace "U.S." with "U_S"
        value = value.replace('U.S.', 'U_S')
        # Replace slashes with dots
        value = value.replace('/', '.').replace('\\', '.')
        # Replace arrow indicators with dots
        value = value.replace('>', '.').strip()
        # Convert to lowercase
        value = value.lower()
        # Replace any non-alphanumeric characters (except dots) with underscores
        value = re.sub(r'[^a-z0-9.]+', '_', value)
        # Replace multiple dots or underscores with a single one
        value = re.sub(r'[._]{2,}', '.', value)
        # Remove leading/trailing dots or underscores
        return value.strip('._')

    def fetch_rss_feeds(self) -> List[Dict]:
        """
        Fetch and parse NYT RSS feeds.
        """
        try:
            print(f"Fetching RSS feeds from {self.base_url}")
            response = requests.get(self.base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            rss_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'rss' in href and href.endswith('.xml'):
                    rss_links.append(href)

            unique_rss_links = list(set(rss_links))
            print(f"Found {len(unique_rss_links)} unique RSS feeds")
            return self.parse_rss_feeds(unique_rss_links)

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch RSS feeds: {e}")

    def parse_rss_feeds(self, rss_links: List[str]) -> List[Dict]:
        """
        Parse RSS feeds and extract category metadata.
        """
        categories = []
        for rss_url in rss_links:
            try:
                print(f"Processing RSS feed: {rss_url}")
                response = requests.get(rss_url)
                response.raise_for_status()
                rss_soup = BeautifulSoup(response.content, 'xml')

                channel = rss_soup.find('channel')
                if channel:
                    category = {
                        'title': channel.find('title').text if channel.find('title') else None,
                        'link': channel.find('link').text if channel.find('link') else None,
                        'description': channel.find('description').text if channel.find('description') else None,
                        'language': channel.find('language').text if channel.find('language') else None,
                        'atom_link': channel.find('atom:link', href=True)['href'] if channel.find('atom:link', href=True) else None
                    }

                    # Create ltree path and level.
                    path = self.clean_ltree(category['title']) if category['title'] else 'unknown'
                    category['path'] = path
                    category['level'] = len(path.split('.'))

                    categories.append(category)

            except Exception as e:
                print(f"Error processing RSS feed {rss_url}: {e}")
                continue

        return categories
    
    def store_categories(self, categories: List[Dict]):
        """
        Store categories using SQLAlchemy ORM.
        """
        session = self.get_session()

        try:
            print("Storing categories in database...")
            count_added = 0
            for category_data in categories:
                slug = self.clean_ltree(category_data['title']) if category_data['title'] else 'unknown'

                existing = session.query(self.NYTCategory).filter(
                    self.NYTCategory.slug == slug,
                    self.NYTCategory.portal_id == self.portal_id
                ).first()
                if existing:
                    print(f"Category with slug '{slug}' already exists. Skipping insertion.")
                    continue

                category = self.NYTCategory(
                    name=category_data['title'],
                    slug=slug,
                    portal_id=self.portal_id,
                    path=category_data['path'],
                    level=category_data['level'],
                    description=category_data['description'],
                    link=category_data['link'],
                    atom_link=category_data['atom_link'],
                    is_active=True
                )
                session.add(category)
                count_added += 1

            session.commit()
            print(f"Successfully stored {count_added} new categories")

        except Exception as e:
            session.rollback()
            raise Exception(f"Failed to store categories: {e}")

        finally:
            session.close()
    
    def run(self):
        """
        Main method to fetch and store NYT categories.
        """
        try:
            categories = self.fetch_rss_feeds()
            self.store_categories(categories)
            print("Category processing completed successfully")
        except Exception as e:
            print(f"Error processing categories: {e}")
            raise


def main():
    """
    Script entry point.
    """
    import argparse
    # Import Base from your models file to inspect the metadata
    from db_scripts.models.models import Base
    print("Registered tables in metadata:", Base.metadata.tables.keys())

    argparser = argparse.ArgumentParser(description="NYT RSS Categories Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment to load data (default: dev)"
    )
    args = argparser.parse_args()

    portal_prefix = "pt_nyt"  # The portal prefix.
    try:
        portal_id = fetch_portal_id_by_prefix(portal_prefix, env=args.env)
        print(f"Using portal_id: {portal_id} for portal_prefix: {portal_prefix}")

        parser_instance = NYTRSSCategoriesParser(portal_id=portal_id, env=args.env, category_model=NYTCategory)
        parser_instance.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()



# ###################################### article question ############################
I similar way how nyt article parser is refactored now I need to refactor from dev script guardian rss article parser.
Make sure you use all fields from article model as is.
In case script is run several times it should not make dupes , just insert new records if there is need for that.


import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
import nltk
from datetime import datetime
from typing import Dict, List, Tuple

class KeywordExtractor:
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
        
        chunks = text.split()
        if not chunks:
            return []
            
        text_embedding = self.model.encode([text])
        chunk_embeddings = self.model.encode(chunks)
        
        similarities = cosine_similarity(text_embedding, chunk_embeddings).flatten()
        scored_chunks = sorted(
            [(chunks[i], score) for i, score in enumerate(similarities)],
            key=lambda x: x[1], reverse=True
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

def recreate_table(connection: psycopg2.extensions.connection, cursor: psycopg2.extensions.cursor) -> None:
    """Create a single combined articles table."""
    try:
        print("Recreating Guardian articles table...")
        cursor.execute("""
        DROP TABLE IF EXISTS guardian.articles;

        CREATE TABLE guardian.articles (
            article_id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            guid TEXT UNIQUE,
            description TEXT,
            author TEXT[],
            pub_date TIMESTAMPTZ,
            category_id INT NOT NULL REFERENCES guardian.categories(category_id) ON DELETE CASCADE,
            keywords TEXT[],
            image_url TEXT,
            image_width INT,
            image_credit TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)
        connection.commit()
        print("Guardian articles table recreated successfully.")
    except psycopg2.Error as e:
        print(f"Error recreating table: {e}")
        connection.rollback()
        raise

def parse_article(item: BeautifulSoup, category_id: int, keyword_extractor: KeywordExtractor) -> Dict:
    """Parse a single Guardian RSS item."""
    title = item.find('title').text.strip() if item.find('title') else ''
    description = item.find('description').text.strip() if item.find('description') else ''
    link = item.find('link').text.strip() if item.find('link') else ''
    guid = item.find('guid').text.strip() if item.find('guid') else ''
    pub_date = item.find('pubDate').text.strip() if item.find('pubDate') else None
    
    # Extract authors
    authors = []
    dc_creator = item.find('dc:creator')
    if dc_creator:
        authors = [author.strip() for author in dc_creator.text.split(',')]
    
    # Extract keywords from title
    keywords = keyword_extractor.extract_keywords(title) if title else []

    # Get the largest image (assuming larger width means better quality)
    image_url = None
    image_width = None
    image_credit = None
    media_contents = item.find_all('media:content')
    
    if media_contents:
        # Sort media content by width and get the largest
        valid_media = [(m.get('url'), int(m.get('width', 0)), m.find('media:credit'))
                      for m in media_contents
                      if m.get('url') and m.get('width')]
        
        if valid_media:
            # Sort by width in descending order
            sorted_media = sorted(valid_media, key=lambda x: x[1], reverse=True)
            image_url, image_width, credit_tag = sorted_media[0]
            image_credit = credit_tag.text if credit_tag else None

    return {
        'title': title,
        'url': link,
        'guid': guid,
        'description': description,
        'author': authors,
        'pub_date': pub_date,
        'category_id': category_id,
        'keywords': keywords,
        'image_url': image_url,
        'image_width': image_width,
        'image_credit': image_credit
    }

def batch_insert_articles(cursor: psycopg2.extensions.cursor, articles: List[Dict]) -> int:
    """Insert articles in batch and return number of inserted articles."""
    if not articles:
        return 0

    insert_query = """
    INSERT INTO guardian.articles (
        title, url, guid, description, author, pub_date, category_id,
        keywords, image_url, image_width, image_credit
    )
    VALUES %s
    ON CONFLICT (guid) DO NOTHING
    RETURNING article_id;
    """
    
    article_data = [
        (
            article['title'],
            article['url'],
            article['guid'],
            article['description'],
            article['author'],
            article['pub_date'],
            article['category_id'],
            article['keywords'],
            article['image_url'],
            article['image_width'],
            article['image_credit']
        )
        for article in articles
    ]
    
    result = execute_values(cursor, insert_query, article_data, fetch=True)
    return len(result)

def process_guardian_rss():
    """Main function to process Guardian RSS feeds."""
    db_config = {
        'dbname': 'news_aggregator',
        'user': 'news_admin',
        'password': 'fasldkflk423mkj4k24jk242',
        'host': 'localhost',
        'port': '5432',
    }

    try:
        print("Initializing keyword extractor...")
        keyword_extractor = KeywordExtractor()
        
        print("Connecting to PostgreSQL...")
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        # Recreate the articles table
        recreate_table(connection, cursor)

        print("Fetching Guardian categories...")
        cursor.execute("""
            SELECT category_id, atom_link, name 
            FROM guardian.categories 
            WHERE atom_link IS NOT NULL 
            ORDER BY category_id;
        """)
        categories = cursor.fetchall()
        print(f"Found {len(categories)} categories to process")

        total_articles = 0
        total_with_images = 0
        total_with_keywords = 0

        for category_id, atom_link, category_name in categories:
            try:
                print(f"\nProcessing category {category_id} - {category_name}")
                print(f"Feed URL: {atom_link}")
                
                response = requests.get(atom_link, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'xml')

                items = soup.find_all('item')
                print(f"Found {len(items)} items in feed")

                # Process items in batches
                batch_size = 50
                category_articles = 0
                category_with_images = 0
                category_with_keywords = 0
                
                for i in range(0, len(items), batch_size):
                    batch_items = items[i:i + batch_size]
                    print(f"Processing batch {i//batch_size + 1} of {(len(items) + batch_size - 1)//batch_size}")
                    
                    # Parse and insert batch of articles
                    parsed_articles = [parse_article(item, category_id, keyword_extractor) for item in batch_items]
                    
                    # Count articles with images and keywords before insertion
                    articles_with_images = sum(1 for a in parsed_articles if a['image_url'])
                    articles_with_keywords = sum(1 for a in parsed_articles if a['keywords'])
                    
                    # Insert articles
                    inserted_count = batch_insert_articles(cursor, parsed_articles)
                    connection.commit()

                    # Update counts
                    category_articles += inserted_count
                    category_with_images += articles_with_images
                    category_with_keywords += articles_with_keywords

                print(f"Category {category_name} processing complete:")
                print(f"- Articles inserted: {category_articles}")
                print(f"- Articles with images: {category_with_images}")
                print(f"- Articles with keywords: {category_with_keywords}")

                total_articles += category_articles
                total_with_images += category_with_images
                total_with_keywords += category_with_keywords

            except requests.exceptions.RequestException as e:
                print(f"Error fetching feed {atom_link}: {e}")
                continue
            except Exception as e:
                print(f"Error processing category {category_name}: {e}")
                continue

        print("\nProcessing complete. Final counts:")
        print(f"Total categories processed: {len(categories)}")
        print(f"Total articles inserted: {total_articles}")
        print(f"Total articles with images: {total_with_images}")
        print(f"Total articles with keywords: {total_with_keywords}")

    except Exception as e:
        print(f"Error: {e}")
        if connection:
            connection.rollback()

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    process_guardian_rss()



# NYT Article Parser
"""
NYT RSS Articles Parser
Fetches and stores NYT RSS feed articles using SQLAlchemy ORM.
"""

import sys
import os
from datetime import datetime
from typing import List, Dict
from uuid import UUID
import requests
from bs4 import BeautifulSoup
import argparse
from sqlalchemy import text

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)
    
# Category model creation
from db_scripts.models.models import create_portal_category_model
NYTCategory = create_portal_category_model("pt_nyt")

# Import the dynamic model factory
from db_scripts.models.models import create_portal_article_model

# Create the dynamic article model for NYT portal
NYTArticle = create_portal_article_model("pt_nyt")

def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
    """Fetches the portal_id from news_portals table."""
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

class NYTRSSArticlesParser:
    """Parser for NYT RSS feed articles"""

    def __init__(self, portal_id: UUID, env: str = 'dev', article_model=None):
        self.portal_id = portal_id
        self.env = env
        self.NYTArticle = article_model

    def get_session(self):
        """Get database session from DatabaseContext."""
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        return db_context.session().__enter__()

    def parse_article(self, item: BeautifulSoup, category_id: UUID) -> Dict:
        """Parse a single NYT RSS item."""
        # Required fields
        title = item.find('title').text.strip() if item.find('title') else 'Untitled'
        link = item.find('link').text.strip() if item.find('link') else 'https://www.nytimes.com'
        guid = item.find('guid').text.strip() if item.find('guid') else link  # Use URL as fallback GUID
        
        # Optional fields with defaults
        description = item.find('description').text.strip() if item.find('description') else None
        content = description  # Using description as content fallback
        pub_date_str = item.find('pubDate').text.strip() if item.find('pubDate') else None
        pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z') if pub_date_str else datetime.utcnow()
        
        # Arrays with empty list defaults
        authors = [creator.text.strip() for creator in item.find_all('dc:creator')] or []
        keywords = [cat.text.strip() for cat in item.find_all('category') 
                   if cat.text.strip() and len(cat.text.strip()) > 2] or []
        
        # Get image information
        image_url = None
        media_contents = item.find_all('media:content')
        if media_contents:
            valid_media = [(m.get('url'), int(m.get('width'))) 
                          for m in media_contents 
                          if m.get('width') and m.get('width').isdigit()]
            if valid_media:
                image_url = max(valid_media, key=lambda x: x[1])[0]

        # Calculate reading time (rough estimate: 200 words per minute)
        text_content = f"{title} {description or ''} {content or ''}"
        word_count = len(text_content.split())
        reading_time = max(1, round(word_count / 200))

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
            'sentiment_score': 0.0,  # Neutral sentiment as default
            'share_count': 0,
            'view_count': 0,
            'comment_count': 0
        }

    def fetch_and_store_articles(self):
        """Fetch and store articles from all RSS feeds."""
        print("Starting fetch_and_store_articles...")
        session = self.get_session()
        print("Executing categories query...")
        try:
            # Get all active categories
            categories = session.execute(
                text("""
                    SELECT category_id, atom_link 
                    FROM pt_nyt.categories 
                    WHERE is_active = true AND atom_link IS NOT NULL 
                """)
            ).fetchall()
            print(f"Found {len(categories)} categories")

            for category_id, atom_link in categories:
                print("Processing category:", category_id)
                try:
                    response = requests.get(atom_link, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'xml')
                    
                    for item in soup.find_all('item'):
                        article_data = self.parse_article(item, category_id)
                        existing = session.query(self.NYTArticle).filter(
                            self.NYTArticle.guid == article_data['guid']
                        ).first()

                        if not existing:
                            article = self.NYTArticle(**article_data)
                            session.add(article)
                        elif existing.pub_date != article_data['pub_date']:
                            for key, value in article_data.items():
                                setattr(existing, key, value)                 

                        print(f"Processing article: {article_data['title']}")
                    
                    session.commit()
                    
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
        """Main method to fetch and store NYT articles."""
        try:
            self.fetch_and_store_articles()
            print("Article processing completed successfully")
        except Exception as e:
            print(f"Error processing articles: {e}")
            raise

def main():
    """Script entry point."""
    argparser = argparse.ArgumentParser(description="NYT RSS Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    try:
        portal_id = fetch_portal_id_by_prefix("pt_nyt", env=args.env)
        parser = NYTRSSArticlesParser(portal_id=portal_id, env=args.env, article_model=NYTArticle)
        parser.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()

# Model from model.py
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

