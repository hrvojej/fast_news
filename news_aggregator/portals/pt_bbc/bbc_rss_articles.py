import sys
import os
from datetime import datetime
from typing import List, Dict
from uuid import UUID
import requests
from bs4 import BeautifulSoup
import argparse
from sqlalchemy import text
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
import nltk

current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)
    
from db_scripts.models.models import create_portal_category_model
BBCCategory = create_portal_category_model("pt_bbc")

from db_scripts.models.models import create_portal_article_model
BBCArticle = create_portal_article_model("pt_bbc")

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

class BBCRSSArticlesParser:
    """Parser for BBC RSS feed articles"""
    
    def __init__(self, portal_id: UUID, env: str = 'dev', article_model=None):
        self.portal_id = portal_id
        self.env = env
        self.BBCArticle = article_model
        self.keyword_extractor = KeywordExtractor()

    def get_session(self):
        """Get database session from DatabaseContext."""
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        return db_context.session().__enter__()

    def parse_article(self, item: BeautifulSoup, category_id: UUID) -> Dict:
        """Parse a single BBC RSS item."""
        # Required fields
        title = item.find('title').text.strip() if item.find('title') else 'Untitled'
        link = item.find('link').text.strip() if item.find('link') else 'https://www.bbc.com'
        guid = item.find('guid').text.strip() if item.find('guid') else link
        
        # Optional fields
        description = item.find('description').text.strip() if item.find('description') else None
        content = description
        pub_date_str = item.find('pubDate').text.strip() if item.find('pubDate') else None
        pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S GMT') if pub_date_str else datetime.utcnow()
        
        keywords = self.keyword_extractor.extract_keywords(title) if title else []
        
        image_url = None
        thumbnail = item.find('media:thumbnail')
        if thumbnail:
            image_url = thumbnail.get('url')

        text_content = f"{title} {description or ''}"
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
            'author': [],
            'pub_date': pub_date,
            'keywords': keywords,
            'reading_time_minutes': reading_time,
            'language_code': 'en',
            'image_url': image_url,
            'sentiment_score': 0.0,
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
            categories = session.execute(
                text("""
                    SELECT category_id, atom_link 
                    FROM pt_bbc.categories 
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
                        existing = session.query(self.BBCArticle).filter(
                            self.BBCArticle.guid == article_data['guid']
                        ).first()

                        if not existing:
                            article = self.BBCArticle(**article_data)
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
        """Main method to fetch and store BBC articles."""
        try:
            self.fetch_and_store_articles()
            print("Article processing completed successfully")
        except Exception as e:
            print(f"Error processing articles: {e}")
            raise

def main():
    """Script entry point."""
    argparser = argparse.ArgumentParser(description="BBC RSS Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    try:
        portal_id = fetch_portal_id_by_prefix("pt_bbc", env=args.env)
        parser = BBCRSSArticlesParser(portal_id=portal_id, env=args.env, article_model=BBCArticle)
        parser.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()