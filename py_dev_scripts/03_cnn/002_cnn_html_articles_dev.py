import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
import nltk
import re
import unicodedata
import random
import time
from datetime import datetime
from urllib.parse import urljoin
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

def clean_text(text: str) -> str:
    """Clean text from special characters and normalize whitespace"""
    if not text:
        return ""
        
    cleaned = text.strip()
    cleaned = re.sub(r'[\n\r\t\f\v]+', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'[^\S\r\n]+', ' ', cleaned)
    cleaned = re.sub(r'¶|•|■|▪|►|▼|▲|◄|★|☆|⚡', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = "".join(char for char in cleaned if unicodedata.category(char)[0] != "C")
    return cleaned.strip()

def fetch_page_with_retry(url: str, max_retries: int = 3) -> str:
    """Fetch page content with retry mechanism"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

    for attempt in range(max_retries):
        try:
            # time.sleep(random.uniform(1, 2))
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(random.uniform(2, 4))

def recreate_table(connection: psycopg2.extensions.connection, cursor: psycopg2.extensions.cursor) -> None:
    """Create a single combined articles table for CNN."""
    try:
        print("Recreating CNN articles table...")
        cursor.execute("""
        DROP TABLE IF EXISTS cnn.articles;

        CREATE TABLE cnn.articles (
            article_id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            guid TEXT UNIQUE,
            description TEXT,
            author TEXT[],
            pub_date TIMESTAMPTZ,
            category_id INT NOT NULL REFERENCES cnn.categories(category_id) ON DELETE CASCADE,
            keywords TEXT[],
            image_url TEXT,
            image_width INT,
            image_credit TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)
        connection.commit()
        print("CNN articles table recreated successfully.")
    except psycopg2.Error as e:
        print(f"Error recreating table: {e}")
        connection.rollback()
        raise

def parse_article(card: BeautifulSoup, category_id: int, base_url: str, keyword_extractor: KeywordExtractor) -> Dict:
    """Parse a single CNN article card."""
    link_elem = card.find('a', class_='container__link') or card.find('a', href=True)
    if not link_elem or not link_elem.get('href'):
        return None

    relative_url = link_elem.get('href', '').strip()
    full_url = urljoin(base_url, relative_url)

    # Extract title
    title = None
    title_elem = link_elem.find('span', class_='container__headline-text')
    if title_elem:
        title = clean_text(title_elem.text)
    if not title:
        headline_div = link_elem.find('div', class_='container__headline')
        if headline_div:
            title = clean_text(headline_div.text)
    if not title:
        link_text = clean_text(link_elem.get_text())
        if len(link_text) > 10:
            title = link_text

    if not title or len(title) < 10:
        return None

    # Clean the title
    title = re.sub(r'►\s*Video\s*►\s*', '', title)
    title = re.sub(r'▶\s*', '', title)
    title = re.sub(r'\s*\d+:\d+\s*$', '', title)

    # Extract image
    image_url = None
    image_width = None
    image_credit = None
    
    image = card.find('img')
    if image:
        image_url = image.get('src')
        if not image_url:
            image_url = image.get('data-src')
        image_width = int(image.get('width')) if image.get('width') and image.get('width').isdigit() else None
        image_credit = 'CNN'

    # Extract keywords from title
    keywords = keyword_extractor.extract_keywords(title) if title else []

    return {
        'title': title,
        'url': full_url,
        'guid': full_url,
        'description': None,
        'author': [],  # CNN HTML doesn't provide authors in card view
        'pub_date': datetime.now(), # Incorrect, but we don't have the actual date
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
    INSERT INTO cnn.articles (
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

def process_cnn():
    """Main function to process CNN categories."""
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

        # First recreate the articles table
        recreate_table(connection, cursor)

        print("Fetching CNN categories...")
        cursor.execute("""
            WITH subcategories AS (
                SELECT c1.category_id, c1.link, c1.name
                FROM cnn.categories c1
                WHERE c1.level = 2
                UNION
                SELECT c2.category_id, c2.link, c2.name
                FROM cnn.categories c2
                WHERE c2.level = 1
                AND NOT EXISTS (
                    SELECT 1 
                    FROM cnn.categories sub 
                    WHERE sub.path <@ c2.path 
                    AND sub.level = 2
                )
            )
            SELECT category_id, link, name 
            FROM subcategories 
            WHERE link IS NOT NULL 
            AND link != ''
            ORDER BY category_id;
        """)
        categories = cursor.fetchall()
        print(f"Found {len(categories)} categories to process")

        total_articles = 0
        total_with_images = 0
        total_with_keywords = 0

        for category_id, link, category_name in categories:
            try:
                print(f"\nProcessing category {category_id} - {category_name}")
                print(f"URL: {link}")
                
                html_content = fetch_page_with_retry(link)
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Find all article cards
                article_cards = []
                for selector in ['div[data-component-name="card"]', 'div.container__item', 'div[data-uri*="card"]']:
                    if not article_cards:
                        article_cards = soup.select(selector)

                print(f"Found {len(article_cards)} items in category")

                # Process items in batches
                batch_size = 50
                category_articles = 0
                category_with_images = 0
                category_with_keywords = 0
                
                for i in range(0, len(article_cards), batch_size):
                    batch_items = article_cards[i:i + batch_size]
                    
                    # Parse batch of articles
                    parsed_articles = [
                        parse_article(card, category_id, link, keyword_extractor) 
                        for card in batch_items
                    ]
                    parsed_articles = [a for a in parsed_articles if a is not None]
                    
                    # Count articles with images and keywords
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

            except requests.RequestException as e:
                print(f"Error fetching URL {link}: {e}")
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
    process_cnn()