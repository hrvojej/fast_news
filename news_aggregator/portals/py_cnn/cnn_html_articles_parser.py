"""
CNN Articles Parser
Fetches and stores CNN articles using SQLAlchemy ORM.
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
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
import nltk
import re
import unicodedata
from urllib.parse import urljoin

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Category model creation
from db_scripts.models.models import create_portal_category_model
CNNCategory = create_portal_category_model("pt_cnn")

# Create the dynamic article model for CNN portal
from db_scripts.models.models import create_portal_article_model
CNNArticle = create_portal_article_model("pt_cnn")

def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
    """Fetches the portal_id from news_portals table."""
    print(f"[DEBUG] Fetching portal ID for prefix: {portal_prefix}, env: {env}")
    from db_scripts.db_context import DatabaseContext
    db_context = DatabaseContext.get_instance(env)
    with db_context.session() as session:
        result = session.execute(
            text("SELECT portal_id FROM public.news_portals WHERE portal_prefix = :prefix"),
            {'prefix': portal_prefix}
        ).fetchone()
        if result:
            print(f"[DEBUG] Found portal ID: {result[0]}")
            return result[0]
        print(f"[DEBUG] No portal found for prefix: {portal_prefix}")
        raise Exception(f"Portal with prefix '{portal_prefix}' not found.")

class KeywordExtractor:
    """Extracts keywords from text using sentence transformers."""
    
    def __init__(self):
        print("[DEBUG] Initializing KeywordExtractor")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        try:
            self.stop_words = set(stopwords.words('english'))
        except LookupError:
            print("[DEBUG] Downloading stopwords")
            nltk.download('stopwords')
            self.stop_words = set(stopwords.words('english'))
        print("[DEBUG] KeywordExtractor initialized")
    
    def extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        print(f"[DEBUG] Extracting keywords from text: {text[:50]}...")
        if not text:
            print("[DEBUG] Empty text, returning empty keywords")
            return []
        
        chunks = text.split()
        if not chunks:
            print("[DEBUG] No chunks found, returning empty keywords")
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
        for word, score in scored_chunks:
            word = word.lower()
            if word not in self.stop_words and word not in seen and len(word) > 2:
                keywords.append(word)
                seen.add(word)
                print(f"[DEBUG] Added keyword: {word} (score: {score:.3f})")
            if len(keywords) >= max_keywords:
                break
        print(f"[DEBUG] Extracted keywords: {keywords}")
        return keywords

class CNNArticlesParser:
    """Parser for CNN articles"""

    def __init__(self, portal_id: UUID, env: str = 'dev', article_model=None):
        print(f"[DEBUG] Initializing CNNArticlesParser with portal_id: {portal_id}, env: {env}")
        self.portal_id = portal_id
        self.env = env
        self.CNNArticle = article_model
        self.keyword_extractor = KeywordExtractor()
        print("[DEBUG] CNNArticlesParser initialized")

    def get_session(self):
        """Get database session from DatabaseContext."""
        print("[DEBUG] Getting database session")
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        session = db_context.session().__enter__()
        print("[DEBUG] Database session obtained")
        return session

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean text from special characters and normalize whitespace"""
        print(f"[DEBUG] Cleaning text: {text[:50]}...")
        if not text:
            print("[DEBUG] Empty text, returning empty string")
            return ""
            
        cleaned = text.strip()
        cleaned = re.sub(r'[\n\r\t\f\v]+', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'[^\S\r\n]+', ' ', cleaned)
        cleaned = re.sub(r'¶|•|■|▪|►|▼|▲|◄|★|☆|⚡', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = "".join(char for char in cleaned if unicodedata.category(char)[0] != "C")
        result = cleaned.strip()
        print(f"[DEBUG] Cleaned text result: {result[:50]}...")
        return result

    def fetch_page_with_retry(self, url: str, max_retries: int = 3) -> str:
        """Fetch page content with retry mechanism"""
        print(f"[DEBUG] Fetching URL with retry: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }

        for attempt in range(max_retries):
            try:
                print(f"[DEBUG] Attempt {attempt + 1}/{max_retries}")
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                print(f"[DEBUG] Successfully fetched URL: {url}")
                return response.text
            except requests.RequestException as e:
                print(f"[DEBUG] Request failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                print("[DEBUG] Retrying...")
                time.sleep(2)

    def parse_article(self, card: BeautifulSoup, category_id: UUID, base_url: str) -> Dict:
        """Parse a single CNN article card."""
        print("[DEBUG] Starting article parsing")
        link_elem = card.find('a', class_='container__link') or card.find('a', href=True)
        if not link_elem or not link_elem.get('href'):
            print("[DEBUG] No valid link element found")
            return None

        relative_url = link_elem.get('href', '').strip()
        full_url = urljoin(base_url, relative_url)
        print(f"[DEBUG] Processing article URL: {full_url}")

        # Extract title
        title = None
        title_elem = link_elem.find('span', class_='container__headline-text')
        if title_elem:
            title = self.clean_text(title_elem.text)
            print(f"[DEBUG] Found title from headline-text: {title}")
        if not title:
            headline_div = link_elem.find('div', class_='container__headline')
            if headline_div:
                title = self.clean_text(headline_div.text)
                print(f"[DEBUG] Found title from headline div: {title}")
        if not title:
            link_text = self.clean_text(link_elem.get_text())
            if len(link_text) > 10:
                title = link_text
                print(f"[DEBUG] Using link text as title: {title}")

        if not title or len(title) < 10:
            print("[DEBUG] No valid title found")
            return None

        # Clean the title
        title = re.sub(r'►\s*Video\s*►\s*', '', title)
        title = re.sub(r'▶\s*', '', title)
        title = re.sub(r'\s*\d+:\d+\s*$', '', title)
        print(f"[DEBUG] Cleaned title: {title}")

        # Extract image
        image = card.find('img')
        image_url = None
        image_width = None
        if image:
            image_url = image.get('src') or image.get('data-src')
            image_width = int(image.get('width')) if image.get('width') and image.get('width').isdigit() else None
            print(f"[DEBUG] Found image: {image_url}, width: {image_width}")

        # Calculate reading time
        text_content = title
        word_count = len(text_content.split())
        reading_time = max(1, round(word_count / 200))
        print(f"[DEBUG] Calculated reading time: {reading_time} minutes")

        # Extract keywords
        keywords = self.keyword_extractor.extract_keywords(title) if title else []
        print(f"[DEBUG] Extracted keywords: {keywords}")

        article_data = {
            'title': title,
            'url': full_url,
            'guid': full_url,
            'category_id': category_id,
            'description': None,
            'content': None,
            'author': [],
            'pub_date': None,  # Leave empty since we don't have actual pub date
            'keywords': keywords,
            'reading_time_minutes': reading_time,
            'language_code': 'en',
            'image_url': image_url,
            'sentiment_score': 0.0,
            'share_count': 0,
            'view_count': 0,
            'comment_count': 0
        }
        print(f"[DEBUG] Created article data: {article_data}")
        return article_data

    def fetch_and_store_articles(self):
        """Fetch and store articles from all CNN categories."""
        print("[DEBUG] Starting fetch_and_store_articles")
        session = self.get_session()
        print("[DEBUG] Executing categories query")
        try:
            categories = session.execute(
                text("""
                    SELECT category_id, link, name 
                    FROM pt_cnn.categories 
                    WHERE is_active = true 
                    AND link IS NOT NULL 
                    AND link != '' 
                    ORDER BY category_id;
                """)
            ).fetchall()
            print(f"[DEBUG] Found {len(categories)} categories")

            for category_id, link, category_name in categories:
                print(f"[DEBUG] Processing category: {category_name}")
                try:
                    html_content = self.fetch_page_with_retry(link)
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    article_cards = []
                    for selector in ['div[data-component-name="card"]', 'div.container__item', 'div[data-uri*="card"]']:
                        if not article_cards:
                            article_cards = soup.select(selector)
                    print(f"[DEBUG] Found {len(article_cards)} article cards")

                    for idx, card in enumerate(article_cards, 1):
                        print(f"[DEBUG] Processing article {idx}/{len(article_cards)}")
                        article_data = self.parse_article(card, category_id, link)
                        if article_data:
                            # Check if article already exists by URL
                            existing = session.query(self.CNNArticle).filter(
                                self.CNNArticle.url == article_data['url']
                            ).first()

                            if not existing:
                                print(f"[DEBUG] Adding new article: {article_data['title']}")
                                article = self.CNNArticle(**article_data)
                                session.add(article)
                                session.commit()
                            else:
                                print(f"[DEBUG] Article already exists, skipping: {article_data['title']}")

                    session.commit()
                    print(f"[DEBUG] Successfully processed category {category_name}")
                    
                except Exception as e:
                    print(f"[DEBUG] Error processing category {category_name}: {str(e)}")
                    session.rollback()
                    continue

        except Exception as e:
            print(f"[DEBUG] Error in fetch_and_store_articles: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()
            print("[DEBUG] Database session closed")

    def run(self):
        """Main method to fetch and store CNN articles."""
        print("[DEBUG] Starting CNN parser run")
        try:
            self.fetch_and_store_articles()
            print("[DEBUG] Article processing completed successfully")
        except Exception as e:
            print(f"[DEBUG] Error processing articles: {str(e)}")
            raise

def main():
    """Script entry point."""
    print("[DEBUG] Starting main function")
    argparser = argparse.ArgumentParser(description="CNN Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()
    print(f"[DEBUG] Parsed arguments: {args}")

    try:
        portal_id = fetch_portal_id_by_prefix("pt_cnn", env=args.env)
        print(f"[DEBUG] Fetched portal_id: {portal_id}")
        parser = CNNArticlesParser(portal_id=portal_id, env=args.env, article_model=CNNArticle)
        parser.run()
        print("[DEBUG] Parser run completed")
    except Exception as e:
        print(f"[DEBUG] Script execution failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()