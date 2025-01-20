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