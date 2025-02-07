#!/usr/bin/env python
"""
Al Jazeera RSS Articles Parser
Fetches and stores Al Jazeera RSS feed articles using SQLAlchemy ORM.
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
    print(f"[DEBUG] Fetching portal_id for prefix '{portal_prefix}' in env '{env}'")
    from db_scripts.db_context import DatabaseContext
    db_context = DatabaseContext.get_instance(env)
    with db_context.session() as session:
        result = session.execute(
            text("SELECT portal_id FROM public.news_portals WHERE portal_prefix = :prefix"),
            {'prefix': portal_prefix}
        ).fetchone()
        if result:
            portal_id = result[0]
            print(f"[DEBUG] Found portal_id: {portal_id}")
            return portal_id
        raise Exception(f"Portal with prefix '{portal_prefix}' not found.")

# --- Keyword Extraction Class ---
class KeywordExtractor:
    def __init__(self):
        print("[DEBUG] Initializing KeywordExtractor...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        try:
            self.stop_words = set(stopwords.words('english'))
        except LookupError:
            nltk.download('stopwords')
            self.stop_words = set(stopwords.words('english'))
        print("[DEBUG] KeywordExtractor initialized.")

    def extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        if not text:
            print("[DEBUG] No text provided for keyword extraction.")
            return []
        
        # Split the text into individual words (chunks)
        chunks = text.split()
        if not chunks:
            print("[DEBUG] No words found in text for keyword extraction.")
            return []
            
        # Compute the embedding for the entire text and for each word
        print(f"[DEBUG] Extracting embeddings for text: '{text[:30]}...'")
        text_embedding = self.model.encode([text])
        chunk_embeddings = self.model.encode(chunks)
        
        # Compute cosine similarity between the text and each word embedding
        similarities = cosine_similarity(text_embedding, chunk_embeddings).flatten()
        scored_chunks = sorted(
            [(chunks[i], score) for i, score in enumerate(similarities)],
            key=lambda x: x[1], reverse=True
        )
        
        # Select keywords that are not stop words and are unique
        keywords = []
        seen = set()
        for word, _ in scored_chunks:
            word = word.lower()
            if word not in self.stop_words and word not in seen and len(word) > 2:
                keywords.append(word)
                seen.add(word)
            if len(keywords) >= max_keywords:
                break
        print(f"[DEBUG] Extracted keywords: {keywords}")
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
        print("[DEBUG] Initializing AlJazeeraRSSArticlesParser...")
        self.keyword_extractor = KeywordExtractor()
        print("[DEBUG] AlJazeeraRSSArticlesParser initialized.")

    def get_session(self):
        """Obtain a database session from the DatabaseContext."""
        print(f"[DEBUG] Obtaining database session for env: {self.env}")
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        session = db_context.session().__enter__()
        print("[DEBUG] Database session obtained.")
        return session

    def parse_article(self, item: BeautifulSoup, category_id: UUID) -> Dict:
        """Parse a single Al Jazeera RSS `<item>` element."""
        print("[DEBUG] Parsing an article item...")
        # Required fields
        title = item.find('title').text.strip() if item.find('title') else 'Untitled'
        link = item.find('link').text.strip() if item.find('link') else "https://www.aljazeera.com"
        guid = item.find('guid').text.strip() if item.find('guid') else link  # Fallback to the link

        # Optional fields (leave empty if not present)
        description = item.find('description').text.strip() if item.find('description') else None
        content = description  # No separate content element; fallback to description

        pub_date_str = item.find('pubDate').text.strip() if item.find('pubDate') else None
        pub_date = None
        if pub_date_str:
            try:
                pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
            except Exception as e:
                print(f"[DEBUG] Error parsing pubDate '{pub_date_str}': {e}")
                pub_date = None

        # Authors: Al Jazeera items typically do not include author info.
        authors = []

        # --- Keywords Extraction ---
        print(f"[DEBUG] Extracting keywords for title: '{title[:30]}...'")
        keywords = self.keyword_extractor.extract_keywords(title) if title else []
        # ---------------------------

        # Get image information (if present)
        image_url = None
        media_contents = item.find_all('media:content')
        if media_contents:
            valid_media = []
            for media in media_contents:
                width = media.get('width')
                if width and width.isdigit():
                    valid_media.append((media.get('url'), int(width)))
            if valid_media:
                # Use the media content with the greatest width
                image_url = max(valid_media, key=lambda x: x[1])[0]

        # Calculate reading time (rough estimate: 200 words per minute)
        text_content = f"{title} {description or ''} {content or ''}"
        word_count = len(text_content.split())
        reading_time = max(1, round(word_count / 200))
        
        print(f"[DEBUG] Finished parsing article: '{title[:30]}...'")
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
            'sentiment_score': 0.0,  # Default neutral sentiment
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
        print(f"[DEBUG] Resolving category for '{derived_name}' with slug '{derived_slug}'")
        # If a category was provided in the item, try to look it up by name.
        if category_text:
            result = session.execute(
                text("SELECT category_id, slug FROM pt_aljazeera.categories WHERE name = :name"),
                {'name': category_text}
            ).fetchone()
            if result:
                cat_id, cat_slug = result
                category_cache[cat_slug] = cat_id
                print(f"[DEBUG] Found category in DB by name: {cat_id}")
                return cat_id

        # Fall back to using the derived category info.
        if derived_slug in category_cache:
            print(f"[DEBUG] Found category in cache: {category_cache[derived_slug]}")
            return category_cache[derived_slug]

        # Check the DB by the derived slug.
        result = session.execute(
            text("SELECT category_id FROM pt_aljazeera.categories WHERE slug = :slug"),
            {'slug': derived_slug}
        ).fetchone()
        if result:
            cat_id = result[0]
            category_cache[derived_slug] = cat_id
            print(f"[DEBUG] Found category in DB by slug: {cat_id}")
            return cat_id

        # Not found: insert a new category.
        print(f"[DEBUG] Inserting new category: {derived_name} with link {derived_link}")
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
            session.commit()  # commit to get the new category_id
            print(f"[DEBUG] New category inserted with id: {new_category.category_id}")
        except IntegrityError as e:
            session.rollback()
            print(f"[DEBUG] IntegrityError while inserting category: {e}")
            # In case of a duplicate (race condition), re-query the category.
            result = session.execute(
                text("SELECT category_id FROM pt_aljazeera.categories WHERE slug = :slug"),
                {'slug': derived_slug}
            ).fetchone()
            if result:
                cat_id = result[0]
                category_cache[derived_slug] = cat_id
                print(f"[DEBUG] Retrieved duplicate category id: {cat_id}")
                return cat_id
            else:
                raise e
        cat_id = new_category.category_id
        category_cache[derived_slug] = cat_id
        return cat_id

    def fetch_and_store_articles(self):
        """Fetch the Al Jazeera RSS feed and store (or update) its articles in the DB."""
        print("[DEBUG] Starting fetch_and_store_articles...")
        session = self.get_session()
        try:
            print(f"[DEBUG] Fetching RSS feed from: {self.FEED_URL}")
            response = requests.get(self.FEED_URL, timeout=10)
            response.raise_for_status()
            print(f"[DEBUG] RSS feed fetched. Status code: {response.status_code}")
            soup = BeautifulSoup(response.content, 'xml')
            print("[DEBUG] RSS feed parsed into BeautifulSoup object.")

            # Cache to avoid repeated DB lookups for the same derived category.
            # The cache key is the derived slug (e.g. "program_newsfeed").
            category_cache = {}

            items = soup.find_all('item')
            print(f"[DEBUG] Found {len(items)} articles in the feed.")

            for idx, item in enumerate(items, start=1):
                print(f"[DEBUG] Processing article {idx}/{len(items)}")
                # Get the article link; if missing, skip the article.
                link_elem = item.find('link')
                if not link_elem or not link_elem.text.strip():
                    print("[DEBUG] No link found for article, skipping.")
                    continue
                link = link_elem.text.strip()

                # Derive category information from the link.
                parsed_url = urlparse(link)
                path_segments = [seg for seg in parsed_url.path.split('/') if seg]
                if len(path_segments) < 2:
                    print(f"[DEBUG] Not enough segments in link {link} to derive category, skipping article.")
                    continue
                phrase1, phrase2 = path_segments[0], path_segments[1]
                derived_category_name = f"{phrase1.capitalize()}_{phrase2.capitalize()}"
                derived_category_slug = derived_category_name.lower()
                derived_category_link = f"{parsed_url.scheme}://{parsed_url.netloc}/{phrase1}/{phrase2}/"

                # Check if a <category> element is provided.
                category_elem = item.find('category')
                category_text = category_elem.text.strip() if category_elem and category_elem.text.strip() else None

                # Get (or create) the category_id using our helper.
                category_id = self.get_or_create_category(
                    session,
                    category_text,
                    derived_category_slug,
                    derived_category_name,
                    derived_category_link,
                    category_cache
                )

                # Parse the article using the determined category_id.
                article_data = self.parse_article(item, category_id)

                # Check for duplicates by GUID.
                existing = session.query(self.AlJazeeraArticle).filter(
                    self.AlJazeeraArticle.guid == article_data['guid']
                ).first()

                if not existing:
                    article = self.AlJazeeraArticle(**article_data)
                    session.add(article)
                    print(f"[DEBUG] Inserted new article: '{article_data['title'][:30]}...'")
                elif existing.pub_date != article_data['pub_date']:
                    # Update the existing record if the publication date has changed.
                    for key, value in article_data.items():
                        setattr(existing, key, value)
                    print(f"[DEBUG] Updated article: '{article_data['title'][:30]}...'")
                else:
                    print(f"[DEBUG] Article already exists and is up-to-date: '{article_data['title'][:30]}...'")

            session.commit()
            print("[DEBUG] All articles processed and committed successfully.")
        except Exception as e:
            print(f"[DEBUG] Error processing articles: {e}")
            session.rollback()
            raise
        finally:
            session.close()
            print("[DEBUG] Database session closed.")

    def run(self):
        """Main method to execute the article fetching and storing process."""
        print("[DEBUG] Running the Al Jazeera RSS Articles Parser...")
        try:
            self.fetch_and_store_articles()
            print("[DEBUG] Article processing completed successfully.")
        except Exception as e:
            print(f"[DEBUG] Error running parser: {e}")
            raise

def main():
    """Script entry point."""
    print("[DEBUG] Starting main()...")
    argparser = argparse.ArgumentParser(description="Al Jazeera RSS Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()
    print(f"[DEBUG] Arguments parsed: {args}")

    try:
        portal_id = fetch_portal_id_by_prefix("pt_aljazeera", env=args.env)
        parser = AlJazeeraRSSArticlesParser(
            portal_id=portal_id,
            env=args.env,
            article_model=AlJazeeraArticle
        )
        parser.run()
    except Exception as e:
        print(f"[DEBUG] Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()
