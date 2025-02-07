"""
Fox News RSS Articles Parser
Fetches and stores Fox News RSS feed articles using SQLAlchemy ORM.
"""

import sys
import os
from datetime import datetime
from typing import List, Dict
from uuid import UUID
import requests
from bs4 import BeautifulSoup
import argparse
from sqlalchemy import text

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Create the dynamic category model for Fox News portal
from db_scripts.models.models import create_portal_category_model
FoxNewsCategory = create_portal_category_model("pt_fox")

# Import the dynamic article model factory
from db_scripts.models.models import create_portal_article_model

# Create the dynamic article model for Fox News portal
FoxNewsArticle = create_portal_article_model("pt_fox")

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

class FoxNewsRSSArticlesParser:
    """Parser for Fox News RSS feed articles"""

    def __init__(self, portal_id: UUID, env: str = 'dev', article_model=None):
        self.portal_id = portal_id
        self.env = env
        self.FoxNewsArticle = article_model

    def get_session(self):
        """Get database session from DatabaseContext."""
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        return db_context.session().__enter__()

    def parse_article(self, item: BeautifulSoup, category_id: UUID) -> Dict:
        """Parse a single Fox News RSS item."""
        # Required fields
        title = item.find('title').text.strip() if item.find('title') else 'Untitled'
        link = item.find('link').text.strip() if item.find('link') else 'https://www.foxnews.com'
        guid = item.find('guid').text.strip() if item.find('guid') else link  # Use URL as fallback GUID

        # Optional fields with defaults
        description = item.find('description').text.strip() if item.find('description') else None

        # Attempt to use <content:encoded> if available, otherwise fallback to description
        content_tag = item.find('content:encoded')
        content = content_tag.text.strip() if content_tag else description

        pub_date_str = item.find('pubDate').text.strip() if item.find('pubDate') else None
        pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z') if pub_date_str else datetime.utcnow()

        # Authors - Fox News RSS might not include authors; default to empty list
        authors = [creator.text.strip() for creator in item.find_all('dc:creator')] or []

        # Keywords - Use only category tags with domain "foxnews.com/taxonomy"
        keywords = [cat.text.strip() for cat in item.find_all('category')
                    if cat.get('domain') == 'foxnews.com/taxonomy'] or []

        # Get image information from media:content elements (choose the one with highest width)
        image_url = None
        media_contents = item.find_all('media:content')
        if media_contents:
            valid_media = [(m.get('url'), int(m.get('width')))
                           for m in media_contents
                           if m.get('width') and m.get('width').isdigit()]
            if valid_media:
                image_url = max(valid_media, key=lambda x: x[1])[0]

        # Calculate reading time (rough estimate: 200 words per minute)
        text_content = f"{title} {description or ''} {content or ''}"
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

    def fetch_and_store_articles(self):
        """Fetch and store articles from all RSS feeds for Fox News."""
        print("Starting fetch_and_store_articles for Fox News...")
        session = self.get_session()
        print("Executing categories query for Fox News...")
        try:
            # Get all active categories with valid atom_link in the pt_fox schema
            categories = session.execute(
                text("""
                    SELECT category_id, atom_link 
                    FROM pt_fox.categories 
                    WHERE is_active = true AND atom_link IS NOT NULL 
                """)
            ).fetchall()
            print(f"Found {len(categories)} categories in Fox News")
            
            for category_id, atom_link in categories:
                print(f"Processing category: {category_id} with feed URL: {atom_link}")
                try:
                    response = requests.get(atom_link, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'xml')
                    
                    for item in soup.find_all('item'):
                        article_data = self.parse_article(item, category_id)
                        existing = session.query(self.FoxNewsArticle).filter(
                            self.FoxNewsArticle.guid == article_data['guid']
                        ).first()

                        if not existing:
                            article = self.FoxNewsArticle(**article_data)
                            session.add(article)
                            print(f"Added new article: {article_data['title']}")
                        elif existing.pub_date != article_data['pub_date']:
                            # Update existing article if pub_date has changed
                            for key, value in article_data.items():
                                setattr(existing, key, value)
                            print(f"Updated article: {article_data['title']}")
                    
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
        """Main method to fetch and store Fox News articles."""
        try:
            self.fetch_and_store_articles()
            print("Fox News article processing completed successfully")
        except Exception as e:
            print(f"Error processing Fox News articles: {e}")
            raise

def main():
    """Script entry point for Fox News RSS Articles Parser."""
    argparser = argparse.ArgumentParser(description="Fox News RSS Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    try:
        # Fetch the portal_id for Fox News using its prefix "pt_fox"
        portal_id = fetch_portal_id_by_prefix("pt_fox", env=args.env)
        parser = FoxNewsRSSArticlesParser(portal_id=portal_id, env=args.env, article_model=FoxNewsArticle)
        parser.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()
