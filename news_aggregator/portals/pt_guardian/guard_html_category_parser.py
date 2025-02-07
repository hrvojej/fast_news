# path: news_dagster-etl/news_aggregator/portals/guardian/rss_categories_parser.py
"""
Guardian Categories Parser
Fetches and stores Guardian categories using SQLAlchemy ORM.
"""

import sys
import os
from typing import List, Dict
from uuid import UUID
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin
from sqlalchemy import text

# Add the package root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Import the dynamic model factory
from db_scripts.models.models import create_portal_category_model

# Create the dynamic category model for the Guardian portal
GuardianCategory = create_portal_category_model("pt_guardian")

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

class GuardianCategoriesParser:
    """Parser for Guardian categories and subcategories"""

    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=None):
        """
        Initialize the parser

        Args:
            portal_id: UUID of the Guardian portal in news_portals table
            env: Environment to use (dev/prod)
            category_model: SQLAlchemy ORM model for categories
        """
        self.portal_id = portal_id
        self.env = env
        self.base_url = 'https://www.theguardian.com'
        self.GuardianCategory = category_model
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }

    def get_session(self):
        """Get a database session from the DatabaseContext."""
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        return db_context.session().__enter__()

    @staticmethod
    def clean_ltree(value: str) -> str:
        """Convert category title into valid ltree path."""
        if not value:
            return "unknown"
        value = value.replace('>', '.').strip()
        value = re.sub(r"[^a-zA-Z0-9.]+", "_", value.lower())
        value = re.sub(r"[._]{2,}", ".", value)
        return value.strip("._")

    @staticmethod
    def generate_slug(url: str) -> str:
        """Generate a unique slug from URL."""
        try:
            path = url.split('//')[1].split('/')[1:]
            path = [p for p in path if p and p not in ['index.html', 'article', 'articles']]
            if not path:
                return 'home'
            return '_'.join(path)
        except:
            return 'unknown'

    def fetch_html_content(self) -> str:
        """Fetch HTML content from Guardian website."""
        try:
            print(f"Requesting URL: {self.base_url}")
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch Guardian homepage: {str(e)}")

    def validate_html_content(self, html_content: str) -> bool:
        """Validate if the HTML content contains expected elements."""
        if not html_content:
            raise Exception("Empty HTML content")
            
        soup = BeautifulSoup(html_content, 'html.parser')
        nav_links = soup.find_all('a', class_='dcr-7612kl')
        
        if not nav_links:
            raise Exception("Could not find main navigation links")
            
        return True

    def extract_categories(self, html_content: str) -> List[Dict]:
        """Extract main categories and subcategories from Guardian navigation."""
        self.validate_html_content(html_content)
        soup = BeautifulSoup(html_content, 'html.parser')
        categories = []
        
        main_links = soup.find_all('a', class_='dcr-7612kl')
        print(f"Found {len(main_links)} main categories")
        
        for main_link in main_links:
            href = main_link.get('href', '')
            if href == '/':
                href = '/news'  # Special case for home/news
                
            full_url = urljoin(self.base_url, href)
            title = main_link.text.strip()
            
            # Get meta description if available
            meta_desc = soup.find('meta', {'name': 'description'})
            description = meta_desc['content'] if meta_desc else None

            main_category = {
                'name': title,
                'slug': self.generate_slug(full_url),
                'portal_id': self.portal_id,  # Explicitly include portal_id
                'path': self.clean_ltree(title),
                'level': 1,
                'description': description,
                'link': full_url,
                'atom_link': f"{full_url}/rss",
                'is_active': True
                # category_id is handled by server_default
            }
            
            # Fetch subcategories
            try:
                response = requests.get(full_url, headers=self.headers, timeout=30)
                if response.status_code == 200:
                    sub_soup = BeautifulSoup(response.text, 'html.parser')
                    sub_links = sub_soup.find_all('li', class_='dcr-5wkng0')
                    
                    for sub_item in sub_links:
                        sub_link = sub_item.find('a')
                        if sub_link:
                            sub_href = sub_link.get('href', '')
                            sub_full_url = urljoin(self.base_url, sub_href)
                            sub_title = sub_link.text.strip()
                            
                            # Try to get subcategory description
                            sub_desc = sub_soup.find('meta', {'name': 'description'})
                            sub_description = sub_desc['content'] if sub_desc else None

                            subcategory = {
                                'name': sub_title,
                                'slug': self.generate_slug(sub_full_url),
                                'portal_id': self.portal_id,  # Explicitly include portal_id
                                'path': f"{main_category['path']}.{self.clean_ltree(sub_title)}",
                                'level': 2,
                                'description': sub_description,
                                'link': sub_full_url,
                                'atom_link': f"{sub_full_url}/rss",
                                'is_active': True
                                # category_id is handled by server_default
                            }
                            categories.append(subcategory)
            except Exception as e:
                print(f"Error fetching subcategories for {title}: {str(e)}")
                
            time.sleep(2)  # Rate limiting
            categories.append(main_category)
        
        return categories

    def store_categories(self, categories: List[Dict]):
        """Store categories using SQLAlchemy ORM."""
        session = self.get_session()
        
        try:
            print("Storing categories in database...")
            count_added = 0
            for category_data in categories:
                existing = session.query(self.GuardianCategory).filter(
                    self.GuardianCategory.slug == category_data['slug'],
                    self.GuardianCategory.portal_id == self.portal_id
                ).first()
                
                if existing:
                    print(f"Category with slug '{category_data['slug']}' already exists. Skipping.")
                    continue

                # Create new category ensuring all fields are explicitly set
                category = self.GuardianCategory(
                    name=category_data['name'],
                    slug=category_data['slug'],
                    portal_id=self.portal_id,
                    path=category_data['path'],
                    level=category_data['level'],
                    description=category_data['description'],
                    link=category_data['link'],
                    atom_link=category_data['atom_link'],
                    is_active=category_data['is_active']
                    # category_id is handled by server_default
                )
                session.add(category)
                count_added += 1

            session.commit()
            print(f"Successfully stored {count_added} new categories")

        except Exception as e:
            session.rollback()
            raise Exception(f"Failed to store categories: {e}")

        finally:
            session.close()

    def run(self):
        """Main method to fetch and store Guardian categories."""
        try:
            html_content = self.fetch_html_content()
            categories = self.extract_categories(html_content)
            self.store_categories(categories)
            print("Category processing completed successfully")
        except Exception as e:
            print(f"Error processing categories: {e}")
            raise

def main():
    """Script entry point."""
    import argparse
    from db_scripts.models.models import Base
    print("Registered tables in metadata:", Base.metadata.tables.keys())

    parser = argparse.ArgumentParser(description="Guardian Categories Parser")
    parser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment to load data (default: dev)"
    )
    args = parser.parse_args()

    portal_prefix = "pt_guardian"
    try:
        portal_id = fetch_portal_id_by_prefix(portal_prefix, env=args.env)
        print(f"Using portal_id: {portal_id} for portal_prefix: {portal_prefix}")

        parser = GuardianCategoriesParser(
            portal_id=portal_id,
            env=args.env,
            category_model=GuardianCategory
        )
        parser.run()
    except Exception as e:
        print(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()