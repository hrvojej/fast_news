from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import re
from etl.common.base.base_html_scraper import BaseHtmlScraper
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class CNNHtmlCategoryScraper(BaseHtmlScraper):
    def __init__(self):
        super().__init__(
            portal_id=3,
            portal_name="CNN",
            portal_domain="cnn.com"
        )
        self.base_url = 'https://edition.cnn.com'

    def get_categories(self) -> List[Dict[str, Any]]:
        """Extract CNN categories from HTML navigation."""
        categories = []
        try:
            soup = self.get_page_content(self.base_url)
            if not soup:
                logger.error("Failed to fetch CNN homepage")
                return categories

            nav = soup.find('nav', class_='subnav')
            if not nav:
                logger.error("Could not find main navigation")
                return categories

            sections = nav.find_all('li', class_='subnav__section')
            logger.info(f"Found {len(sections)} main categories")

            for section in sections:
                main_link = section.find('a', class_='subnav__section-link')
                if not main_link:
                    continue

                main_url = self.get_absolute_url(self.base_url, main_link.get('href', ''))
                main_title = main_link.text.strip()
                main_slug = self._generate_slug(main_url)

                main_category = {
                    'name': main_title,
                    'slug': main_slug,
                    'portal_id': self.portal_id,
                    'path': self._clean_ltree(main_title),
                    'level': 1,
                    'title': main_title,
                    'link': main_url,
                    'atom_link': None,
                    'description': f"CNN {main_title} section",
                    'language': 'en'
                }
                categories.append(main_category)

                subsections = section.find_all('li', class_='subnav__subsection')
                for subsection in subsections:
                    sub_link = subsection.find('a', class_='subnav__subsection-link')
                    if not sub_link:
                        continue

                    sub_url = self.get_absolute_url(self.base_url, sub_link.get('href', ''))
                    sub_title = sub_link.text.strip()
                    sub_slug = self._generate_slug(sub_url)

                    subcategory = {
                        'name': sub_title,
                        'slug': sub_slug,
                        'portal_id': self.portal_id,
                        'path': f"{self._clean_ltree(main_title)}.{self._clean_ltree(sub_title)}",
                        'level': 2,
                        'title': sub_title,
                        'link': sub_url,
                        'atom_link': None,
                        'description': f"CNN {main_title} - {sub_title}",
                        'language': 'en'
                    }
                    categories.append(subcategory)

            logger.info(f"Extracted {len(categories)} total categories")
            return categories

        except Exception as e:
            logger.error(f"Error scraping CNN categories: {str(e)}")
            return categories

    def _generate_slug(self, url: str) -> str:
        """Generate a unique slug from URL."""
        if not url:
            return 'home'
        try:
            path = url.split('//')[1].split('/')[1:]
            path = [p for p in path if p and p not in ['index.html', 'article', 'articles']]
            return '_'.join(path) if path else 'home'
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
