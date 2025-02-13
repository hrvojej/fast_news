#!/usr/bin/env python
"""
ABC News RSS Categories Parser
Fetches and stores ABC News RSS feed categories using SQLAlchemy ORM.
Refactored in a similar style as abc_article_rss_parser.
"""

import argparse
import sys
import os
import requests
import re
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

# Dynamically create the category model for the ABC News portal.
ABCCategory = create_portal_category_model("pt_abc")


class ABCRSSCategoriesParser:
    """
    Parser for ABC News RSS feed categories.
    Fetches a page listing RSS feeds, parses each feed to extract category metadata,
    and stores unique categories in the database.
    """

    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=ABCCategory):
        """
        Initialize the parser.

        Args:
            portal_id: UUID of the ABC News portal in the news_portals table.
            env: Environment to use ('dev' or 'prod').
            category_model: SQLAlchemy ORM model for categories.
        """
        self.portal_id = portal_id
        self.env = env
        self.category_model = category_model
        self.base_url = "https://abcnews.go.com/Site/page/rss-feeds-3520115"

    @staticmethod
    def clean_ltree(value: str) -> str:
        """
        Convert a category title into a valid ltree path.
        """
        if not value:
            return "unknown"
        # Replace "U.S." with "U_S", slashes/backslashes with dots, arrow indicators with dots,
        # then convert to lowercase.
        value = value.replace('U.S.', 'U_S')
        value = value.replace('/', '.').replace('\\', '.')
        value = value.replace('>', '.').strip()
        value = value.lower()
        # Replace any non-alphanumeric characters (except dots) with underscores.
        value = re.sub(r'[^a-z0-9.]+', '_', value)
        # Replace multiple dots or underscores with a single dot.
        value = re.sub(r'[._]{2,}', '.', value)
        return value.strip('._')

    def fetch_rss_feeds(self):
        """
        Fetch the ABC News RSS feeds page, extract unique RSS feed URLs,
        and parse each feed to extract category metadata.
        """
        try:
            logger.info(f"Fetching RSS feeds page from {self.base_url}")
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
            logger.info(f"Found {len(unique_rss_links)} unique RSS feeds")
            return self.parse_rss_feeds(unique_rss_links)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch RSS feeds page: {e}")
            raise Exception(f"Failed to fetch RSS feeds page: {e}")

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
                logger.info(f"Processing RSS feed: {rss_url}")
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
        Main method to fetch, parse, and store ABC News categories.
        """
        try:
            categories = self.fetch_rss_feeds()
            self.store_categories(categories)
            logger.info("Category processing completed successfully.")
        except Exception as e:
            logger.error(f"Error processing categories: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description="ABC News RSS Categories Parser")
    parser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = parser.parse_args()

    portal_id = fetch_portal_id_by_prefix("pt_abc", env=args.env)
    logger.info(f"Using portal_id: {portal_id} for portal_prefix: pt_abc")
    parser_instance = ABCRSSCategoriesParser(portal_id=portal_id, env=args.env)
    parser_instance.run()


if __name__ == "__main__":
    main()
