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
AljazeeraCategory = create_portal_category_model("pt_aljazeera")

class AljazeeraCategoriesParser:
    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=AljazeeraCategory):
        self.portal_id = portal_id
        self.env = env
        self.category_model = category_model
        self.base_url = "https://www.aljazeera.com"
    
    @staticmethod
    def clean_ltree(value: str) -> str:
        if not value:
            return "unknown"
        value = value.replace('>', '.').replace('/', '.').replace('\\', '.').strip().lower()
        value = re.sub(r'[^a-z0-9.]+', '_', value)
        value = re.sub(r'[._]{2,}', '.', value)
        return value.strip('._')
    
    def fetch_page(self, url: str):
        try:
            logger.info(f"Fetching page: {url}")
            response = requests.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch page {url}: {e}")
            return None
    
    def parse_categories(self, ul, parent_path=""):
        categories = []
        for li in ul.find_all("li", recursive=False):
            a_tag = li.find("a", href=True)
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            href = self.base_url + a_tag.get("href") if a_tag["href"].startswith("/") else a_tag["href"]
            cleaned_title = self.clean_ltree(title)
            full_path = f"{parent_path}.{cleaned_title}" if parent_path else cleaned_title
            categories.append({
                'title': title, 'link': href, 'path': full_path, 'level': len(full_path.split('.'))
            })
            submenu_wrapper = li.find("div", class_="submenu_wrapper")
            if submenu_wrapper:
                nested_ul = submenu_wrapper.find("ul")
                if nested_ul:
                    categories.extend(self.parse_categories(nested_ul, full_path))
        return categories
    
    def fetch_main_categories(self):
        soup = self.fetch_page(self.base_url)
        if not soup:
            return []
        nav = soup.find("nav", class_="site-header__navigation")
        ul = nav.find("ul", class_="menu header-menu") if nav else None
        return self.parse_categories(ul) if ul else []
    
    def fetch_sports_categories(self):
        soup = self.fetch_page(f"{self.base_url}/sports/")
        if not soup:
            return []
        scroll_div = soup.find("div", {"data-testid": "scrollable-element"})
        ul = scroll_div.find("ul") if scroll_div else None
        return self.parse_categories(ul) if ul else []
    
    def store_categories(self, categories):
        from db_scripts.db_context import DatabaseContext
        session = DatabaseContext.get_instance(self.env).session().__enter__()
        try:
            count_added = 0
            for cat_data in categories:
                slug = self.clean_ltree(cat_data['title'])
                existing = session.query(self.category_model).filter(
                    self.category_model.slug == slug,
                    self.category_model.portal_id == self.portal_id
                ).first()
                if existing:
                    logger.info(f"Category '{slug}' already exists. Skipping.")
                    continue
                category = self.category_model(
                    name=cat_data['title'], slug=slug, portal_id=self.portal_id,
                    path=cat_data['path'], level=cat_data['level'],
                    description=None, link=cat_data['link'], atom_link=None, is_active=True
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
        try:
            categories = self.fetch_main_categories() + self.fetch_sports_categories()
            unique_categories = {cat['path']: cat for cat in categories}.values()
            self.store_categories(unique_categories)
            logger.info("Category processing completed successfully.")
        except Exception as e:
            logger.error(f"Error processing categories: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description="Al Jazeera Categories Parser")
    parser.add_argument('--env', choices=['dev', 'prod'], default='dev', help="Specify environment")
    args = parser.parse_args()
    portal_id = fetch_portal_id_by_prefix("pt_aljazeera", env=args.env)
    logger.info(f"Using portal_id: {portal_id}")
    parser_instance = AljazeeraCategoriesParser(portal_id=portal_id, env=args.env)
    parser_instance.run()

if __name__ == "__main__":
    main()
