import sys
import os
import re
import requests
from bs4 import BeautifulSoup
import argparse
from typing import Tuple, Optional, Dict, List
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from uuid import UUID

# Set up paths so that package modules are discoverable.
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from db_scripts.models.models import create_portal_category_model
from portals.modules.logging_config import setup_script_logging

logger = setup_script_logging(__file__)
BBCCategory = create_portal_category_model("pt_bbc")


def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
    """
    Fetch the portal_id from the news_portals table based on the portal prefix.
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


class BBCRSSCategoriesParser:
    """
    Parser for BBC RSS feed categories.
    Fetches multiple RSS feeds, extracts category metadata, and stores them
    using PostgreSQL upsert functionality.
    """

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
            "https://feeds.bbci.co.uk/news/have_your_say/rss.xml"
        ]

    def get_session(self):
        """
        Get a database session from the DatabaseContext.
        """
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        return db_context.session().__enter__()

    @staticmethod
    def clean_cdata(text_value: Optional[str]) -> Optional[str]:
        """
        Clean CDATA tags from the text.
        """
        if not text_value:
            return None
        cleaned = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', str(text_value)).strip()
        return cleaned if cleaned else None

    @staticmethod
    def clean_ltree(value: Optional[str]) -> str:
        """
        Clean a string to make it compatible with ltree format.
        """
        if not value:
            return "unknown"
        value = value.replace(">", ".").strip()
        value = re.sub(r"[^a-zA-Z0-9.]+", "_", value.lower())
        value = re.sub(r"[._]{2,}", ".", value)
        return value.strip("._")

    @staticmethod
    def generate_slug(url: Optional[str], title: Optional[str]) -> str:
        """
        Generate a slug from the URL or title.
        """
        if not url:
            return BBCRSSCategoriesParser.clean_ltree(title or 'unknown')
        try:
            # Extract parts from the URL.
            parts = url.split('//')[1].split('/')[2:-1]
            if not parts:
                return BBCRSSCategoriesParser.clean_ltree(title or 'unknown')
            return '_'.join(parts)
        except Exception:
            return BBCRSSCategoriesParser.clean_ltree(title or 'unknown')

    def validate_rss(self, rss_url: str) -> Tuple[bool, Optional[BeautifulSoup], Optional[str]]:
        """
        Validate the RSS feed URL by checking for the existence of
        required elements in the XML (e.g., <channel> and <title>).
        """
        try:
            logger.info(f"Validating RSS feed: {rss_url}")
            response = requests.get(rss_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'xml')
            channel = soup.find('channel')
            if not channel:
                logger.error(f"No channel element found in RSS feed: {rss_url}")
                return False, None, "No channel element found"
            if not channel.find('title'):
                logger.error(f"No title element found in RSS feed: {rss_url}")
                return False, None, "No title element found"
            return True, soup, None
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error for RSS feed {rss_url}: {e}")
            return False, None, f"HTTP error: {str(e)}"
        except Exception as e:
            logger.error(f"Error processing RSS feed {rss_url}: {e}")
            return False, None, f"Error: {str(e)}"

    def parse_category(self, channel: BeautifulSoup, rss_url: str) -> Dict:
        """
        Parse the RSS channel metadata to extract category information.
        """
        title = self.clean_cdata(channel.find('title').string if channel.find('title') else None)
        path = self.clean_ltree(title or 'unknown')
        slug = self.generate_slug(rss_url, title)
        atom_link_elem = channel.find('atom:link')
        atom_link = atom_link_elem['href'] if atom_link_elem and atom_link_elem.has_attr('href') else rss_url

        return {
            'title': title,
            'name': title,
            'link': self.clean_cdata(channel.find('link').string if channel.find('link') else None),
            'atom_link': atom_link,
            'description': self.clean_cdata(channel.find('description').string if channel.find('description') else None),
            'path': path,
            'level': len(slug.split('_')),
            'is_active': True
        }

    def process_categories(self) -> List[Dict]:
        """
        Process all RSS feeds and extract category metadata.
        """
        categories = []
        for rss_url in self.base_urls:
            try:
                is_valid, rss_soup, error_msg = self.validate_rss(rss_url)
                if not is_valid:
                    logger.warning(f"Skipping invalid RSS feed: {rss_url} - {error_msg}")
                    continue

                channel = rss_soup.find('channel')
                if channel:
                    category_data = self.parse_category(channel, rss_url)
                    categories.append(category_data)
                    logger.info(f"Processed category: {category_data['name']}")
            except Exception as e:
                logger.error(f"Error processing feed {rss_url}: {e}")
                continue
        return categories

    def store_categories(self, categories: List[Dict]):
        """
        Store categories in the database by inserting only those that do not already exist.
        """
        session = self.get_session()
        try:
            count_inserted = 0
            for category in categories:
                # Generate a slug using the atom_link and title.
                slug = self.generate_slug(category['atom_link'], category['title'])
                category_data = {
                    'name': category['name'],
                    'slug': slug,
                    'portal_id': self.portal_id,
                    'path': category['path'],
                    'level': category['level'],
                    'description': category['description'],
                    'link': category['link'],
                    'atom_link': category['atom_link'],
                    'is_active': category['is_active']
                }
                stmt = insert(BBCCategory).values(category_data)
                # Instead of updating on conflict, do nothing if the record exists.
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['slug', 'portal_id']
                )
                result = session.execute(stmt)
                # result.rowcount will be 1 if a new row was inserted, 0 if the row already exists.
                count_inserted += result.rowcount if result.rowcount else 0
                logger.info(f"Attempted to insert category: {category_data['name']}")
            session.commit()
            logger.info(f"Inserted {count_inserted} new categories successfully.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing categories: {e}")
            raise
        finally:
            session.close()


    def run(self):
        """
        Main method to fetch and store BBC RSS feed categories.
        """
        try:
            categories = self.process_categories()
            self.store_categories(categories)
            logger.info("Category processing completed successfully.")
        except Exception as e:
            logger.error(f"Error processing categories: {e}")
            raise


def main():
    """
    Script entry point.
    """
    argparser = argparse.ArgumentParser(description="BBC RSS Categories Parser")
    argparser.add_argument('--env', choices=['dev', 'prod'], default='dev', help="Specify the environment")
    args = argparser.parse_args()

    try:
        portal_id = fetch_portal_id_by_prefix("pt_bbc", env=args.env)
        logger.info(f"Using portal_id: {portal_id}")
        parser = BBCRSSCategoriesParser(portal_id=portal_id, env=args.env)
        parser.run()
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
