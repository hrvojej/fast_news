"""
Fox News RSS Categories Parser
Fetches and stores Fox News RSS feed categories using SQLAlchemy ORM.
"""

import sys
import os
import argparse
import re
import requests
from bs4 import BeautifulSoup
import sqlalchemy as sa
from sqlalchemy import text
from uuid import UUID
from typing import List, Dict

# Add the package root (e.g. news_aggregator) to sys.path.
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Import the dynamic model factory from your models file.
from db_scripts.models.models import create_portal_category_model

# Create the dynamic category model for the Fox News portal.
FOXCategory = create_portal_category_model("pt_fox")


def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
    """
    Fetches the portal_id from the news_portals table for the given portal_prefix.
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


class FoxRSSCategoriesParser:
    """Parser for Fox News RSS feed categories"""

    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=None):
        """
        Initialize the parser.

        Args:
            portal_id: UUID of the Fox News portal from the news_portals table.
            env: Environment to use (dev/prod).
            category_model: SQLAlchemy ORM model for categories.
        """
        self.portal_id = portal_id
        self.env = env
        self.base_url = "https://www.foxnews.com/story/foxnews-com-rss-feeds"
        self.FOXCategory = category_model

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
        Convert a string into a valid ltree path (lowercase, with underscores).
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

    def fetch_rss_categories(self) -> List[Dict]:
        """
        Fetch the Fox News RSS feeds page and parse all <a> elements whose URL
        ends with '.xml'. For each, derive the category name from the filename
        (e.g. 'travel.xml' becomes 'Travel'), store the original URL as the
        atom_link, and generate the public link.
        """
        try:
            print(f"Fetching Fox News RSS feeds page from {self.base_url}")
            response = requests.get(self.base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            categories = []
            for a in soup.find_all("a"):
                url = a.get("href")
                if not url or not url.strip():
                    url = a.get_text().strip()
                url = url.strip()

                # Process only URLs from Fox News feeds that end with '.xml'
                if "moxie.foxnews.com/google-publisher/" in url and url.endswith(".xml"):
                    # Extract the filename (e.g., 'travel.xml')
                    filename = url.split("/")[-1]
                    if filename.endswith(".xml"):
                        # Remove the '.xml' extension to get the category identifier.
                        cat_identifier = filename[:-4]
                        # Capitalize to form the category name.
                        name = cat_identifier.capitalize()
                        slug = self.clean_ltree(name)
                        path = slug  # In this simple case, the path is identical to the slug.
                        level = 1

                        # Use the original URL as the atom_link and generate the public link.
                        category = {
                            'name': name,
                            'slug': slug,
                            'atom_link': url,
                            'link': self.generate_link(url),
                            'description': '',  # No description available.
                            'path': path,
                            'level': level,
                        }
                        categories.append(category)
            print(f"Found {len(categories)} RSS categories.")
            return categories

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch Fox News RSS page: {e}")

    def store_categories(self, categories: List[Dict]):
        """
        Store the parsed categories in the database using SQLAlchemy ORM.
        Checks for existing records (by slug and portal_id) to avoid duplicates.
        """
        session = self.get_session()
        try:
            print("Storing categories in the database...")
            count_added = 0
            for cat in categories:
                # Check if the category already exists.
                existing = session.query(self.FOXCategory).filter(
                    self.FOXCategory.slug == cat['slug'],
                    self.FOXCategory.portal_id == self.portal_id
                ).first()
                if existing:
                    print(f"Category '{cat['name']}' already exists. Skipping insertion.")
                    continue

                new_category = self.FOXCategory(
                    name=cat['name'],
                    slug=cat['slug'],
                    portal_id=self.portal_id,
                    path=cat['path'],
                    level=cat['level'],
                    description=cat['description'],
                    link=cat['link'],
                    atom_link=cat['atom_link'],
                    is_active=True
                )
                session.add(new_category)
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
        Main method to fetch and store Fox News RSS feed categories.
        """
        try:
            categories = self.fetch_rss_categories()
            self.store_categories(categories)
            print("Category processing completed successfully.")
        except Exception as e:
            print(f"Error processing categories: {e}")
            raise


def main():
    """
    Script entry point.
    """
    from db_scripts.models.models import Base
    print("Registered tables in metadata:", Base.metadata.tables.keys())

    argparser = argparse.ArgumentParser(description="Fox News RSS Categories Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment to load data (default: dev)"
    )
    args = argparser.parse_args()

    portal_prefix = "pt_fox"
    try:
        portal_id = fetch_portal_id_by_prefix(portal_prefix, env=args.env)
        print(f"Using portal_id: {portal_id} for portal_prefix: {portal_prefix}")

        parser_instance = FoxRSSCategoriesParser(
            portal_id=portal_id,
            env=args.env,
            category_model=FOXCategory
        )
        parser_instance.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
