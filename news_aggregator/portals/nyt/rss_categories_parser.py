# path: news_dagster-etl/news_aggregator/portals/nyt/rss_categories_parser.py
"""
NYT RSS Categories Parser
Fetches and stores NYT RSS feed categories using SQLAlchemy ORM.
"""

import sys
import os

# Add the package root (news_aggregator) to sys.path.
current_dir = os.path.dirname(os.path.abspath(__file__))
# news_aggregator is two directories up from portals/nyt/
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

import argparse
import requests
from bs4 import BeautifulSoup
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import re
from typing import List, Dict
from uuid import UUID
from sqlalchemy import text

# Import the dynamic model factory from your models file.
from db_scripts.models.models import create_portal_category_model

# Create the dynamic category model for the NYT portal.
# Here the schema is "pt_nyt" as used in your queries.
NYTCategory = create_portal_category_model("pt_nyt")


def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
    """
    Fetches the portal_id from the news_portals table for the given portal_prefix.

    Args:
        portal_prefix: The prefix of the portal (e.g., 'pt_nyt')
        env: The environment to use ('dev' or 'prod')

    Returns:
        The UUID of the portal.

    Raises:
        Exception: If no portal with the given prefix is found.
    """
    # Import DatabaseContext from your db_context module.
    from db_scripts.db_context import DatabaseContext
    db_context = DatabaseContext.get_instance(env)
    with db_context.session() as session:
        result = session.execute(
            text("SELECT portal_id FROM public.news_portals WHERE portal_prefix = :prefix"),
            {'prefix': portal_prefix}
        ).fetchone()
        if result:
            return result[0]
        else:
            raise Exception(f"Portal with prefix '{portal_prefix}' not found.")


class NYTRSSCategoriesParser:
    """Parser for NYT RSS feed categories"""

    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=None):
        """
        Initialize the parser

        Args:
            portal_id: UUID of the NYT portal in news_portals table
            env: Environment to use (dev/prod)
            category_model: SQLAlchemy ORM model for categories (if applicable)
        """
        self.portal_id = portal_id
        self.env = env
        self.base_url = "https://www.nytimes.com/rss"
        self.NYTCategory = category_model

    def get_session(self):
        """
        Obtain a database session from the DatabaseContext.
        """
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        # Directly enter the session context to get a session object.
        return db_context.session().__enter__()

    @staticmethod
    def clean_ltree(value: str) -> str:
        """
        Convert category title into valid ltree path.
        """
        if not value:
            return "unknown"

        # Replace "U.S." with "U_S"
        value = value.replace('U.S.', 'U_S')
        # Replace slashes with dots
        value = value.replace('/', '.').replace('\\', '.')
        # Replace arrow indicators with dots
        value = value.replace('>', '.').strip()
        # Convert to lowercase
        value = value.lower()
        # Replace any non-alphanumeric characters (except dots) with underscores
        value = re.sub(r'[^a-z0-9.]+', '_', value)
        # Replace multiple dots or underscores with a single one
        value = re.sub(r'[._]{2,}', '.', value)
        # Remove leading/trailing dots or underscores
        return value.strip('._')

    def fetch_rss_feeds(self) -> List[Dict]:
        """
        Fetch and parse NYT RSS feeds.
        """
        try:
            print(f"Fetching RSS feeds from {self.base_url}")
            response = requests.get(self.base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            rss_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'rss' in href and href.endswith('.xml'):
                    rss_links.append(href)

            unique_rss_links = list(set(rss_links))
            print(f"Found {len(unique_rss_links)} unique RSS feeds")
            return self.parse_rss_feeds(unique_rss_links)

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch RSS feeds: {e}")

    def parse_rss_feeds(self, rss_links: List[str]) -> List[Dict]:
        """
        Parse RSS feeds and extract category metadata.
        """
        categories = []
        for rss_url in rss_links:
            try:
                print(f"Processing RSS feed: {rss_url}")
                response = requests.get(rss_url)
                response.raise_for_status()
                rss_soup = BeautifulSoup(response.content, 'xml')

                channel = rss_soup.find('channel')
                if channel:
                    category = {
                        'title': channel.find('title').text if channel.find('title') else None,
                        'link': channel.find('link').text if channel.find('link') else None,
                        'description': channel.find('description').text if channel.find('description') else None,
                        'language': channel.find('language').text if channel.find('language') else None,
                        'atom_link': channel.find('atom:link', href=True)['href'] if channel.find('atom:link', href=True) else None
                    }

                    # Create ltree path and level.
                    path = self.clean_ltree(category['title']) if category['title'] else 'unknown'
                    category['path'] = path
                    category['level'] = len(path.split('.'))

                    categories.append(category)

            except Exception as e:
                print(f"Error processing RSS feed {rss_url}: {e}")
                continue

        return categories
    
    def store_categories(self, categories: List[Dict]):
        """
        Store categories using SQLAlchemy ORM.
        """
        session = self.get_session()

        try:
            print("Storing categories in database...")
            count_added = 0
            for category_data in categories:
                slug = self.clean_ltree(category_data['title']) if category_data['title'] else 'unknown'

                existing = session.query(self.NYTCategory).filter(
                    self.NYTCategory.slug == slug,
                    self.NYTCategory.portal_id == self.portal_id
                ).first()
                if existing:
                    print(f"Category with slug '{slug}' already exists. Skipping insertion.")
                    continue

                category = self.NYTCategory(
                    name=category_data['title'],
                    slug=slug,
                    portal_id=self.portal_id,
                    path=category_data['path'],
                    level=category_data['level'],
                    description=category_data['description'],
                    link=category_data['link'],
                    atom_link=category_data['atom_link'],
                    is_active=True
                )
                session.add(category)
                count_added += 1

            session.commit()
            print(f"Successfully stored {count_added} new categories")

        except Exception as e:
            session.rollback()
            raise Exception(f"Failed to store categories: {e}")

        finally:
            session.close()
    
    def run(self):
        """
        Main method to fetch and store NYT categories.
        """
        try:
            categories = self.fetch_rss_feeds()
            self.store_categories(categories)
            print("Category processing completed successfully")
        except Exception as e:
            print(f"Error processing categories: {e}")
            raise


def main():
    """
    Script entry point.
    """
    import argparse
    # Import Base from your models file to inspect the metadata
    from db_scripts.models.models import Base
    print("Registered tables in metadata:", Base.metadata.tables.keys())

    argparser = argparse.ArgumentParser(description="NYT RSS Categories Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment to load data (default: dev)"
    )
    args = argparser.parse_args()

    portal_prefix = "pt_nyt"  # The portal prefix.
    try:
        portal_id = fetch_portal_id_by_prefix(portal_prefix, env=args.env)
        print(f"Using portal_id: {portal_id} for portal_prefix: {portal_prefix}")

        parser_instance = NYTRSSCategoriesParser(portal_id=portal_id, env=args.env, category_model=NYTCategory)
        parser_instance.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()