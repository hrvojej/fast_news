#!/usr/bin/env python
"""
Guardian Categories Parser
Fetches and stores Guardian categories using SQLAlchemy ORM.
"""

import argparse
import sys
import os
import requests
import re
import time
from uuid import UUID
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Add the package root (e.g., news_aggregator) to sys.path if needed.
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from portals.modules.portal_db import fetch_portal_id_by_prefix
from db_scripts.models.models import create_portal_category_model
from portals.modules.logging_config import setup_script_logging

logger = setup_script_logging(__file__)

# Create the dynamic category model for the Guardian portal
GuardianCategory = create_portal_category_model("pt_guardian")


class GuardianCategoriesParser:
    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=GuardianCategory):
        """
        Initialize the Guardian parser.
        Args:
            portal_id: UUID of the Guardian portal.
            env: Environment to use (dev/prod).
            category_model: SQLAlchemy ORM model for categories.
        """
        self.portal_id = portal_id
        self.env = env
        self.category_model = category_model
        self.base_url = 'https://www.theguardian.com'
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/91.0.4472.124 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }

    @staticmethod
    def clean_ltree(value: str) -> str:
        """Convert a category title into a valid ltree path."""
        if not value:
            return "unknown"
        # Replace '>' with dot and clean up the string
        value = value.replace('>', '.').strip()
        value = re.sub(r"[^a-zA-Z0-9.]+", "_", value.lower())
        value = re.sub(r"[._]{2,}", ".", value)
        return value.strip("._")

    @staticmethod
    def generate_slug(url: str) -> str:
        """Generate a unique slug from a URL."""
        try:
            parts = url.split('//')[1].split('/')[1:]
            # Filter out known non-slug parts
            parts = [part for part in parts if part and part not in ['index.html', 'article', 'articles']]
            if not parts:
                return 'home'
            return '_'.join(parts)
        except Exception:
            return 'unknown'

    def fetch_page(self, url: str) -> BeautifulSoup:
        """
        Fetch a page and return a BeautifulSoup object.
        """
        try:
            logger.info(f"Fetching URL: {url}")
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch page {url}: {e}")
            return None

    def parse_main_categories(self, soup: BeautifulSoup):
        """
        Parse the main categories from the Guardian homepage soup.
        """
        if not soup:
            raise Exception("No content to parse for main categories.")
        categories = []
        # The main navigation links use a specific class
        main_links = soup.find_all('a', class_='dcr-7612kl')
        logger.info(f"Found {len(main_links)} main navigation links.")

        for link in main_links:
            href = link.get('href', '')
            # Special case: if link is root, use '/news'
            if href == '/':
                href = '/news'
            full_url = urljoin(self.base_url, href)
            title = link.get_text(strip=True)
            slug = self.generate_slug(full_url)
            path = self.clean_ltree(title)
            # Optionally, you could fetch a meta description from the homepage if needed.
            description = None

            main_category = {
                'title': title,
                'link': full_url,
                'slug': slug,
                'path': path,
                'level': 1,
                'description': description
            }
            categories.append(main_category)
            # Attempt to fetch subcategories for this main category
            subcategories = self.parse_subcategories(full_url, path)
            if subcategories:
                categories.extend(subcategories)
            time.sleep(2)  # Respect rate limiting
        return categories

    def parse_subcategories(self, url: str, parent_path: str):
        """
        Fetch the page at the given URL and extract subcategories.
        """
        subcategories = []
        soup = self.fetch_page(url)
        if not soup:
            logger.warning(f"Could not fetch subcategories page for URL: {url}")
            return subcategories

        # The subcategory items are contained in list items with a specific class
        sub_items = soup.find_all('li', class_='dcr-5wkng0')
        logger.info(f"Found {len(sub_items)} subcategory items on page: {url}")

        for item in sub_items:
            a_tag = item.find('a', href=True)
            if not a_tag:
                continue
            sub_href = a_tag.get('href', '')
            sub_full_url = urljoin(self.base_url, sub_href)
            sub_title = a_tag.get_text(strip=True)
            sub_slug = self.generate_slug(sub_full_url)
            sub_path = f"{parent_path}.{self.clean_ltree(sub_title)}"

            subcategory = {
                'title': sub_title,
                'link': sub_full_url,
                'slug': sub_slug,
                'path': sub_path,
                'level': 2,
                'description': None  # Could be extended to extract a proper description if available
            }
            subcategories.append(subcategory)
        return subcategories

    def store_categories(self, categories):
        """
        Store categories in the database using SQLAlchemy ORM.
        """
        from db_scripts.db_context import DatabaseContext
        session = DatabaseContext.get_instance(self.env).session().__enter__()
        try:
            count_added = 0
            for cat in categories:
                # Check for existing category using slug and portal_id
                existing = session.query(self.category_model).filter(
                    self.category_model.slug == cat['slug'],
                    self.category_model.portal_id == self.portal_id
                ).first()
                if existing:
                    logger.info(f"Category '{cat['slug']}' already exists. Skipping.")
                    continue

                # Create new category record
                category = self.category_model(
                    name=cat['title'],
                    slug=cat['slug'],
                    portal_id=self.portal_id,
                    path=cat['path'],
                    level=cat['level'],
                    description=cat['description'],
                    link=cat['link'],
                    atom_link=f"{cat['link']}/rss",
                    is_active=True
                )
                session.add(category)
                count_added += 1

            session.commit()
            logger.info(f"Stored {count_added} new categories.")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store categories: {e}")
            raise
        finally:
            session.close()

    def run(self):
        """
        Main method to fetch, parse, and store Guardian categories.
        """
        try:
            homepage_soup = self.fetch_page(self.base_url)
            if not homepage_soup:
                raise Exception("Failed to fetch the Guardian homepage.")
            categories = self.parse_main_categories(homepage_soup)
            # Remove duplicate categories based on unique path if needed
            unique_categories = {cat['path']: cat for cat in categories}.values()
            self.store_categories(unique_categories)
            logger.info("Category processing completed successfully.")
        except Exception as e:
            logger.error(f"Error processing categories: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description="Guardian Categories Parser")
    parser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = parser.parse_args()

    try:
        portal_id = fetch_portal_id_by_prefix("pt_guardian", env=args.env)
        logger.info(f"Using portal_id: {portal_id} for Guardian portal.")
        parser_instance = GuardianCategoriesParser(
            portal_id=portal_id,
            env=args.env,
            category_model=GuardianCategory
        )
        parser_instance.run()
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
