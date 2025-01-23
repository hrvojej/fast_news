from typing import List, Dict, Any
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from etl.common.base.base_html_scraper import BaseHtmlScraper
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class GuardianHtmlCategoryScraper(BaseHtmlScraper):
    def __init__(self):
        super().__init__(
            portal_id=4,
            portal_name="The Guardian",
            portal_domain="theguardian.com"
        )
        self.base_url = 'https://www.theguardian.com'

    def get_categories(self) -> List[Dict[str, Any]]:
        """Extract main categories and subcategories from Guardian navigation."""
        categories = []
        try:
            soup = self.get_page_content(self.base_url)
            if not soup:
                return categories

            main_links = soup.find_all('a', class_='dcr-7612kl')
            logger.info(f"Found {len(main_links)} main categories")

            for main_link in main_links:
                href = main_link.get('href', '')
                if href == '/':
                    href = '/news'  # Special case for home/news
                    
                full_url = urljoin(self.base_url, href)
                title = main_link.text.strip()
                
                main_category = {
                    'title': title,
                    'name': title,
                    'link': full_url,
                    'atom_link': f"{full_url}/rss",
                    'description': f"Guardian {title} section",
                    'language': 'en',
                    'copyright_text': None,
                    'last_build_date': None,
                    'pub_date': None,
                    'portal_id': self.portal_id,
                    'path': self._clean_ltree(title),
                    'level': 1,
                    'slug': self._generate_slug(full_url)
                }
                
                categories.append(main_category)
                categories.extend(self._get_subcategories(full_url, main_category))

            return categories

        except Exception as e:
            logger.error(f"Error scraping Guardian categories: {str(e)}")
            return categories

    def _get_subcategories(self, url: str, parent: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get subcategories from a category page."""
        subcategories = []
        try:
            soup = self.get_page_content(url)
            if not soup:
                return subcategories

            sub_links = soup.find_all('li', class_='dcr-5wkng0')
            for sub_item in sub_links:
                sub_link = sub_item.find('a')
                if not sub_link:
                    continue

                sub_href = sub_link.get('href', '')
                sub_full_url = urljoin(self.base_url, sub_href)
                sub_title = sub_link.text.strip()
                
                subcategories.append({
                    'title': sub_title,
                    'name': sub_title,
                    'link': sub_full_url,
                    'atom_link': f"{sub_full_url}/rss",
                    'description': f"Guardian {parent['title']} - {sub_title}",
                    'language': 'en',
                    'copyright_text': None,
                    'last_build_date': None,
                    'pub_date': None,
                    'portal_id': self.portal_id,
                    'path': f"{parent['path']}.{self._clean_ltree(sub_title)}",
                    'level': 2,
                    'slug': self._generate_slug(sub_full_url)
                })

            return subcategories

        except Exception as e:
            logger.error(f"Error getting subcategories for {url}: {str(e)}")
            return subcategories

    def _generate_slug(self, url: str) -> str:
        """Generate a unique slug from URL."""
        try:
            path = url.split('//')[1].split('/')[1:]
            path = [p for p in path if p and p not in ['index.html', 'article', 'articles']]
            if not path:
                return 'home'
            return '_'.join(path)
        except:
            return 'unknown'

    def _clean_ltree(self, value: str) -> str:
        """Clean string for use as ltree path."""
        if not value:
            return "unknown"
        value = value.replace(">", ".").strip()
        value = re.sub(r"[^a-zA-Z0-9.]+", "_", value.lower())
        value = re.sub(r"[._]{2,}", ".", value)
        return value.strip("._")
