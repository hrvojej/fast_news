"""
ABC RSS Articles Parser
Fetches and stores ABC RSS feed articles using SQLAlchemy ORM.
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

# New imports for keyword extraction:
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
import nltk

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Import the dynamic model factory functions for categories and articles
from db_scripts.models.models import create_portal_category_model, create_portal_article_model

# Create the dynamic models for the ABC portal (portal prefix: pt_abc)
ABCCategory = create_portal_category_model("pt_abc")
ABCArticle = create_portal_article_model("pt_abc")


def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
    """Fetches the portal_id from the news_portals table."""
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


class KeywordExtractor:
    """
    Uses a SentenceTransformer model to extract keywords from text.
    """
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
        
        # Split text into individual words (chunks)
        chunks = text.split()
        if not chunks:
            return []
            
        text_embedding = self.model.encode([text])
        chunk_embeddings = self.model.encode(chunks)
        
        similarities = cosine_similarity(text_embedding, chunk_embeddings).flatten()
        scored_chunks = sorted(
            [(chunks[i], score) for i, score in enumerate(similarities)],
            key=lambda x: x[1],
            reverse=True
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


class ABCRSSArticlesParser:
    """Parser for ABC RSS feed articles."""

    def __init__(self, portal_id: UUID, env: str = 'dev', article_model=None):
        self.portal_id = portal_id
        self.env = env
        self.ABCArticle = article_model
        # Instantiate the keyword extractor (SentenceTransformer based)
        self.keyword_extractor = KeywordExtractor()

    def get_session(self):
        """Obtain a database session from the DatabaseContext."""
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        return db_context.session().__enter__()

    def parse_article(self, item: BeautifulSoup, category_id: UUID) -> Dict:
        """Parse a single ABC RSS <item> element."""
        # Required fields
        title_tag = item.find('title')
        title = title_tag.text.strip() if title_tag else 'Untitled'

        link_tag = item.find('link')
        link = link_tag.text.strip() if link_tag else 'https://abcnews.go.com'

        guid_tag = item.find('guid')
        guid = guid_tag.text.strip() if guid_tag else link  # Use link as fallback GUID

        # Optional fields
        description_tag = item.find('description')
        description = description_tag.text.strip() if description_tag else None

        # In this case, we use description as a fallback for content
        content = description

        # Process pubDate: if not present, leave as None (do not insert current timestamp)
        pub_date_tag = item.find('pubDate')
        pub_date = None
        if pub_date_tag:
            pub_date_str = pub_date_tag.text.strip()
            try:
                pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
            except Exception as e:
                print(f"Error parsing pubDate '{pub_date_str}': {e}")
                pub_date = None

        # Authors: ABC feed does not provide an explicit author field, so we leave it empty.
        authors = []

        # ----------------------------
        # NEW: Keyword extraction
        # Instead of relying solely on <category> or media:keywords tags,
        # we now extract keywords from the title using our KeywordExtractor.
        keywords = self.keyword_extractor.extract_keywords(title) if title else []
        # ----------------------------

        # Get image URL from <media:thumbnail> elements.
        image_url = None
        media_thumbnails = item.find_all('media:thumbnail')
        if media_thumbnails:
            valid_thumbnails = []
            for thumb in media_thumbnails:
                url = thumb.get('url')
                width = thumb.get('width')
                if url and width and width.isdigit():
                    valid_thumbnails.append((url, int(width)))
            if valid_thumbnails:
                image_url = max(valid_thumbnails, key=lambda x: x[1])[0]

        # Calculate reading time (estimate: 200 words per minute)
        text_content = f"{title} {description or ''} {content or ''}"
        word_count = len(text_content.split())
        reading_time = max(1, round(word_count / 200)) if word_count > 0 else 1

        return {
            # Required fields
            'title': title,
            'url': link,
            'guid': guid,
            'category_id': category_id,

            # Optional fields
            'description': description,
            'content': content,
            'author': authors,
            'pub_date': pub_date,
            'keywords': keywords,
            'reading_time_minutes': reading_time,
            'language_code': 'en',
            'image_url': image_url,
            'sentiment_score': 0.0,  # Neutral sentiment by default
            'share_count': 0,
            'view_count': 0,
            'comment_count': 0
        }

    def fetch_and_store_articles(self):
        """Fetch and store articles from all ABC RSS feeds."""
        print("Starting fetch_and_store_articles for ABC...")
        session = self.get_session()
        print("Executing categories query...")
        try:
            # Select all active categories that have an atom_link defined
            categories = session.execute(
                text("""
                    SELECT category_id, atom_link 
                    FROM pt_abc.categories 
                    WHERE is_active = true AND atom_link IS NOT NULL
                """)
            ).fetchall()
            print(f"Found {len(categories)} categories.")

            for category_id, atom_link in categories:
                print(f"Processing category: {category_id} with feed URL: {atom_link}")
                try:
                    response = requests.get(atom_link, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'xml')

                    for item in soup.find_all('item'):
                        article_data = self.parse_article(item, category_id)
                        # Check for duplicate based on guid
                        existing = session.query(self.ABCArticle).filter(
                            self.ABCArticle.guid == article_data['guid']
                        ).first()

                        if not existing:
                            article = self.ABCArticle(**article_data)
                            session.add(article)
                            print(f"Added new article: {article_data['title']}")
                        else:
                            # If needed, update the existing record (e.g., if pub_date has changed)
                            if existing.pub_date != article_data['pub_date']:
                                for key, value in article_data.items():
                                    setattr(existing, key, value)
                                print(f"Updated article: {article_data['title']}")

                    session.commit()
                    print(f"Finished processing feed: {atom_link}")

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
        """Main method to fetch and store ABC articles."""
        try:
            self.fetch_and_store_articles()
            print("ABC article processing completed successfully.")
        except Exception as e:
            print(f"Error processing ABC articles: {e}")
            raise


def main():
    """Script entry point."""
    argparser = argparse.ArgumentParser(description="ABC RSS Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    try:
        portal_id = fetch_portal_id_by_prefix("pt_abc", env=args.env)
        parser = ABCRSSArticlesParser(portal_id=portal_id, env=args.env, article_model=ABCArticle)
        parser.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
