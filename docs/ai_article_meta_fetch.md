Based on this script:
#!/usr/bin/env python
"""
ABC RSS Articles Parser
Fetches and stores ABC RSS feed articles using SQLAlchemy ORM.

Timestamps are normalized to UTC for both storage and comparison, ensuring that 
updates occur only when there is an actual change in the absolute publication time.
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

        # Process pubDate: if not present, leave as None
        pub_date_tag = item.find('pubDate')
        pub_date = None
        if pub_date_tag:
            pub_date_str = pub_date_tag.text.strip()
            try:
                # Convert parsed date to UTC for consistent storage
                pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z').astimezone(timezone.utc)
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

        # Counters and details for reporting.
        new_articles_count = 0
        updated_articles_count = 0
        updated_articles_details = []  # list of tuples (article title, old pub_date, new pub_date)

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
                print(f"\nProcessing category: {atom_link}")
                try:
                    response = requests.get(atom_link, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'xml')

                    # Get all articles (items) and calculate total count.
                    items = soup.find_all('item')
                    total_articles = len(items)
                    print(f"Found {total_articles} articles in feed {atom_link}.")

                    for article_index, item in enumerate(items, start=1):
                        article_data = self.parse_article(item, category_id)
                        # Check for duplicate based on guid
                        existing = session.query(self.ABCArticle).filter(
                            self.ABCArticle.guid == article_data['guid']
                        ).first()

                        if not existing:
                            article = self.ABCArticle(**article_data)
                            session.add(article)
                            new_articles_count += 1
                            print(f"Added new article: {article_data['title']}")
                        else:
                            # Normalize both datetime objects to UTC before comparing.
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
                                updated_articles_details.append(
                                    (article_data['title'], old_pub_date, new_pub_date)
                                )
                                print(f"Updated article: {article_data['title']}")
                    session.commit()
                    print(f"Finished processing feed: {atom_link}")

                except Exception as e:
                    print(f"Error processing feed {atom_link}: {e}")
                    session.rollback()
                    continue

            # Final reporting
            print("\nFinal Report:")
            print(f"Newly added articles: {new_articles_count}")
            print(f"Updated articles: {updated_articles_count}")
            if updated_articles_details:
                print("\nDetails of updated articles:")
                for title, old_date, new_date in updated_articles_details:
                    print(f" - Article '{title}': pub_date in DB: {old_date}, pub_date online: {new_date}")

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

# Here is current bbc script that needs to be modified following example above. BBC related extraction logic should remain as. All other features from above should implemented except that

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
                print("Processing category:", atom_link)
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

Ask if something is not clear. Do not assume. 

# #### Answers to AI questions

I want to make sure I fully understand your requirements before proceeding. Here are a few points I’d like to clarify:

UTC Normalization:
In the ABC script the publication date is parsed and normalized to UTC. For the BBC script, do you want the publication date parsing to be updated to include UTC normalization (for example, using something like .astimezone(timezone.utc) or setting the appropriate timezone)? YES.

Article Update Logic and Reporting:
The ABC script keeps track of new and updated articles (with counts and details about updates). Should the BBC script be modified to include similar reporting (e.g., counts of newly added articles and updated articles, along with details such as the old and new publication dates)? Yes.

Keyword Extraction & Other Common Features:
The ABC script uses a KeywordExtractor based on SentenceTransformer and includes keyword extraction from the title. The BBC script already has this extractor, so should it remain the same? YES.
 Are there any additional features (like reading time calculation, sentiment score initialization, etc.) from the ABC script that you want to add to the BBC version? All other features from ABC should be in BBC. 

BBC-Specific Extraction Logic:
You mentioned that “BBC related extraction logic should remain as.” Does that mean:

The way the BBC script handles fields such as title, link, description, and image URL should not be altered? Yes because they are related to BBC HTML pages which are specific. 
The specific date parsing format (e.g., using %a, %d %b %Y %H:%M:%S GMT) should remain, aside from adding UTC normalization? NO, it should be converted to normalized UTC as it is in ABC example. 
Exceptions or “Except That” Clause:
Your instruction ends with “All other features from above should implemented except that” — could you please clarify what should not be implemented or what exceptions there are? There are no exceptions - only stuff related to BBC HTML pages are specific, thats all. 