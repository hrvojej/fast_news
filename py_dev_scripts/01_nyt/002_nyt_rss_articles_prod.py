import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values
from typing import Dict, List, Set, Tuple, Optional
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
    keywords: List[str]  # Simplified to match Guardian script
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
        self.cursor.execute("""
            SELECT category_id, atom_link, name 
            FROM nyt.categories 
            WHERE atom_link IS NOT NULL 
            ORDER BY category_id;
        """)
        categories = self.cursor.fetchall()
        logger.info(f"Found {len(categories)} categories with atom_link.")
        return categories

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
        
        # Parse authors
        authors = []
        dc_creators = item.find_all('dc:creator')
        if dc_creators:
            authors = [creator.text.strip() for creator in dc_creators]

        # Parse date
        pub_date_str = item.find('pubDate').text.strip() if item.find('pubDate') else None
        pub_date = self.parse_date(pub_date_str)

        # Extract keywords from categories
        keywords = []
        for category in item.find_all('category'):
            keyword = category.text.strip()
            if keyword and len(keyword) > 2:
                keywords.append(keyword)

        # Get the largest image
        image_url = None
        image_width = None
        image_credit = None
        media_contents = item.find_all('media:content')
        
        if media_contents:
            valid_media = []
            for media in media_contents:
                width = media.get('width')
                url = media.get('url')
                if width and url and width.isdigit():
                    credit = media.find('media:credit')
                    valid_media.append((url, int(width), credit))
            
            if valid_media:
                sorted_media = sorted(valid_media, key=lambda x: x[1], reverse=True)
                image_url, image_width, credit_tag = sorted_media[0]
                image_credit = credit_tag.text if credit_tag else None

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
        """
        Upsert articles and return count of inserted and updated articles.
        """
        if not articles:
            return 0, 0

        upsert_query = """
        INSERT INTO nyt.articles (
            title, url, guid, description, author, pub_date, category_id,
            keywords, image_url, image_width, image_credit, updated_at
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
            image_credit = EXCLUDED.image_credit,
            updated_at = CURRENT_TIMESTAMP
        WHERE nyt.articles.pub_date < EXCLUDED.pub_date
        RETURNING article_id, (xmax = 0) as inserted;
        """

        article_data = [
            (
                article.title,
                article.link,
                article.guid,
                article.description,
                article.author,
                article.pub_date,
                article.category_id,
                article.keywords,
                article.image_url,
                article.image_width,
                article.image_credit,
                datetime.now(timezone.utc)
            )
            for article in articles
        ]

        results = execute_values(self.cursor, upsert_query, article_data, fetch=True)
        
        if results:
            inserted = sum(1 for r in results if r[1])  # r[1] is the "inserted" boolean
            updated = len(results) - inserted
            return inserted, updated
        return 0, 0

    def process_category(self, category_id: int, atom_link: str, category_name: str) -> None:
        """Process a single category feed."""
        try:
            logger.info(f"Processing category {category_id} - {category_name}")
            logger.info(f"Feed URL: {atom_link}")
            
            response = requests.get(atom_link, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'xml')

            items = soup.find_all('item')
            logger.info(f"Found {len(items)} items in feed")

            # Process items in batches
            batch_size = 50
            category_stats = {
                'articles_inserted': 0,
                'articles_updated': 0,
                'articles_with_images': 0,
                'articles_with_keywords': 0
            }

            for i in range(0, len(items), batch_size):
                batch_items = items[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} of {(len(items) + batch_size - 1)//batch_size}")
                
                # Parse batch of articles
                parsed_articles = [self.parse_article(item, category_id) for item in batch_items]
                
                # Count articles with images and keywords
                articles_with_images = sum(1 for a in parsed_articles if a.image_url)
                articles_with_keywords = sum(1 for a in parsed_articles if a.keywords)
                
                # Upsert articles
                inserted, updated = self.upsert_articles(parsed_articles)
                self.connection.commit()

                # Update category stats
                category_stats['articles_inserted'] += inserted
                category_stats['articles_updated'] += updated
                category_stats['articles_with_images'] += articles_with_images
                category_stats['articles_with_keywords'] += articles_with_keywords

            # Log category completion
            logger.info(f"Category {category_name} processing complete:")
            logger.info(f"- Articles inserted: {category_stats['articles_inserted']}")
            logger.info(f"- Articles updated: {category_stats['articles_updated']}")
            logger.info(f"- Articles with images: {category_stats['articles_with_images']}")
            logger.info(f"- Articles with keywords: {category_stats['articles_with_keywords']}")

            # Update total stats
            self.stats['total_inserted'] += category_stats['articles_inserted']
            self.stats['total_updated'] += category_stats['articles_updated']
            self.stats['total_with_images'] += category_stats['articles_with_images']
            self.stats['total_with_keywords'] += category_stats['articles_with_keywords']
            self.stats['categories_processed'] += 1

        except requests.RequestException as e:
            logger.error(f"Error fetching feed {atom_link}: {e}")
            self.stats['categories_failed'] += 1
            raise
        except Exception as e:
            logger.error(f"Error processing category {category_name}: {e}")
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

            self.stats['total_processed'] = self.stats['total_inserted'] + self.stats['total_updated']

            # Log final statistics
            logger.info("\nProcessing complete. Final statistics:")
            logger.info(f"Categories processed: {self.stats['categories_processed']}")
            logger.info(f"Categories failed: {self.stats['categories_failed']}")
            logger.info(f"Articles inserted: {self.stats['total_inserted']}")
            logger.info(f"Articles updated: {self.stats['total_updated']}")
            logger.info(f"Articles with images: {self.stats['total_with_images']}")
            logger.info(f"Articles with keywords: {self.stats['total_with_keywords']}")

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
    
    try:
        scraper = NYTScraper(db_config)
        scraper.run()
    except Exception as e:
        logger.error(f"Script failed: {e}")
        raise