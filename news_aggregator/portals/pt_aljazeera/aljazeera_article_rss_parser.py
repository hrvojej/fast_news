#!/usr/bin/env python
"""
Al Jazeera RSS Articles Parser
Fetches and stores Al Jazeera RSS feed articles using SQLAlchemy ORM.
Converts publication dates to UTC before storing/comparing.
"""

import sys
import os
from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID
import requests
from bs4 import BeautifulSoup
import argparse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from urllib.parse import urlparse

# --- New imports for keyword extraction ---
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
import nltk
# ------------------------------------------

# Add package root to path (adjust if needed)
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Import the dynamic model factory and category model creation
from db_scripts.models.models import create_portal_category_model, create_portal_article_model

# Create the dynamic models for the Al Jazeera portal using its schema prefix "pt_aljazeera"
AlJazeeraCategory = create_portal_category_model("pt_aljazeera")
AlJazeeraArticle = create_portal_article_model("pt_aljazeera")

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

# --- Keyword Extraction Class ---
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
        
        # Split the text into individual words (chunks)
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
# --------------------------------

class AlJazeeraRSSArticlesParser:
    """Parser for Al Jazeera RSS feed articles."""
    
    FEED_URL = "https://www.aljazeera.com/xml/rss/all.xml"
    
    def __init__(self, portal_id: UUID, env: str = 'dev', article_model=None):
        self.portal_id = portal_id
        self.env = env
        self.AlJazeeraArticle = article_model
        # Initialize the keyword extractor
        self.keyword_extractor = KeywordExtractor()
    
    def get_session(self):
        """Obtain a database session from the DatabaseContext."""
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        return db_context.session().__enter__()
    
    def parse_article(self, item: BeautifulSoup, category_id: UUID) -> Dict:
        """Parse a single Al Jazeera RSS <item> element."""
        # Required fields
        title_tag = item.find('title')
        title = title_tag.text.strip() if title_tag else 'Untitled'
        
        link_tag = item.find('link')
        link = link_tag.text.strip() if link_tag else "https://www.aljazeera.com"
        
        guid_tag = item.find('guid')
        guid = guid_tag.text.strip() if guid_tag else link  # Fallback to the link
        
        # Optional fields
        description_tag = item.find('description')
        description = description_tag.text.strip() if description_tag else None
        content = description  # Fallback to description
        
        # Process pubDate and convert to UTC for consistent storage/comparison.
        pub_date = None
        pub_date_tag = item.find('pubDate')
        if pub_date_tag:
            pub_date_str = pub_date_tag.text.strip()
            try:
                pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z').astimezone(timezone.utc)
            except Exception as e:
                print(f"Error parsing pubDate '{pub_date_str}': {e}")
                pub_date = None
        
        # Authors: typically no author info in Al Jazeera items.
        authors = []
        
        # Keyword extraction from title
        keywords = self.keyword_extractor.extract_keywords(title) if title else []
        
        # Get image URL from media:content elements.
        image_url = None
        media_contents = item.find_all('media:content')
        if media_contents:
            valid_media = []
            for media in media_contents:
                url = media.get('url')
                width = media.get('width')
                if url and width and width.isdigit():
                    valid_media.append((url, int(width)))
            if valid_media:
                image_url = max(valid_media, key=lambda x: x[1])[0]
        
        # Calculate reading time (estimate: 200 words per minute)
        text_content = f"{title} {description or ''} {content or ''}"
        word_count = len(text_content.split())
        reading_time = max(1, round(word_count / 200)) if word_count > 0 else 1
        
        return {
            'title': title,
            'url': link,
            'guid': guid,
            'category_id': category_id,
            'description': description,
            'content': content,
            'author': authors,
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
    
    def get_or_create_category(self, session, category_text, derived_slug, derived_name, derived_link, category_cache):
        """
        Returns the category_id by first checking the provided category (if any),
        then the derived slug. It consults the in‑memory cache, then the DB,
        and finally inserts a new category if needed.
        """
        # If a category was provided in the item, try to look it up by name.
        if category_text:
            result = session.execute(
                text("SELECT category_id, slug FROM pt_aljazeera.categories WHERE name = :name"),
                {'name': category_text}
            ).fetchone()
            if result:
                cat_id, cat_slug = result
                category_cache[cat_slug] = cat_id
                return cat_id
        
        # Fall back to using the derived category info.
        if derived_slug in category_cache:
            return category_cache[derived_slug]
        
        # Check the DB by the derived slug.
        result = session.execute(
            text("SELECT category_id FROM pt_aljazeera.categories WHERE slug = :slug"),
            {'slug': derived_slug}
        ).fetchone()
        if result:
            cat_id = result[0]
            category_cache[derived_slug] = cat_id
            return cat_id
        
        # Not found: insert a new category.
        new_category = AlJazeeraCategory(
            name=derived_name,
            slug=derived_slug,
            portal_id=self.portal_id,
            path=derived_link,
            level=1,
            description=None,
            link=derived_link,
            atom_link=derived_link,
            is_active=True
        )
        session.add(new_category)
        try:
            session.commit()
        except IntegrityError as e:
            session.rollback()
            result = session.execute(
                text("SELECT category_id FROM pt_aljazeera.categories WHERE slug = :slug"),
                {'slug': derived_slug}
            ).fetchone()
            if result:
                cat_id = result[0]
                category_cache[derived_slug] = cat_id
                return cat_id
            else:
                raise e
        cat_id = new_category.category_id
        category_cache[derived_slug] = cat_id
        return cat_id
    
    def fetch_and_store_articles(self):
        """Fetch the Al Jazeera RSS feed and store (or update) its articles in the DB."""
        print("Starting fetch_and_store_articles for Al Jazeera...")
        session = self.get_session()
        new_articles_count = 0
        updated_articles_count = 0
        updated_articles_details = []
        try:
            print(f"Fetching RSS feed from: {self.FEED_URL}")
            response = requests.get(self.FEED_URL, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'xml')
            print("RSS feed fetched and parsed.")
            
            # Cache for category lookups
            category_cache = {}
            items = soup.find_all('item')
            print(f"Found {len(items)} articles in the feed.")
            
            for item in items:
                link_elem = item.find('link')
                if not link_elem or not link_elem.text.strip():
                    continue
                link = link_elem.text.strip()
                
                # Derive category information from the link.
                parsed_url = urlparse(link)
                path_segments = [seg for seg in parsed_url.path.split('/') if seg]
                if len(path_segments) < 2:
                    continue
                phrase1, phrase2 = path_segments[0], path_segments[1]
                derived_category_name = f"{phrase1.capitalize()}_{phrase2.capitalize()}"
                derived_category_slug = derived_category_name.lower()
                derived_category_link = f"{parsed_url.scheme}://{parsed_url.netloc}/{phrase1}/{phrase2}/"
                
                # Check if a <category> element is provided.
                category_elem = item.find('category')
                category_text = category_elem.text.strip() if category_elem and category_elem.text.strip() else None
                
                # Get or create the category.
                category_id = self.get_or_create_category(
                    session,
                    category_text,
                    derived_category_slug,
                    derived_category_name,
                    derived_category_link,
                    category_cache
                )
                
                # Parse the article.
                article_data = self.parse_article(item, category_id)
                
                # Check for duplicate based on guid.
                existing = session.query(self.AlJazeeraArticle).filter(
                    self.AlJazeeraArticle.guid == article_data['guid']
                ).first()
                
                if not existing:
                    article = self.AlJazeeraArticle(**article_data)
                    session.add(article)
                    new_articles_count += 1
                else:
                    update_needed = False
                    if existing.pub_date and article_data['pub_date']:
                        if existing.pub_date.astimezone(timezone.utc) != article_data['pub_date'].astimezone(timezone.utc):
                            update_needed = True
                    elif existing.pub_date != article_data['pub_date']:
                        update_needed = True
                    if update_needed:
                        old_pub_date = existing.pub_date
                        new_pub_date = article_data['pub_date']
                        for key, value in article_data.items():
                            setattr(existing, key, value)
                        updated_articles_count += 1
                        updated_articles_details.append((article_data['title'], old_pub_date, new_pub_date))
            
            session.commit()
            print("\nFinal Report:")
            print(f"Newly added articles: {new_articles_count}")
            print(f"Updated articles: {updated_articles_count}")
            if updated_articles_details:
                print("\nDetails of updated articles:")
                for title, old_date, new_date in updated_articles_details:
                    print(f" - Article '{title}': pub_date in DB: {old_date}, pub_date online: {new_date}")
            print("All articles processed and committed successfully.")
        except Exception as e:
            print(f"Error processing articles: {e}")
            session.rollback()
            raise
        finally:
            session.close()
            print("Database session closed.")
    
    def run(self):
        """Main method to execute the article fetching and storing process."""
        try:
            self.fetch_and_store_articles()
            print("Al Jazeera article processing completed successfully.")
        except Exception as e:
            print(f"Error processing Al Jazeera articles: {e}")
            raise

def main():
    """Script entry point."""
    argparser = argparse.ArgumentParser(description="Al Jazeera RSS Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()
    
    try:
        portal_id = fetch_portal_id_by_prefix("pt_aljazeera", env=args.env)
        parser = AlJazeeraRSSArticlesParser(
            portal_id=portal_id,
            env=args.env,
            article_model=AlJazeeraArticle
        )
        parser.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()
