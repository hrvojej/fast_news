"""
Al Jazeera Categories Parser
Fetches and stores Al Jazeera website categories using SQLAlchemy ORM.
"""

import sys
import os
import argparse
import requests
import re
from bs4 import BeautifulSoup
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from uuid import UUID

# Add the package root (e.g., news_aggregator) to sys.path if needed.
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Import the dynamic model factory from your models file.
from db_scripts.models.models import create_portal_category_model
# Create the dynamic category model for the Al Jazeera portal.
# Here we use schema "pt_aljazeera" as specified.
AljazeeraCategory = create_portal_category_model("pt_aljazeera")

def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
    """
    Fetch the portal_id from the news_portals table given the portal_prefix.
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


class AljazeeraCategoriesParser:
    """
    Parser for Al Jazeera website categories.
    It fetches categories from the homepage navigation and from the sports section.
    """
    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=None):
        self.portal_id = portal_id
        self.env = env
        self.category_model = category_model
        self.base_url = "https://www.aljazeera.com"

    def get_session(self):
        """
        Obtain a database session.
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
        # Replace slashes, arrow symbols, etc.
        value = value.replace('>', '.').replace('/', '.').replace('\\', '.').strip()
        # Convert to lowercase
        value = value.lower()
        # Replace any non-alphanumeric characters (except dots) with underscores
        value = re.sub(r'[^a-z0-9.]+', '_', value)
        # Replace multiple dots or underscores with a single dot
        value = re.sub(r'[._]{2,}', '.', value)
        return value.strip('._')

    def parse_menu(self, ul, parent_path=""):
        """
        Recursively parse a <ul> element to extract category items.
        Returns a list of category dictionaries.
        Each dictionary will include:
            - title
            - link
            - description (None if not available)
            - atom_link (None if not available)
            - slug (computed from title)
            - path (if nested, parent_path + '.' + cleaned title)
            - level (number of parts in path)
        """
        categories = []
        for li in ul.find_all("li", recursive=False):
            # Look for an <a> tag; if not present, skip this li.
            a_tag = li.find("a", href=True)
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href")
            # If href is relative, prepend base URL
            if href and href.startswith("/"):
                href = self.base_url + href
            # Build full path and compute level
            cleaned_title = self.clean_ltree(title)
            full_path = f"{parent_path}.{cleaned_title}" if parent_path else cleaned_title
            level = len(full_path.split('.'))
            category = {
                'title': title,
                'link': href,
                'description': None,
                'atom_link': None,
                'slug': full_path,  # using full_path as slug; adjust if needed
                'path': full_path,
                'level': level
            }
            categories.append(category)
            # Check if this li has a submenu container (e.g. <div class="submenu_wrapper"> with a nested <ul>)
            submenu_wrapper = li.find("div", class_="submenu_wrapper")
            if submenu_wrapper:
                nested_ul = submenu_wrapper.find("ul")
                if nested_ul:
                    # Recursively parse the nested menu; pass current full_path as parent
                    nested_categories = self.parse_menu(nested_ul, parent_path=full_path)
                    categories.extend(nested_categories)
        return categories

    def fetch_main_categories(self):
        """
        Fetch categories from the main Al Jazeera homepage navigation.
        """
        url = self.base_url + "/"
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            # Locate the primary navigation menu
            nav = soup.find("nav", class_="site-header__navigation")
            if not nav:
                print("Primary navigation menu not found on homepage.")
                return []
            ul = nav.find("ul", class_="menu header-menu")
            if not ul:
                print("Menu list not found in navigation.")
                return []
            categories = self.parse_menu(ul)
            print(f"Found {len(categories)} main navigation categories.")
            return categories
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch main categories: {e}")

    def fetch_sports_categories(self):
        """
        Fetch categories from the sports section.
        This version targets the scrollable container (data-testid="scrollable-element")
        to locate the sports subcategories.
        """
        url = self.base_url + "/sports/"
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            # Look for the container that holds the scrollable sports navigation
            scroll_div = soup.find("div", {"data-testid": "scrollable-element"})
            if not scroll_div:
                print("Sports scrollable container not found.")
                return []
            ul = scroll_div.find("ul")
            if not ul:
                print("Sports menu list not found.")
                return []
            categories = []
            for li in ul.find_all("li", class_="menu__item"):
                a_tag = li.find("a", href=True)
                if not a_tag:
                    continue
                title = a_tag.get_text(strip=True)
                href = a_tag.get("href")
                if href and href.startswith("/"):
                    href = self.base_url + href
                cleaned_title = self.clean_ltree(title)
                full_path = cleaned_title  # Flat structure so level is 1.
                category = {
                    'title': title,
                    'link': href,
                    'description': None,
                    'atom_link': None,
                    'slug': full_path,
                    'path': full_path,
                    'level': 1
                }
                categories.append(category)
            print(f"Found {len(categories)} sports categories.")
            return categories
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch sports categories: {e}")


    def run(self):
        """
        Main method to fetch and store all Al Jazeera categories.
        Combines main navigation and sports categories.
        """
        try:
            main_cats = self.fetch_main_categories()
            sports_cats = self.fetch_sports_categories()
            all_categories = main_cats + sports_cats
            # Deduplicate categories based on slug
            unique = {}
            for cat in all_categories:
                unique[cat['slug']] = cat
            deduped_categories = list(unique.values())
            print(f"Total unique categories to store: {len(deduped_categories)}")
            self.store_categories(deduped_categories)
            print("Category processing completed successfully.")
        except Exception as e:
            print(f"Error processing categories: {e}")
            raise

    def store_categories(self, categories):
        """
        Store categories using SQLAlchemy ORM.
        Checks for existing entries by slug and portal_id.
        """
        session = self.get_session()
        try:
            count_added = 0
            for cat_data in categories:
                slug = cat_data['slug']
                # Check if a category with this slug and portal_id already exists.
                existing = session.query(self.category_model).filter(
                    self.category_model.slug == slug,
                    self.category_model.portal_id == self.portal_id
                ).first()
                if existing:
                    print(f"Category with slug '{slug}' already exists. Skipping insertion.")
                    continue
                category_instance = self.category_model(
                    name=cat_data['title'],
                    slug=slug,
                    portal_id=self.portal_id,
                    path=cat_data['path'],
                    level=cat_data['level'],
                    description=cat_data['description'],
                    link=cat_data['link'],
                    atom_link=cat_data['atom_link'],
                    is_active=True
                )
                session.add(category_instance)
                count_added += 1
            session.commit()
            print(f"Successfully stored {count_added} new categories.")
        except Exception as e:
            session.rollback()
            raise Exception(f"Failed to store categories: {e}")
        finally:
            session.close()


def main():
    """
    Script entry point.
    """
    # Adjust the package root if necessary.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    package_root = os.path.abspath(os.path.join(current_dir, "../../"))
    if package_root not in sys.path:
        sys.path.insert(0, package_root)

    argparser = argparse.ArgumentParser(description="Al Jazeera Categories Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment to load data (default: dev)"
    )
    args = argparser.parse_args()
    portal_prefix = "pt_aljazeera"  # Portal prefix for Al Jazeera
    try:
        portal_id = fetch_portal_id_by_prefix(portal_prefix, env=args.env)
        print(f"Using portal_id: {portal_id} for portal_prefix: {portal_prefix}")
        parser_instance = AljazeeraCategoriesParser(
            portal_id=portal_id,
            env=args.env,
            category_model=AljazeeraCategory
        )
        parser_instance.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
