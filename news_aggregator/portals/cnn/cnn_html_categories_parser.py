import sys
import os
from typing import List, Dict
from uuid import UUID
import requests
from bs4 import BeautifulSoup
import re
from sqlalchemy import text

current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from db_scripts.models.models import create_portal_category_model
CNNCategory = create_portal_category_model("pt_cnn")

def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev') -> UUID:
    from db_scripts.db_context import DatabaseContext
    db_context = DatabaseContext.get_instance(env)
    with db_context.session() as session:
        result = session.execute(
            text("SELECT portal_id FROM public.news_portals WHERE portal_prefix = :prefix"),
            {'prefix': portal_prefix}
        ).fetchone()
        if result:
            return result[0]
        raise Exception(f"Portal with prefix '{portal_prefix}' not found.")

class CNNCategoriesParser:
    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=None):
        self.portal_id = portal_id
        self.env = env
        self.base_url = "https://edition.cnn.com/"
        self.CNNCategory = category_model
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
        }

    def get_session(self):
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        return db_context.session().__enter__()

    @staticmethod
    def clean_ltree(value: str) -> str:
        if not value:
            return "unknown"
        value = value.replace('>', '.').strip()
        value = re.sub(r"[^a-zA-Z0-9.]+", "_", value.lower())
        value = re.sub(r"[._]{2,}", ".", value)
        return value.strip("._")

    @staticmethod
    def generate_slug(url: str, title: str) -> str:
        if not url:
            return CNNCategoriesParser.clean_ltree(title or 'unknown')
        try:
            path = url.split('//')[1].split('/')[1:]
            path = [p for p in path if p and p not in ['index.html', 'article', 'articles']]
            return '_'.join(path) if path else CNNCategoriesParser.clean_ltree(title or 'unknown')
        except:
            return CNNCategoriesParser.clean_ltree(title or 'unknown')

    def fetch_html_content(self) -> str:
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch CNN homepage: {e}")

    def extract_categories(self, html_content: str) -> List[Dict]:
        soup = BeautifulSoup(html_content, 'html.parser')
        nav = soup.find('nav', class_='subnav')
        if not nav:
            raise Exception("Could not find main navigation")

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

            categories.append(main_category)
            print(f"Processing category: {main_title}")

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
                print(f"Processing subcategory: {sub_title}")

                categories.append(subcategory)

        return categories

    def store_categories(self, categories: List[Dict]):
        session = self.get_session()
        try:
            for category_data in categories:
                existing = session.query(self.CNNCategory).filter(
                    self.CNNCategory.slug == category_data['slug'],
                    self.CNNCategory.portal_id == self.portal_id
                ).first()
                
                if not existing:
                    category = self.CNNCategory(
                        name=category_data['title'],
                        slug=category_data['slug'],
                        portal_id=self.portal_id,
                        path=category_data['path'],
                        level=category_data['level'],
                        description=category_data['description'],
                        link=category_data['link'],
                        is_active=True
                    )
                    session.add(category)
            
            session.commit()
        except Exception as e:
            session.rollback()
            raise Exception(f"Failed to store categories: {e}")
        finally:
            session.close()

    def run(self):
        try:
            html_content = self.fetch_html_content()
            categories = self.extract_categories(html_content)
            self.store_categories(categories)
        except Exception as e:
            raise Exception(f"Error processing categories: {e}")

def main():
    import argparse
    from db_scripts.models.models import Base
    
    argparser = argparse.ArgumentParser(description="CNN Categories Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    try:
        portal_id = fetch_portal_id_by_prefix("pt_cnn", env=args.env)
        parser = CNNCategoriesParser(portal_id=portal_id, env=args.env, category_model=CNNCategory)
        parser.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()