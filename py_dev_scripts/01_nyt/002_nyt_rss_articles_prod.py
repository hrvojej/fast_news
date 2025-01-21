import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

@dataclass
class Article:
    title: str
    link: str
    guid: str
    description: Optional[str]
    author: List[str]
    pub_date: Optional[datetime]
    category_id: int
    keywords: List[str]
    image_url: Optional[str]
    image_width: Optional[int]
    image_credit: Optional[str]

class NYTScraper:
    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
        self.connection = None
        self.cursor = None
        self.stats = {
            'total_processed': 0,
            'total_inserted': 0,
            'total_updated': 0,
            'total_with_images': 0,
            'total_with_keywords': 0,
            'categories_processed': 0,
            'categories_failed': 0
        }

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

    def get_categories(self) -> List[Tuple[int, str, str]]:
        """Fetch categories with atom_links."""
        try:
            self.cursor.execute("""
                SELECT category_id, atom_link, name 
                FROM nyt.categories 
                WHERE atom_link IS NOT NULL 
                ORDER BY category_id;
            """)
            categories = self.cursor.fetchall()
            logger.info(f"Found {len(categories)} categories with atom_link.")
            return categories
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            self.connection.rollback()
            raise

    def parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse publication date string to datetime."""
        if not date_str:
            return None
        try:
            return parsedate_to_datetime(date_str).astimezone(timezone.utc)
        except Exception as e:
            logger.warning(f"Could not parse date {date_str}: {e}")
            return None

    def parse_article(self, item: BeautifulSoup, category_id: int) -> Article:
        """Parse a single article item."""
        title = item.find('title').text.strip() if item.find('title') else ''
        link = item.find('link').text.strip() if item.find('link') else ''
        guid = item.find('guid').text.strip() if item.find('guid') else ''
        description = item.find('description').text.strip() if item.find('description') else ''

        authors = [creator.text.strip() for creator in item.find_all('dc:creator')] if item.find_all('dc:creator') else []

        pub_date_str = item.find('pubDate').text.strip() if item.find('pubDate') else None
        pub_date = self.parse_date(pub_date_str)

        keywords = [category.text.strip() for category in item.find_all('category') if category.text.strip() and len(category.text.strip()) > 2]

        image_url, image_width, image_credit = None, None, None
        media_contents = item.find_all('media:content')
        if media_contents:
            valid_media = [
                (media.get('url'), int(media.get('width', 0)), media.find('media:credit'))
                for media in media_contents if media.get('url') and media.get('width', '0').isdigit()
            ]
            if valid_media:
                sorted_media = sorted(valid_media, key=lambda x: x[1], reverse=True)
                image_url, image_width, credit_tag = sorted_media[0]
                image_credit = credit_tag.text.strip() if credit_tag else None

        return Article(
            title=title,
            link=link,
            guid=guid,
            description=description,
            author=authors,
            pub_date=pub_date,
            category_id=category_id,
            keywords=keywords,
            image_url=image_url,
            image_width=image_width,
            image_credit=image_credit
        )

    def upsert_articles(self, articles: List[Article]) -> Tuple[int, int]:
        """Upsert articles and return count of inserted and updated articles."""
        if not articles:
            return 0, 0

        upsert_query = """
        INSERT INTO nyt.articles (
            title, url, guid, description, author, pub_date, category_id,
            keywords, image_url, image_width, image_credit
        )
        VALUES %s
        ON CONFLICT (guid) 
        DO UPDATE SET
            title = EXCLUDED.title,
            url = EXCLUDED.url,
            description = EXCLUDED.description,
            author = EXCLUDED.author,
            pub_date = EXCLUDED.pub_date,
            category_id = EXCLUDED.category_id,
            keywords = EXCLUDED.keywords,
            image_url = EXCLUDED.image_url,
            image_width = EXCLUDED.image_width,
            image_credit = EXCLUDED.image_credit
        WHERE nyt.articles.pub_date < EXCLUDED.pub_date
        RETURNING article_id, (xmax = 0) as inserted;
        """

        article_data = [
            (
                article.title, article.link, article.guid, article.description,
                article.author, article.pub_date, article.category_id, article.keywords,
                article.image_url, article.image_width, article.image_credit
            ) for article in articles
        ]

        try:
            results = execute_values(self.cursor, upsert_query, article_data, fetch=True)
            inserted = sum(1 for r in results if r[1])
            updated = len(results) - inserted
            return inserted, updated
        except Exception as e:
            logger.error(f"Error executing upsert query: {e}")
            self.connection.rollback()
            raise

    def process_category(self, category_id: int, atom_link: str, category_name: str) -> None:
        """Process a single category feed."""
        try:
            logger.info(f"Processing category {category_id} - {category_name}")
            response = requests.get(atom_link, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'xml')

            items = soup.find_all('item')
            logger.info(f"Found {len(items)} items in feed")

            batch_size = 50
            for i in range(0, len(items), batch_size):
                batch_items = items[i:i + batch_size]
                parsed_articles = [self.parse_article(item, category_id) for item in batch_items]

                inserted, updated = self.upsert_articles(parsed_articles)
                self.connection.commit()

                self.stats['total_inserted'] += inserted
                self.stats['total_updated'] += updated

        except requests.RequestException as e:
            logger.error(f"Error fetching feed {atom_link}: {e}")
            self.connection.rollback()
            self.stats['categories_failed'] += 1
            raise
        except Exception as e:
            logger.error(f"Error processing category {category_name}: {e}")
            self.connection.rollback()
            self.stats['categories_failed'] += 1
            raise

    def run(self) -> Dict[str, int]:
        """Main execution method."""
        try:
            self.connect_to_db()
            categories = self.get_categories()

            for category_id, atom_link, category_name in categories:
                try:
                    self.process_category(category_id, atom_link, category_name)
                except Exception as e:
                    logger.error(f"Error processing category {category_name}: {e}")
                    continue

            logger.info("\nProcessing complete. Final statistics:")
            logger.info(f"Categories processed: {self.stats['categories_processed']}")
            logger.info(f"Categories failed: {self.stats['categories_failed']}")
            logger.info(f"Articles inserted: {self.stats['total_inserted']}")
            logger.info(f"Articles updated: {self.stats['total_updated']}")

            return self.stats

        except Exception as e:
            logger.error(f"Fatal error: {e}")
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
    try:
        stats = scraper.run()
        print("Scraping completed successfully")
    except Exception as e:
        print(f"Scraping failed: {e}")