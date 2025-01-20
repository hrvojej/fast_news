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
import logging
from datetime import datetime, timezone

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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

def parse_article(item: BeautifulSoup, category_id: int, keyword_extractor: KeywordExtractor) -> Dict:
    """Parse a single Guardian RSS item."""
    title = item.find('title').text.strip() if item.find('title') else ''
    description = item.find('description').text.strip() if item.find('description') else ''
    link = item.find('link').text.strip() if item.find('link') else ''
    guid = item.find('guid').text.strip() if item.find('guid') else ''
    
    # Parse publication date
    pub_date_str = item.find('pubDate').text.strip() if item.find('pubDate') else None
    pub_date = None
    if pub_date_str:
        try:
            # Convert to datetime object
            pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %Z')
            # Make timezone-aware
            pub_date = pub_date.replace(tzinfo=timezone.utc)
        except ValueError as e:
            logger.warning(f"Could not parse date {pub_date_str}: {e}")
    
    # Extract authors
    authors = []
    dc_creator = item.find('dc:creator')
    if dc_creator:
        authors = [author.strip() for author in dc_creator.text.split(',')]
    
    # Extract keywords from title
    keywords = keyword_extractor.extract_keywords(title) if title else []

    # Get the largest image
    image_url = None
    image_width = None
    image_credit = None
    media_contents = item.find_all('media:content')
    
    if media_contents:
        valid_media = [(m.get('url'), int(m.get('width', 0)), m.find('media:credit'))
                      for m in media_contents
                      if m.get('url') and m.get('width')]
        
        if valid_media:
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

def upsert_articles(cursor: psycopg2.extensions.cursor, articles: List[Dict]) -> Tuple[int, int]:
    """
    Upsert articles and return count of inserted and updated articles.
    """
    if not articles:
        return 0, 0

    # Prepare the upsert query
    upsert_query = """
    INSERT INTO guardian.articles (
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
    WHERE guardian.articles.pub_date < EXCLUDED.pub_date
    RETURNING article_id, 
            (xmax = 0) as inserted;
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
            article['image_credit'],
            datetime.now(timezone.utc)
        )
        for article in articles
    ]
    
    results = execute_values(cursor, upsert_query, article_data, fetch=True)
    
    # Count insertions and updates
    if results:
        inserted = sum(1 for r in results if r[1])  # r[1] is the "inserted" boolean
        updated = len(results) - inserted
        return inserted, updated
    return 0, 0

def process_guardian_rss() -> Dict[str, int]:
    """
    Main function to process Guardian RSS feeds.
    Returns dictionary with processing statistics.
    """
    db_config = {
        'dbname': 'news_aggregator',
        'user': 'news_admin',
        'password': 'fasldkflk423mkj4k24jk242',
        'host': 'localhost',
        'port': '5432',
    }

    stats = {
        'total_processed': 0,
        'total_inserted': 0,
        'total_updated': 0,
        'total_with_images': 0,
        'total_with_keywords': 0,
        'categories_processed': 0,
        'categories_failed': 0
    }

    try:
        logger.info("Initializing keyword extractor...")
        keyword_extractor = KeywordExtractor()
        
        logger.info("Connecting to PostgreSQL...")
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        logger.info("Fetching Guardian categories...")
        cursor.execute("""
            SELECT category_id, atom_link, name 
            FROM guardian.categories 
            WHERE atom_link IS NOT NULL 
            ORDER BY category_id;
        """)
        categories = cursor.fetchall()
        logger.info(f"Found {len(categories)} categories to process")

        for category_id, atom_link, category_name in categories:
            try:
                logger.info(f"Processing category {category_id} - {category_name}")
                logger.debug(f"Feed URL: {atom_link}")
                
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
                    logger.debug(f"Processing batch {i//batch_size + 1} of {(len(items) + batch_size - 1)//batch_size}")
                    
                    # Parse articles
                    parsed_articles = [parse_article(item, category_id, keyword_extractor) for item in batch_items]
                    
                    # Count articles with images and keywords
                    category_stats['articles_with_images'] += sum(1 for a in parsed_articles if a['image_url'])
                    category_stats['articles_with_keywords'] += sum(1 for a in parsed_articles if a['keywords'])
                    
                    # Upsert articles
                    inserted, updated = upsert_articles(cursor, parsed_articles)
                    category_stats['articles_inserted'] += inserted
                    category_stats['articles_updated'] += updated
                    connection.commit()

                # Log category completion
                logger.info(f"Category {category_name} processing complete:")
                logger.info(f"- Articles inserted: {category_stats['articles_inserted']}")
                logger.info(f"- Articles updated: {category_stats['articles_updated']}")
                logger.info(f"- Articles with images: {category_stats['articles_with_images']}")
                logger.info(f"- Articles with keywords: {category_stats['articles_with_keywords']}")

                # Update total stats
                stats['total_inserted'] += category_stats['articles_inserted']
                stats['total_updated'] += category_stats['articles_updated']
                stats['total_with_images'] += category_stats['articles_with_images']
                stats['total_with_keywords'] += category_stats['articles_with_keywords']
                stats['categories_processed'] += 1

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching feed {atom_link}: {e}")
                stats['categories_failed'] += 1
                continue
            except Exception as e:
                logger.error(f"Error processing category {category_name}: {e}")
                stats['categories_failed'] += 1
                continue

        stats['total_processed'] = stats['total_inserted'] + stats['total_updated']
        
        logger.info("\nProcessing complete. Final statistics:")
        logger.info(f"Categories processed: {stats['categories_processed']}")
        logger.info(f"Categories failed: {stats['categories_failed']}")
        logger.info(f"Articles inserted: {stats['total_inserted']}")
        logger.info(f"Articles updated: {stats['total_updated']}")
        logger.info(f"Articles with images: {stats['total_with_images']}")
        logger.info(f"Articles with keywords: {stats['total_with_keywords']}")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            logger.info("Database connection closed.")

    return stats

if __name__ == "__main__":
    try:
        process_guardian_rss()
    except Exception as e:
        logger.error(f"Script failed: {e}")
        raise