import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values
from typing import Dict, List, Set, Tuple, Optional
import logging
from dataclasses import dataclass
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Article:
    title: str
    link: str
    guid: str
    description: Optional[str]
    author: List[str]
    pub_date: Optional[str]
    category_id: int
    keywords: List[Tuple[str, str]]  # List of (domain, keyword) tuples
    media: List[Tuple[str, str, Optional[int], Optional[int], Optional[str], Optional[str]]]  # url, medium, width, height, credit, description

class NYTScraper:
    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
        self.connection = None
        self.cursor = None
        
    def check_and_remove_duplicates(self):
        """Check for and remove duplicate entries in articles, keywords, and media tables."""
        try:
            # Remove duplicate articles keeping the latest version
            self.cursor.execute("""
                WITH duplicates AS (
                    SELECT guid,
                           ROW_NUMBER() OVER (PARTITION BY guid ORDER BY created_at DESC) as row_num
                    FROM nyt.articles
                    WHERE guid IS NOT NULL
                )
                DELETE FROM nyt.articles
                WHERE guid IN (
                    SELECT guid 
                    FROM duplicates 
                    WHERE row_num > 1
                );
            """)
            
            # Remove duplicate keywords
            self.cursor.execute("""
                WITH duplicates AS (
                    SELECT article_id, domain, keyword,
                           ROW_NUMBER() OVER (PARTITION BY article_id, domain, keyword ORDER BY created_at DESC) as row_num
                    FROM nyt.keywords
                )
                DELETE FROM nyt.keywords
                WHERE (article_id, domain, keyword) IN (
                    SELECT article_id, domain, keyword
                    FROM duplicates 
                    WHERE row_num > 1
                );
            """)
            
            # Remove duplicate media entries
            self.cursor.execute("""
                WITH duplicates AS (
                    SELECT article_id, url,
                           ROW_NUMBER() OVER (PARTITION BY article_id, url ORDER BY created_at DESC) as row_num
                    FROM nyt.media
                )
                DELETE FROM nyt.media
                WHERE (article_id, url) IN (
                    SELECT article_id, url
                    FROM duplicates 
                    WHERE row_num > 1
                );
            """)
            
            affected_rows = self.cursor.statusmessage
            self.connection.commit()
            logger.info(f"Duplicate removal completed: {affected_rows}")
            
        except psycopg2.Error as e:
            logger.error(f"Error removing duplicates: {e}")
            self.connection.rollback()
            raise

    def connect_to_db(self):
        """Establish database connection."""
        try:
            logger.info("Connecting to PostgreSQL...")
            self.connection = psycopg2.connect(**self.db_config)
            self.cursor = self.connection.cursor()
        except psycopg2.Error as e:
            logger.error(f"Database connection error: {e}")
            raise

    def close_db_connection(self):
        """Close database connection and cursor."""
        if self.cursor:
            self.cursor.close()
            logger.info("Database cursor closed.")
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed.")

    def get_existing_articles(self) -> Set[str]:
        """Fetch existing article GUIDs from database."""
        self.cursor.execute("SELECT guid FROM nyt.articles;")
        existing_guids = set(row[0] for row in self.cursor.fetchall())
        logger.info(f"Found {len(existing_guids)} existing articles in database.")
        return existing_guids

    def get_categories(self) -> List[Tuple[int, str]]:
        """Fetch categories with atom_links."""
        self.cursor.execute("SELECT category_id, atom_link FROM nyt.categories WHERE atom_link IS NOT NULL;")
        categories = self.cursor.fetchall()
        logger.info(f"Found {len(categories)} categories with atom_link.")
        return categories

    def parse_article(self, item, category_id: int) -> Article:
        """Parse a single article item."""
        # Extract core article fields
        title = item.find('title').text if item.find('title') else None
        link = item.find('link').text if item.find('link') else None
        guid = item.find('guid').text if item.find('guid') else None
        description = item.find('description').text if item.find('description') else None
        author = [creator.text for creator in item.find_all('dc:creator')] if item.find('dc:creator') else []
        pub_date = item.find('pubDate').text if item.find('pubDate') else None

        # Extract keywords
        keywords = []
        for category in item.find_all('category'):
            domain = category.get('domain', 'unknown')
            keyword = category.text.strip()
            keywords.append((domain, keyword))

        # Extract media content
        media = []
        for media_content in item.find_all('media:content'):
            url = media_content.get('url')
            medium = media_content.get('medium')
            width = int(media_content.get('width')) if media_content.get('width') else None
            height = int(media_content.get('height')) if media_content.get('height') else None
            credit = item.find('media:credit').text if item.find('media:credit') else None
            media_desc = item.find('media:description').text if item.find('media:description') else None
            media.append((url, medium, width, height, credit, media_desc))

        return Article(
            title=title,
            link=link,
            guid=guid,
            description=description,
            author=author,
            pub_date=pub_date,
            category_id=category_id,
            keywords=keywords,
            media=media
        )

    def fetch_and_parse_feed(self, category_id: int, atom_link: str) -> List[Article]:
        """Fetch and parse an RSS feed."""
        try:
            logger.info(f"Fetching RSS feed: {atom_link}")
            response = requests.get(atom_link, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'xml')
            articles = []

            for item in soup.find_all('item'):
                article = self.parse_article(item, category_id)
                if article.guid:  # Only add articles with valid GUIDs
                    articles.append(article)

            return articles
            
        except requests.RequestException as e:
            logger.error(f"Error fetching RSS feed {atom_link}: {e}")
            return []

    def update_database(self, articles: List[Article], existing_guids: Set[str]):
        """Update database with new content."""
        try:
            # Prepare article data for insertion
            article_data = [
                (
                    a.title, a.link, a.guid, a.description, a.author,
                    a.pub_date, a.category_id, 'now()', 'now()'
                )
                for a in articles
                if a.guid not in existing_guids
            ]

            # Insert articles and get their IDs
            if article_data:
                insert_articles_query = """
                INSERT INTO nyt.articles (
                    title, url, guid, description, author, pub_date, category_id, created_at, updated_at
                )
                VALUES %s
                RETURNING article_id, guid;
                """
                execute_values(self.cursor, insert_articles_query, article_data)
                
                # Create a mapping of guid to article_id
                article_mapping = {row[1]: row[0] for row in self.cursor.fetchall()}
            else:
                article_mapping = {}

            # Get existing article IDs for all articles
            self.cursor.execute(
                "SELECT article_id, guid FROM nyt.articles WHERE guid = ANY(%s);",
                ([a.guid for a in articles],)
            )
            article_mapping.update(dict(self.cursor.fetchall()))

            # Prepare keywords and media data
            keywords_data = []
            media_data = []

            for article in articles:
                article_id = article_mapping.get(article.guid)
                if article_id:
                    # Add keywords
                    for domain, keyword in article.keywords:
                        keywords_data.append(
                            (article_id, domain, keyword, 'now()', 'now()')
                        )
                    
                    # Add media entries
                    for url, medium, width, height, credit, description in article.media:
                        media_data.append(
                            (article_id, url, medium, width, height, credit, description, 'now()', 'now()')
                        )

            # Insert keywords
            if keywords_data:
                insert_keywords_query = """
                INSERT INTO nyt.keywords (
                    article_id, domain, keyword, created_at, updated_at
                )
                VALUES %s
                ON CONFLICT (article_id, domain, keyword) DO NOTHING;
                """
                execute_values(self.cursor, insert_keywords_query, keywords_data)

            # Insert media
            if media_data:
                insert_media_query = """
                INSERT INTO nyt.media (
                    article_id, url, medium, width, height, credit, description, created_at, updated_at
                )
                VALUES %s
                ON CONFLICT DO NOTHING;
                """
                execute_values(self.cursor, insert_media_query, media_data)

            self.connection.commit()
            logger.info(f"Database updated successfully - {len(article_data)} new articles, {len(keywords_data)} keywords, {len(media_data)} media entries")
            
        except psycopg2.Error as e:
            logger.error(f"Database update error: {e}")
            self.connection.rollback()
            raise

    def run(self):
        """Main execution method."""
        try:
            self.connect_to_db()
            existing_guids = self.get_existing_articles()
            categories = self.get_categories()

            all_articles = []
            for category_id, atom_link in categories:
                articles = self.fetch_and_parse_feed(category_id, atom_link)
                all_articles.extend(articles)

            logger.info(f"Parsed {len(all_articles)} total articles")
            self.update_database(all_articles, existing_guids)

        except Exception as e:
            logger.error(f"Error during execution: {e}")
            raise
        finally:
            self.close_db_connection()

if __name__ == "__main__":
    db_config = {
        'dbname': 'news_aggregator',
        'user': 'news_admin',
        'password': 'fasldkflk423mkj4k24jk242',
        'host': 'localhost',
        'port': '5432',
    }
    
    scraper = NYTScraper(db_config)
    scraper.run()