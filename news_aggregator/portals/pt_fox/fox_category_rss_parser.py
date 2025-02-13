#!/usr/bin/env python
"""
Fox News RSS Categories Parser
Fetches and stores Fox News RSS feed categories using SQLAlchemy ORM.
Refactored in a similar style as abc_article_rss_parser.
"""

import argparse
import sys
import os
import re
import requests
from bs4 import BeautifulSoup
from uuid import UUID

# Add the package root (e.g., news_aggregator) to sys.path if needed.
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from portals.modules.portal_db import fetch_portal_id_by_prefix
from db_scripts.models.models import create_portal_category_model
from portals.modules.logging_config import setup_script_logging

logger = setup_script_logging(__file__)

# Dynamically create the category model for the Fox News portal.
FOXCategory = create_portal_category_model("pt_fox")


class FoxRSSCategoriesParser:
    """
    Parser for Fox News RSS feed categories.
    Fetches a page listing RSS feeds, parses each link to extract category metadata,
    and stores unique categories in the database.
    """

    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=FOXCategory):
        """
        Initialize the parser.

        Args:
            portal_id: UUID of the Fox News portal in the news_portals table.
            env: Environment to use ('dev' or 'prod').
            category_model: SQLAlchemy ORM model for categories.
        """
        self.portal_id = portal_id
        self.env = env
        self.category_model = category_model
        self.base_url = "https://www.foxnews.com/story/foxnews-com-rss-feeds"

    @staticmethod
    def clean_ltree(value: str) -> str:
        """
        Convert a category title into a valid ltree path (lowercase with underscores).
        """
        if not value:
            return "unknown"
        cleaned = value.lower()
        cleaned = re.sub(r'\s+', '_', cleaned)
        cleaned = re.sub(r'[^a-z0-9_]', '', cleaned)
        return cleaned

    def generate_link(self, atom_link: str) -> str:
        """
        Generate the public-facing link from the atom_link.
        For example, given:
            https://moxie.foxnews.com/google-publisher/opinion.xml
        it returns:
            https://www.foxnews.com/opinion
        """
        prefix = "https://moxie.foxnews.com/google-publisher/"
        if atom_link.startswith(prefix) and atom_link.endswith(".xml"):
            # Remove the prefix and the .xml suffix.
            category_segment = atom_link[len(prefix):-4]
            return f"https://www.foxnews.com/{category_segment}"
        return ""

    def fetch_rss_feeds(self):
        """
        Fetch the Fox News RSS feeds page and extract unique RSS feed URLs.
        
        Returns:
            A list of dictionaries containing category metadata.
        """
        try:
            logger.info(f"Fetching Fox News RSS feeds page from {self.base_url}")
            response = requests.get(self.base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            rss_links = []
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                if "moxie.foxnews.com/google-publisher/" in href and href.endswith(".xml"):
                    rss_links.append(href)
            unique_rss_links = list(set(rss_links))
            logger.info(f"Found {len(unique_rss_links)} unique RSS feed links")
            return self.parse_rss_feeds(unique_rss_links)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Fox News RSS feeds page: {e}")
            raise Exception(f"Failed to fetch Fox News RSS feeds page: {e}")

    def parse_rss_feeds(self, rss_links):
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
                # Extract the filename (e.g., 'travel.xml') from the URL.
                filename = rss_url.split("/")[-1]
                if filename.endswith(".xml"):
                    cat_identifier = filename[:-4]
                else:
                    cat_identifier = filename

                # Capitalize to form the category title.
                title = cat_identifier.capitalize()
                slug = self.clean_ltree(title)
                path = slug  # In this case, the path is identical to the slug.
                level = 1

                category = {
                    'title': title,
                    'link': self.generate_link(rss_url),
                    'description': "",  # No description available.
                    'atom_link': rss_url,
                    'path': path,
                    'level': level
                }
                categories.append(category)
            except Exception as e:
                logger.error(f"Error processing RSS feed {rss_url}: {e}")
                continue
        return categories

    def store_categories(self, categories):
        """
        Store categories in the database using SQLAlchemy ORM.
        Avoids inserting duplicate categories.

        Args:
            categories: List of category dictionaries.
        """
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        session = db_context.session().__enter__()
        try:
            logger.info("Storing categories in the database...")
            count_added = 0
            for category_data in categories:
                slug = self.clean_ltree(category_data['title'])
                # Check if this category already exists for the portal.
                existing = session.query(self.category_model).filter(
                    self.category_model.slug == slug,
                    self.category_model.portal_id == self.portal_id
                ).first()
                if existing:
                    logger.info(f"Category with slug '{slug}' already exists. Skipping insertion.")
                    continue

                category = self.category_model(
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
            logger.info(f"Successfully stored {count_added} new categories.")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store categories: {e}")
            raise Exception(f"Failed to store categories: {e}")
        finally:
            session.close()

    def run(self):
        """
        Main method to fetch, parse, and store Fox News RSS feed categories.
        """
        try:
            categories = self.fetch_rss_feeds()
            self.store_categories(categories)
            logger.info("Category processing completed successfully.")
        except Exception as e:
            logger.error(f"Error processing categories: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description="Fox News RSS Categories Parser")
    parser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = parser.parse_args()

    portal_id = fetch_portal_id_by_prefix("pt_fox", env=args.env)
    logger.info(f"Using portal_id: {portal_id} for portal_prefix: pt_fox")
    parser_instance = FoxRSSCategoriesParser(portal_id=portal_id, env=args.env)
    parser_instance.run()


if __name__ == "__main__":
    main()
