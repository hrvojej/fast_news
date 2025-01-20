import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
import nltk
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional

# Set up logging - only basic configuration needed
print("Initializing keyword extractor...")

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

class BBCNewsProcessor:
    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
        self.keyword_extractor = KeywordExtractor()
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
        print("Connecting to PostgreSQL...")
        self.connection = psycopg2.connect(**self.db_config)
        self.cursor = self.connection.cursor()

    def close_db_connection(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            print("\nDatabase connection closed.")

    def parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
        except Exception:
            return None

    def parse_article(self, item: BeautifulSoup, category_id: int) -> Dict:
        title = item.find('title').text.strip() if item.find('title') else ''
        description = item.find('description').text.strip() if item.find('description') else ''
        link = item.find('link').text.strip() if item.find('link') else ''
        guid = item.find('guid').text.strip() if item.find('guid') else ''
        pub_date_str = item.find('pubDate').text.strip() if item.find('pubDate') else None
        pub_date = self.parse_date(pub_date_str)

        keywords = self.keyword_extractor.extract_keywords(title) if title else []

        image_url = None
        image_width = None
        image_credit = None
        thumbnail = item.find('media:thumbnail')
        
        if thumbnail:
            image_url = thumbnail.get('url')
            width = thumbnail.get('width')
            image_width = int(width) if width and width.isdigit() else None
            image_credit = 'BBC News'

        return {
            'title': title,
            'url': link,
            'guid': guid,
            'description': description,
            'author': [],  # BBC doesn't provide authors in RSS
            'pub_date': pub_date,
            'category_id': category_id,
            'keywords': keywords,
            'image_url': image_url,
            'image_width': image_width,
            'image_credit': image_credit
        }

    def upsert_articles(self, articles: List[Dict]) -> Tuple[int, int]:
        if not articles:
            return 0, 0

        upsert_query = """
        INSERT INTO bbc.articles (
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
        WHERE bbc.articles.pub_date < EXCLUDED.pub_date
        RETURNING article_id, (xmax = 0) as inserted;
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
        
        results = execute_values(self.cursor, upsert_query, article_data, fetch=True)
        
        if results:
            inserted = sum(1 for r in results if r[1])
            updated = len(results) - inserted
            return inserted, updated
        return 0, 0

    def process_category(self, category_id: int, atom_link: str, category_name: str) -> None:
        try:
            print(f"\nProcessing category {category_id} - {category_name}")
            print(f"Feed URL: {atom_link}")
            
            response = requests.get(atom_link, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'xml')

            items = soup.find_all('item')
            print(f"Found {len(items)} items in feed")

            batch_size = 50
            category_stats = {
                'articles_inserted': 0,
                'articles_updated': 0,
                'articles_with_images': 0,
                'articles_with_keywords': 0
            }

            for i in range(0, len(items), batch_size):
                batch_items = items[i:i + batch_size]
                parsed_articles = [self.parse_article(item, category_id) for item in batch_items]
                
                articles_with_images = sum(1 for a in parsed_articles if a['image_url'])
                articles_with_keywords = sum(1 for a in parsed_articles if a['keywords'])
                
                inserted, updated = self.upsert_articles(parsed_articles)
                self.connection.commit()

                category_stats['articles_inserted'] += inserted
                category_stats['articles_updated'] += updated
                category_stats['articles_with_images'] += articles_with_images
                category_stats['articles_with_keywords'] += articles_with_keywords

            print(f"Category {category_name} processing complete:")
            print(f"- Articles inserted: {category_stats['articles_inserted']}")
            print(f"- Articles updated: {category_stats['articles_updated']}")
            print(f"- Articles with images: {category_stats['articles_with_images']}")
            print(f"- Articles with keywords: {category_stats['articles_with_keywords']}")

            self.stats['total_inserted'] += category_stats['articles_inserted']
            self.stats['total_updated'] += category_stats['articles_updated']
            self.stats['total_with_images'] += category_stats['articles_with_images']
            self.stats['total_with_keywords'] += category_stats['articles_with_keywords']
            self.stats['categories_processed'] += 1

        except requests.RequestException as e:
            print(f"Error fetching feed {atom_link}: {e}")
            self.stats['categories_failed'] += 1
        except Exception as e:
            print(f"Error processing category {category_name}: {e}")
            self.stats['categories_failed'] += 1

    def run(self) -> Dict[str, int]:
        try:
            self.connect_to_db()
            
            print("Fetching BBC categories...")
            self.cursor.execute("""
                SELECT category_id, atom_link, name 
                FROM bbc.categories 
                WHERE atom_link IS NOT NULL 
                ORDER BY category_id;
            """)
            categories = self.cursor.fetchall()
            print(f"Found {len(categories)} categories to process")

            for category_id, atom_link, category_name in categories:
                try:
                    self.process_category(category_id, atom_link, category_name)
                except Exception as e:
                    print(f"Error processing category {category_name}: {e}")
                    continue

            self.stats['total_processed'] = self.stats['total_inserted'] + self.stats['total_updated']

            print("\nProcessing complete. Final statistics:")
            print(f"Categories processed: {self.stats['categories_processed']}")
            print(f"Categories failed: {self.stats['categories_failed']}")
            print(f"Articles inserted: {self.stats['total_inserted']}")
            print(f"Articles updated: {self.stats['total_updated']}")
            print(f"Articles with images: {self.stats['total_with_images']}")
            print(f"Articles with keywords: {self.stats['total_with_keywords']}")

            return self.stats

        except Exception as e:
            print(f"Fatal error: {e}")
            raise
        finally:
            self.close_db_connection()

if __name__ == "__main__":
    try:
        db_config = {
            'dbname': 'news_aggregator',
            'user': 'news_admin',
            'password': 'fasldkflk423mkj4k24jk242',
            'host': 'localhost',
            'port': '5432',
        }
        
        processor = BBCNewsProcessor(db_config)
        processor.run()
    except Exception as e:
        print(f"Script failed: {e}")
        raise