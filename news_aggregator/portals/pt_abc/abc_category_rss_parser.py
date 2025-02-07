#!/usr/bin/env python
"""
ABC News RSS Categories Parser
Fetches and stores ABC News RSS feed categories using SQLAlchemy ORM.
"""

import sys
import os
import argparse
import requests
import re
from bs4 import BeautifulSoup
from typing import List, Dict
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Add the package root (e.g., news_aggregator) to sys.path if needed.
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Import the dynamic model factory from your models file.
# Note the corrected function name: create_portal_category_model
from db_scripts.models.models import create_portal_category_model

# Create the dynamic category model for the ABC News portal.
ABCNewsCategory = create_portal_category_model("pt_abc")


def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
    """
    Fetches the portal_id from the news_portals table for the given portal_prefix.

    Args:
        portal_prefix: The prefix of the portal (e.g., 'pt_abc')
        env: The environment to use ('dev' or 'prod')

    Returns:
        The UUID of the portal.

    Raises:
        Exception: If no portal with the given prefix is found.
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
        else:
            raise Exception(f"Portal with prefix '{portal_prefix}' not found.")


class ABCNewsRSSCategoriesParser:
    """Parser for ABC News RSS feed categories"""

    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=None):
        """
        Initialize the parser.

        Args:
            portal_id: UUID of the ABC News portal in news_portals table.
            env: Environment to use (dev/prod).
            category_model: SQLAlchemy ORM model for categories.
        """
        self.portal_id = portal_id
        self.env = env
        self.base_url = "https://abcnews.go.com/Site/page/rss-feeds-3520115"
        self.ABCNewsCategory = category_model

    def get_session(self):
        """
        Obtain a database session from the DatabaseContext.
        """
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        return db_context.session().__enter__()

    @staticmethod
    def clean_ltree(value: str) -> str:
        """
        Convert a category title into a valid ltree path.
        """
        if not value:
            return "unknown"
        # Replace "U.S." with "U_S", slashes and backslashes with dots,
        # arrow indicators with dots, and then convert to lowercase.
        value = value.replace('U.S.', 'U_S')
        value = value.replace('/', '.').replace('\\', '.')
        value = value.replace('>', '.').strip()
        value = value.lower()
        # Replace any non-alphanumeric characters (except dots) with underscores.
        value = re.sub(r'[^a-z0-9.]+', '_', value)
        # Replace multiple dots or underscores with a single dot.
        value = re.sub(r'[._]{2,}', '.', value)
        return value.strip('._')

    def fetch_rss_feeds(self) -> List[Dict]:
        """
        Fetch and parse the ABC News RSS feeds page to extract RSS feed links,
        then process each feed to extract category metadata.
        """
        try:
            print(f"Fetching RSS feeds page from {self.base_url}")
            response = requests.get(self.base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            rss_links = []
            # Look for <a> elements whose href starts with the expected ABC News RSS feed URL.
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                if href.startswith("https://feeds.abcnews.com/"):
                    rss_links.append(href)
            unique_rss_links = list(set(rss_links))
            print(f"Found {len(unique_rss_links)} unique RSS feeds")
            return self.parse_rss_feeds(unique_rss_links)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch RSS feeds page: {e}")

    def parse_rss_feeds(self, rss_links: List[str]) -> List[Dict]:
        """
        Parse each RSS feed URL and extract category metadata.

        Args:
            rss_links: List of RSS feed URLs.

        Returns:
            A list of dictionaries containing category metadata.
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
                    title_tag = channel.find('title')
                    link_tag = channel.find('link')
                    description_tag = channel.find('description')
                    
                    # Use the RSS feed title if available, otherwise fallback to the URL.
                    title = title_tag.text.strip() if title_tag and title_tag.text else rss_url
                    link = link_tag.text.strip() if link_tag and link_tag.text else ""
                    description = description_tag.text.strip() if description_tag and description_tag.text else ""
                    
                    # Always use the RSS feed URL for atom_link.
                    atom_link = rss_url
                    
                    # Create a path and level based on the title.
                    path = self.clean_ltree(title)
                    level = len(path.split('.'))
                    
                    category = {
                        'title': title,
                        'link': link,
                        'description': description,
                        'atom_link': atom_link,
                        'path': path,
                        'level': level
                    }
                    categories.append(category)
                else:
                    # If no <channel> element is present, store minimal information.
                    title = rss_url
                    path = self.clean_ltree(title)
                    level = len(path.split('.'))
                    category = {
                        'title': title,
                        'link': "",
                        'description': "",
                        'atom_link': rss_url,
                        'path': path,
                        'level': level
                    }
                    categories.append(category)
            except Exception as e:
                print(f"Error processing RSS feed {rss_url}: {e}")
                continue
        return categories

    def store_categories(self, categories: List[Dict]):
        """
        Store categories in the database using SQLAlchemy ORM.
        Avoids inserting duplicate categories.

        Args:
            categories: List of category dictionaries.
        """
        session = self.get_session()
        try:
            print("Storing categories in the database...")
            count_added = 0
            for category_data in categories:
                slug = self.clean_ltree(category_data['title'])
                # Check if this category already exists for the portal.
                existing = session.query(self.ABCNewsCategory).filter(
                    self.ABCNewsCategory.slug == slug,
                    self.ABCNewsCategory.portal_id == self.portal_id
                ).first()
                if existing:
                    print(f"Category with slug '{slug}' already exists. Skipping insertion.")
                    continue

                category = self.ABCNewsCategory(
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
            print(f"Successfully stored {count_added} new categories.")
        except Exception as e:
            session.rollback()
            raise Exception(f"Failed to store categories: {e}")
        finally:
            session.close()

    def run(self):
        """
        Main method to fetch, parse, and store ABC News categories.
        """
        try:
            categories = self.fetch_rss_feeds()
            self.store_categories(categories)
            print("Category processing completed successfully.")
        except Exception as e:
            print(f"Error processing categories: {e}")
            raise


def main():
    """
    Script entry point.
    """
    # Print registered tables for debugging.
    from db_scripts.models.models import Base
    print("Registered tables in metadata:", Base.metadata.tables.keys())
    
    argparser = argparse.ArgumentParser(description="ABC News RSS Categories Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment to load data (default: dev)"
    )
    args = argparser.parse_args()

    portal_prefix = "pt_abc"  # The portal prefix for ABC News.
    try:
        portal_id = fetch_portal_id_by_prefix(portal_prefix, env=args.env)
        print(f"Using portal_id: {portal_id} for portal_prefix: {portal_prefix}")
        parser_instance = ABCNewsRSSCategoriesParser(
            portal_id=portal_id,
            env=args.env,
            category_model=ABCNewsCategory
        )
        parser_instance.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
