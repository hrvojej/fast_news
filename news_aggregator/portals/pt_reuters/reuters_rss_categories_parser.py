"""
Reuters RSS Categories Parser
Fetches and stores Reuters navigation categories using SQLAlchemy ORM and pychrome.

Run first in PowerShell command to start Chrome in headless mode. Go to info.md for more details.

"""

import sys
import os
import argparse
import time
import re
from typing import List, Dict
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy import text
from bs4 import BeautifulSoup

# Add the package root (news_aggregator) to sys.path.
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Import the dynamic model factory from your models file.
from db_scripts.models.models import create_portal_category_model

# Create the dynamic category model for the Reuters portal.
# Use the schema "pt_reuters" as defined in your database.
ReutersCategory = create_portal_category_model("pt_reuters")


def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
    """
    Fetch the portal_id from the news_portals table for the given portal_prefix.
    
    Args:
        portal_prefix: The prefix of the portal (e.g., 'pt_reuters')
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


class ReutersRSSCategoriesParser:
    """Parser for Reuters navigation categories using pychrome to fetch the homepage"""

    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=None):
        """
        Initialize the parser.

        Args:
            portal_id: UUID of the Reuters portal in the news_portals table.
            env: Environment to use (dev/prod).
            category_model: SQLAlchemy ORM model for categories.
        """
        self.portal_id = portal_id
        self.env = env
        # Reuters homepage URL.
        self.base_url = "https://www.reuters.com/"
        self.CategoryModel = category_model

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
        Convert a category title into a valid ltree path (and slug).
        """
        if not value:
            return "unknown"
        # Replace "U.S." with "U_S"
        value = value.replace('U.S.', 'U_S')
        # Replace slashes/backslashes and arrow characters with dots
        value = value.replace('/', '.').replace('\\', '.').replace('>', '.').strip()
        # Convert to lowercase
        value = value.lower()
        # Replace non-alphanumeric (except dot) characters with underscore
        value = re.sub(r'[^a-z0-9.]+', '_', value)
        # Replace multiple dots or underscores with a single dot
        value = re.sub(r'[._]{2,}', '.', value)
        return value.strip('._')

    def fetch_html_with_pychrome(self, url: str) -> str:
        """
        Fetch the HTML content of a page using pychrome (headless Chrome).

        Args:
            url: The URL to navigate to.

        Returns:
            The cleaned HTML content of the page.

        Raises:
            Exception: If any error occurs during the Chrome automation.
        """
        try:
            import pychrome

            print(f"Fetching page using pychrome: {url}")
            browser = pychrome.Browser(url="http://127.0.0.1:9222")
            tab = browser.new_tab()

            def handle_exception(msg):
                print(f"Debug: {msg}")

            tab.set_listener("exception", handle_exception)
            tab.start()
            tab.Page.enable()
            tab.Runtime.enable()

            tab.Page.navigate(url=url)
            # Wait for the page to load and render.
            time.sleep(5)

            clean_html_js = """
            function cleanHTML() {
                const elements = document.querySelectorAll('script, style, iframe, link, meta');
                elements.forEach(el => el.remove());
                return document.documentElement.outerHTML;
            }
            cleanHTML();
            """
            result = tab.Runtime.evaluate(expression=clean_html_js)
            html_content = result["result"]["value"]

            tab.stop()
            browser.close_tab(tab)

            return html_content

        except Exception as e:
            raise Exception(f"Failed to fetch page via pychrome: {e}")

    def fetch_categories(self) -> List[Dict]:
        """
        Fetch and parse Reuters categories from the homepage using pychrome.
        
        Returns:
            A list of dictionaries containing category metadata.
        """
        try:
            html_content = self.fetch_html_with_pychrome(self.base_url)
            soup = BeautifulSoup(html_content, 'html.parser')
            categories = []

            # Locate the navigation element.
            nav = soup.find('nav', attrs={'aria-label': 'Main navigation'})
            if not nav:
                print("No navigation element found on the page.")
                return categories

            # Process top-level categories and subcategories.
            for li in nav.find_all('li', class_=lambda x: x and 'nav-bar__category__' in x):
                main_a = li.find('a', attrs={'data-testid': 'Body'})
                if main_a:
                    main_title = main_a.get_text(strip=True)
                    main_link = main_a.get('href', '')
                    main_slug = self.clean_ltree(main_title)
                    main_category = {
                        'title': main_title,
                        'link': self.base_url.rstrip('/') + main_link if main_link.startswith('/') else main_link,
                        'description': None,
                        'atom_link': None,
                        'path': main_slug,
                        'level': 1
                    }
                    categories.append(main_category)
                else:
                    continue

                # Process subcategories from the dropdown container.
                dropdown = li.find('div', class_=lambda x: x and 'nav-bar__hidden__' in x)
                if dropdown:
                    sub_links = dropdown.find_all('a', attrs={'data-testid': 'Body'})
                    for sub_a in sub_links:
                        sub_title = sub_a.get_text(strip=True)
                        if sub_title.lower().startswith("browse"):
                            continue
                        sub_link = sub_a.get('href', '')
                        sub_slug = self.clean_ltree(sub_title)
                        full_path = main_slug + '.' + sub_slug
                        sub_category = {
                            'title': sub_title,
                            'link': self.base_url.rstrip('/') + sub_link if sub_link.startswith('/') else sub_link,
                            'description': None,
                            'atom_link': None,
                            'path': full_path,
                            'level': 2
                        }
                        categories.append(sub_category)

            # Process additional "More" sections if present.
            more_container = nav.find('div', attrs={'data-testid': 'moreSectionDropdownContainer'})
            if more_container:
                more_sections = more_container.find_all('section', attrs={'data-testid': 'MoreDropdown'})
                for sec in more_sections:
                    main_heading = sec.find('a', attrs={'data-testid': 'Heading'})
                    if main_heading:
                        more_main_title = main_heading.get_text(strip=True)
                        more_main_link = main_heading.get('href', '')
                        more_main_slug = self.clean_ltree(more_main_title)
                        more_main_category = {
                            'title': more_main_title,
                            'link': self.base_url.rstrip('/') + more_main_link if more_main_link.startswith('/') else more_main_link,
                            'description': None,
                            'atom_link': None,
                            'path': more_main_slug,
                            'level': 1
                        }
                        categories.append(more_main_category)
                        ul = sec.find('ul')
                        if ul:
                            for li in ul.find_all('li'):
                                sub_a = li.find('a')
                                if sub_a:
                                    sub_title = sub_a.get_text(strip=True)
                                    if sub_title.lower().startswith("browse"):
                                        continue
                                    sub_link = sub_a.get('href', '')
                                    sub_slug = self.clean_ltree(sub_title)
                                    full_path = more_main_slug + '.' + sub_slug
                                    sub_category = {
                                        'title': sub_title,
                                        'link': self.base_url.rstrip('/') + sub_link if sub_link.startswith('/') else sub_link,
                                        'description': None,
                                        'atom_link': None,
                                        'path': full_path,
                                        'level': 2
                                    }
                                    categories.append(sub_category)
            print(f"Found {len(categories)} categories in total.")
            return categories

        except Exception as e:
            raise Exception(f"Failed to fetch categories: {e}")

    def store_categories(self, categories: List[Dict]):
        """
        Store categories in the database using SQLAlchemy ORM.
        """
        session = self.get_session()
        try:
            print("Storing categories in database...")
            count_added = 0
            for cat_data in categories:
                slug = self.clean_ltree(cat_data.get('title')) if cat_data.get('title') else 'unknown'
                # Check for an existing category by slug and portal_id.
                existing = session.query(self.CategoryModel).filter(
                    self.CategoryModel.slug == slug,
                    self.CategoryModel.portal_id == self.portal_id
                ).first()
                if existing:
                    print(f"Category with slug '{slug}' already exists. Skipping insertion.")
                    continue

                category = self.CategoryModel(
                    name=cat_data.get('title'),
                    slug=slug,
                    portal_id=self.portal_id,
                    path=cat_data.get('path'),
                    level=cat_data.get('level'),
                    description=cat_data.get('description'),
                    link=cat_data.get('link'),
                    atom_link=cat_data.get('atom_link'),
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
        Main method to fetch and store Reuters categories.
        """
        try:
            categories = self.fetch_categories()
            self.store_categories(categories)
            print("Category processing completed successfully.")
        except Exception as e:
            print(f"Error processing categories: {e}")
            raise


def main():
    """
    Script entry point.
    """
    # Import Base from your models file to inspect the metadata.
    from db_scripts.models.models import Base
    print("Registered tables in metadata:", Base.metadata.tables.keys())

    argparser = argparse.ArgumentParser(description="Reuters RSS Categories Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment to load data (default: dev)"
    )
    args = argparser.parse_args()

    portal_prefix = "pt_reuters"  # The Reuters portal prefix.
    try:
        portal_id = fetch_portal_id_by_prefix(portal_prefix, env=args.env)
        print(f"Using portal_id: {portal_id} for portal_prefix: {portal_prefix}")

        parser_instance = ReutersRSSCategoriesParser(
            portal_id=portal_id,
            env=args.env,
            category_model=ReutersCategory
        )
        parser_instance.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
