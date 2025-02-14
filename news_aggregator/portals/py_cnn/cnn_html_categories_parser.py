#!/usr/bin/env python
"""
CNN Homepage Categories Parser
Fetches and stores CNN homepage categories using SQLAlchemy ORM.
Refactored in a similar style as abc_article_rss_parser.
"""

import argparse
import sys
import os
import re
import requests
from uuid import UUID
from bs4 import BeautifulSoup
from sqlalchemy import text

# Add the package root to sys.path if needed.
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from portals.modules.logging_config import setup_script_logging
from db_scripts.models.models import create_portal_category_model

logger = setup_script_logging(__file__)

# Dynamically create the category model for the CNN portal.
CNNCategoriesModel = create_portal_category_model("pt_cnn")


def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
    """
    Fetch the portal_id from the database using the portal prefix.
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
        error_msg = f"Portal with prefix '{portal_prefix}' not found."
        logger.error(error_msg)
        raise Exception(error_msg)


class CNNCategoriesParser:
    """
    Parser for CNN homepage categories.
    Fetches the CNN homepage, extracts navigation categories, and stores them in the database.
    """

    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=CNNCategoriesModel):
        """
        Initialize the parser.

        Args:
            portal_id: UUID of the CNN portal in the news_portals table.
            env: Environment to use ('dev' or 'prod').
            category_model: SQLAlchemy ORM model for categories.
        """
        self.portal_id = portal_id
        self.env = env
        self.category_model = category_model
        self.base_url = "https://edition.cnn.com/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
        }

    @staticmethod
    def clean_ltree(value: str) -> str:
        """
        Convert a category title into a valid ltree path.

        Args:
            value: The input string to be cleaned.

        Returns:
            A cleaned string suitable for ltree paths.
        """
        if not value:
            return "unknown"
        value = value.replace('>', '.').strip()
        value = re.sub(r"[^a-zA-Z0-9.]+", "_", value.lower())
        value = re.sub(r"[._]{2,}", ".", value)
        return value.strip("._")

    @staticmethod
    def generate_slug(url: str, title: str) -> str:
        """
        Generate a slug for the category based on its URL or title.

        Args:
            url: The URL of the category.
            title: The title of the category.

        Returns:
            A slug string.
        """
        if not url:
            return CNNCategoriesParser.clean_ltree(title or 'unknown')
        try:
            parts = url.split('//')[1].split('/')[1:]
            parts = [p for p in parts if p and p not in ['index.html', 'article', 'articles']]
            return '_'.join(parts) if parts else CNNCategoriesParser.clean_ltree(title or 'unknown')
        except Exception:
            return CNNCategoriesParser.clean_ltree(title or 'unknown')

    def fetch_html_content(self) -> str:
        """
        Fetch the HTML content of the CNN homepage.

        Returns:
            The HTML content as a string.

        Raises:
            Exception: If the page cannot be fetched.
        """
        try:
            logger.info(f"Fetching CNN homepage from {self.base_url}")
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch CNN homepage: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def extract_categories(self, html_content: str):
        """
        Parse the CNN homepage HTML and extract category metadata.

        Args:
            html_content: HTML content of the CNN homepage.

        Returns:
            A list of dictionaries, each containing category metadata.

        Raises:
            Exception: If the main navigation cannot be found.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        nav = soup.find('nav', class_='subnav')
        if not nav:
            error_msg = "Could not find main navigation on CNN homepage."
            logger.error(error_msg)
            raise Exception(error_msg)

        categories = []
        sections = nav.find_all('li', class_='subnav__section')
        for section in sections:
            main_link = section.find('a', class_='subnav__section-link')
            if not main_link:
                continue

            main_title = main_link.text.strip()
            main_href = main_link.get('href', '')
            main_path = self.clean_ltree(main_title)

            main_category = {
                'title': main_title,
                'link': main_href,
                'path': main_path,
                'level': 1,
                'slug': self.generate_slug(main_href, main_title),
                'description': main_title
            }
            logger.info(f"Processing category: {main_title}")
            categories.append(main_category)

            subsections = section.find_all('li', class_='subnav__subsection')
            for subsection in subsections:
                sub_link = subsection.find('a', class_='subnav__subsection-link')
                if not sub_link:
                    continue

                sub_title = sub_link.text.strip()
                sub_href = sub_link.get('href', '')
                sub_path = f"{main_path}.{self.clean_ltree(sub_title)}"

                subcategory = {
                    'title': sub_title,
                    'link': sub_href,
                    'path': sub_path,
                    'level': 2,
                    'slug': self.generate_slug(sub_href, sub_title),
                    'description': f"{main_title} - {sub_title}"
                }
                logger.info(f"Processing subcategory: {sub_title}")
                categories.append(subcategory)

        return categories

    def store_categories(self, categories):
        """
        Store extracted categories into the database using SQLAlchemy ORM.
        Avoids duplicate entries.

        Args:
            categories: List of category dictionaries.
        """
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        session = db_context.session().__enter__()
        count_added = 0
        try:
            logger.info("Storing categories in the database...")
            for category_data in categories:
                slug = category_data['slug']
                # Check for existing category.
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
                    is_active=True
                )
                session.add(category)
                count_added += 1

            session.commit()
            logger.info(f"Successfully stored {count_added} new categories.")
        except Exception as e:
            session.rollback()
            error_msg = f"Failed to store categories: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
        finally:
            session.close()

    def run(self):
        """
        Execute the parsing process: fetch, extract, and store categories.
        """
        try:
            html_content = self.fetch_html_content()
            categories = self.extract_categories(html_content)
            self.store_categories(categories)
            logger.info("Category processing completed successfully.")
        except Exception as e:
            error_msg = f"Error processing categories: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)


def main():
    parser = argparse.ArgumentParser(description="CNN Homepage Categories Parser")
    parser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = parser.parse_args()

    try:
        portal_id = fetch_portal_id_by_prefix("pt_cnn", env=args.env)
        logger.info(f"Using portal_id: {portal_id} for portal_prefix: pt_cnn")
        parser_instance = CNNCategoriesParser(portal_id=portal_id, env=args.env)
        parser_instance.run()
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
