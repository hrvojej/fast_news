"""
BBC RSS Articles Parser
Fetches and stores BBC RSS feed articles using SQLAlchemy ORM.
"""

import sys
import os
import re
import requests
from bs4 import BeautifulSoup
import argparse
from typing import Tuple, Optional, Dict, List
from sqlalchemy import text
from datetime import datetime
from uuid import UUID

current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from db_scripts.models.models import create_portal_category_model
BBCCategory = create_portal_category_model("pt_bbc")

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

class BBCRSSCategoriesParser:
    """Parser for BBC RSS feed categories"""

    def __init__(self, portal_id: UUID, env: str = 'dev'):
        self.portal_id = portal_id
        self.env = env
        self.base_urls = [
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://feeds.bbci.co.uk/news/world/rss.xml",
            "https://feeds.bbci.co.uk/news/uk/rss.xml",
            "https://feeds.bbci.co.uk/news/business/rss.xml",
            "https://feeds.bbci.co.uk/news/technology/rss.xml",
            "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
            "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
            "https://feeds.bbci.co.uk/news/health/rss.xml",
            "https://feeds.bbci.co.uk/news/education/rss.xml",
            "https://feeds.bbci.co.uk/news/politics/rss.xml",
            "https://feeds.bbci.co.uk/sport/rss.xml",
            "https://feeds.bbci.co.uk/sport/football/rss.xml",
            "https://feeds.bbci.co.uk/sport/cricket/rss.xml",
            "https://feeds.bbci.co.uk/sport/formula1/rss.xml",
            "https://feeds.bbci.co.uk/sport/rugby-union/rss.xml",
            "https://feeds.bbci.co.uk/sport/tennis/rss.xml",
            "https://feeds.bbci.co.uk/sport/golf/rss.xml",
            "https://feeds.bbci.co.uk/sport/athletics/rss.xml",
            "https://feeds.bbci.co.uk/sport/cycling/rss.xml",
            "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
            "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
            "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
            "https://feeds.bbci.co.uk/news/world/australia/rss.xml",
            "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
            "https://feeds.bbci.co.uk/news/world/latin_america/rss.xml",
            "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
            "https://feeds.bbci.co.uk/news/in_pictures/rss.xml",
            "https://feeds.bbci.co.uk/news/have_your_say/rss.xml",
            "https://feeds.bbci.co.uk/news/live/rss.xml"
        ]

    def get_session(self):
        """Get database session from DatabaseContext."""
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        return db_context.session().__enter__()

    @staticmethod
    def clean_cdata(text: Optional[str]) -> Optional[str]:
        """Clean CDATA tags from text."""
        if not text:
            return None
        cleaned = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', str(text)).strip()
        return cleaned if cleaned else None

    @staticmethod
    def generate_slug(url: Optional[str], title: Optional[str]) -> str:
        """Generate a slug from URL or title."""
        if not url:
            return BBCRSSCategoriesParser.clean_ltree(title or 'unknown')
        path = url.split('//')[1].split('/')[2:-1]
        if not path:
            return BBCRSSCategoriesParser.clean_ltree(title or 'unknown')
        return '_'.join(path)

    @staticmethod
    def clean_ltree(value: Optional[str]) -> str:
        """Clean value for ltree compatibility."""
        if not value:
            return "unknown"
        value = value.replace(">", ".").strip()
        value = re.sub(r"[^a-zA-Z0-9.]+", "_", value.lower())
        value = re.sub(r"[._]{2,}", ".", value)
        return value.strip("._")

    def validate_rss(self, rss_url: str) -> Tuple[bool, Optional[BeautifulSoup], Optional[str]]:
        """Validate RSS feed URL."""
        try:
            print(f"\nValidating RSS feed: {rss_url}")
            response = requests.get(rss_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'xml')
            channel = soup.find('channel')
            
            if not channel:
                return False, None, "No channel element found"
            if not channel.find('title'):
                return False, None, "No title element found"
                
            return True, soup, None
            
        except requests.exceptions.RequestException as e:
            return False, None, f"HTTP error: {str(e)}"
        except Exception as e:
            return False, None, f"Error: {str(e)}"

    def parse_category(self, channel: BeautifulSoup, rss_url: str) -> Dict:
        """Parse RSS channel metadata."""
        title = self.clean_cdata(channel.find('title').string if channel.find('title') else None)
        path = self.clean_ltree(title or 'unknown')
        slug = self.generate_slug(rss_url, title)
        
        return {
            'title': title,
            'name': title,
            'link': self.clean_cdata(channel.find('link').string if channel.find('link') else None),
            'atom_link': channel.find('atom:link')['href'] if channel.find('atom:link') else rss_url,
            'description': self.clean_cdata(channel.find('description').string if channel.find('description') else None),
            'path': path,
            'level': len(slug.split('_')),
            'is_active': True
        }

    def process_categories(self) -> List[Dict]:
        """Process all RSS feeds and extract categories."""
        categories = []
        
        for index, rss_url in enumerate(self.base_urls, 1):
            try:
                is_valid, rss_soup, error_msg = self.validate_rss(rss_url)
                
                if not is_valid:
                    print(f"❌ Skipping invalid RSS feed: {rss_url}")
                    if error_msg:
                        print(f"Error details: {error_msg}")
                    continue

                channel = rss_soup.find('channel')
                if channel:
                    category_data = self.parse_category(channel, rss_url)
                    categories.append(category_data)
                    print(f"✓ Successfully processed: {category_data['name']}")
                
            except Exception as e:
                print(f"❌ Error processing feed {rss_url}: {str(e)}")
                continue

        return categories

    def store_categories(self, categories: List[Dict]):
        """Store categories in database."""
        session = self.get_session()
        try:
            for category in categories:
                slug = self.generate_slug(category['atom_link'], category['title'])
                path = self.clean_ltree(category['title'] or 'unknown')
                level = len(slug.split('_'))
                
                category_obj = BBCCategory(
                    name=category['name'],
                    slug=slug,
                    portal_id=self.portal_id,
                    path=category['path'],
                    level=category['level'],
                    description=category['description'],
                    link=category['link'],
                    atom_link=category['atom_link'],
                    is_active=category['is_active']
                )
                
                session.merge(category_obj)
            
            session.commit()
            print("Categories stored successfully")
            
        except Exception as e:
            print(f"Error storing categories: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def run(self):
        """Main method to fetch and store BBC categories."""
        try:
            categories = self.process_categories()
            self.store_categories(categories)
            print("Category processing completed successfully")
        except Exception as e:
            print(f"Error processing categories: {e}")
            raise

def main():
    """Script entry point."""
    argparser = argparse.ArgumentParser(description="BBC RSS Categories Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    try:
        portal_id = fetch_portal_id_by_prefix("pt_bbc", env=args.env)
        parser = BBCRSSCategoriesParser(portal_id=portal_id, env=args.env)
        parser.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()