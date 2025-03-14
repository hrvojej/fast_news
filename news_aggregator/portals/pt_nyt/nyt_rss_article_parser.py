"""
NYT RSS Articles Parser
Fetches and stores NYT RSS feed articles using SQLAlchemy ORM,
refactored to reuse common functionality from BaseRSSParser.
"""

import sys
import os
from datetime import datetime
from uuid import UUID
import argparse
import requests
from bs4 import BeautifulSoup
from sqlalchemy import text

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Import dynamic model factories for portal-specific models
from db_scripts.models.models import create_portal_category_model, create_portal_article_model
NYTCategory = create_portal_category_model("pt_nyt")
NYTArticle = create_portal_article_model("pt_nyt")

def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
    """
    Fetches the portal_id from the news_portals table.
    """
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

# Import the base class and shared logging configuration.
from portals.modules.logging_config import setup_script_logging
from portals.modules.base_parser import BaseRSSParser  # Assumes BaseRSSParser is available here

logger = setup_script_logging(__file__)

class NYTRSSParser(BaseRSSParser):
    """
    NYT RSS Parser implementation using BaseRSSParser.
    
    This parser provides NYT-specific logic:
      - Parsing <dc:creator> for authors.
      - Extracting image URL from <media:content> (selecting the largest by width).
      - Estimating reading time based on word count.
    """
    def __init__(self, portal_id, env='dev'):
        super().__init__(portal_id, env)
        # Set the SQLAlchemy model for articles.
        self.model = NYTArticle

    def parse_item(self, item, category_id):
        """
        Parses a single NYT RSS <item> element.
        
        :param item: BeautifulSoup element corresponding to an <item>
        :param category_id: Associated category ID
        :return: Dictionary with extracted article data.
        """
        # Required fields
        title_tag = item.find('title')
        title = title_tag.text.strip() if title_tag else 'Untitled'

        link_tag = item.find('link')
        link = link_tag.text.strip() if link_tag else 'https://www.nytimes.com'
        if "https://www.nytimes.com/video/" in link:
            logger.info(f"Skipping video article with URL: {link}")
            return None


        guid_tag = item.find('guid')
        guid = guid_tag.text.strip() if guid_tag else link  # Fallback to link

        # Optional fields with fallbacks
        description_tag = item.find('description')
        description = description_tag.text.strip() if description_tag else None
        content = description  # Using description as content fallback

        pub_date_tag = item.find('pubDate')
        if pub_date_tag:
            pub_date_str = pub_date_tag.text.strip()
            try:
                pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
            except Exception as e:
                logger.warning(f"Failed to parse pub_date '{pub_date_str}': {e}")
                pub_date = datetime.utcnow()
        else:
            pub_date = datetime.utcnow()

        # Extract authors from <dc:creator>
        authors = [creator.text.strip() for creator in item.find_all('dc:creator')] or []

        # Extract keywords from <category> elements (ignoring very short strings)
        keywords = [cat.text.strip() for cat in item.find_all('category')
                    if cat.text and len(cat.text.strip()) > 2] or []

        # Extract image URL from <media:content>
        image_url = None
        media_contents = item.find_all('media:content')
        if media_contents:
            valid_media = []
            for m in media_contents:
                width_str = m.get('width')
                if width_str and width_str.isdigit():
                    width = int(width_str)
                    valid_media.append((m.get('url'), width))
            if valid_media:
                image_url = max(valid_media, key=lambda x: x[1])[0]

        # Estimate reading time (approx. 200 words per minute)
        text_content = f"{title} {description or ''} {content or ''}"
        word_count = len(text_content.split())
        reading_time = max(1, round(word_count / 200))

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

    def run(self):
        """
        Main execution method for the NYT RSS Parser.
        
        It retrieves all active categories (with non-null atom_link values)
        from the pt_nyt.categories table, processes each feed using the base
        class functionality, and prints a full report of new and updated articles.
        """
        feeds = []
        try:
            with self.db_context.session() as session:
                categories = session.execute(
                    text("""
                        SELECT category_id, atom_link 
                        FROM pt_nyt.categories 
                        WHERE is_active = true AND atom_link IS NOT NULL
                    """)
                ).fetchall()
                logger.info(f"Found {len(categories)} active categories with feeds.")
                for category_id, atom_link in categories:
                    feeds.append((category_id, atom_link))
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            raise

        # Process the feeds and print the full report (new/updated articles).
        self.run_feeds(feeds)

def main():
    """Script entry point."""
    argparser = argparse.ArgumentParser(description="NYT RSS Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    try:
        portal_id = fetch_portal_id_by_prefix("pt_nyt", env=args.env)
        parser = NYTRSSParser(portal_id=portal_id, env=args.env)
        parser.run()
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()
