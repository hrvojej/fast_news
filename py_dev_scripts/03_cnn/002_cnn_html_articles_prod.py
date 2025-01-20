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
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin
from typing import Dict, List, Optional

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

class CNNNewsProcessor:
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

    def parse_article(self, card: BeautifulSoup, category_id: int, base_url: str) -> Optional[Dict]:
        try:
            link_elem = card.find('a', class_='container__link') or card.find('a', href=True)
            if not link_elem or not link_elem.get('href'):
                return None

            relative_url = link_elem.get('href', '').strip()
            full_url = urljoin(base_url, relative_url)

            title_elem = link_elem.find('span', class_='container__headline-text')
            title = self.clean_text(title_elem.text) if title_elem else None
            if not title:
                headline_div = link_elem.find('div', class_='container__headline')
                title = self.clean_text(headline_div.text) if headline_div else None
            if not title:
                link_text = self.clean_text(link_elem.get_text())
                title = link_text if len(link_text) > 10 else None

            if not title:
                return None

            image = card.find('img')
            image_url = image.get('src') or image.get('data-src') if image else None
            image_width = int(image.get('width')) if image and image.get('width', '').isdigit() else None

            keywords = self.keyword_extractor.extract_keywords(title)

            return {
                'title': title,
                'url': full_url,
                'guid': full_url,
                'description': None,
                'author': [],
                'pub_date': datetime.now(timezone.utc),
                'category_id': category_id,
                'keywords': keywords,
                'image_url': image_url,
                'image_width': image_width,
                'image_credit': 'CNN'
            }
        except Exception as e:
            print(f"Error parsing article: {e}")
            return None

    def connect_to_db(self):
        print("Connecting to PostgreSQL...")
        self.connection = psycopg2.connect(**self.db_config)
        self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ)
        self.cursor = self.connection.cursor()

    def close_db_connection(self):
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection and not self.connection.closed:
                self.connection.close()
                print("Database connection closed.")
        except Exception as e:
            print(f"Error closing database connection: {e}")

    def process_batch(self, batch_items: List[BeautifulSoup], category_id: int, base_url: str) -> Dict[str, int]:
        batch_stats = {
            'articles_inserted': 0,
            'articles_updated': 0,
            'articles_with_images': 0,
            'articles_with_keywords': 0
        }

        try:
            parsed_articles = [self.parse_article(card, category_id, base_url) for card in batch_items]
            parsed_articles = [a for a in parsed_articles if a]

            if not parsed_articles:
                return batch_stats

            batch_stats['articles_with_images'] = sum(1 for a in parsed_articles if a['image_url'])
            batch_stats['articles_with_keywords'] = sum(1 for a in parsed_articles if a['keywords'])

            # Insert articles logic placeholder
            # inserted, updated = self.upsert_articles(parsed_articles)
            # self.connection.commit()

            return batch_stats
        except Exception as e:
            self.connection.rollback()
            print(f"Error processing batch: {e}")
            return batch_stats

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        cleaned = re.sub(r'\s+', ' ', text.strip())
        cleaned = ''.join(char for char in cleaned if unicodedata.category(char)[0] != "C")
        return cleaned

if __name__ == "__main__":
    db_config = {
        'dbname': 'news_aggregator',
        'user': 'news_admin',
        'password': 'fasldkflk423mkj4k24jk242',
        'host': 'localhost',
        'port': '5432'
    }

    processor = CNNNewsProcessor(db_config)
    processor.run() 
    processor.connect_to_db()
    processor.close_db_connection()
