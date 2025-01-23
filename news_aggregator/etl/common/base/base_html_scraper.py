from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
import re
import unicodedata
from datetime import datetime
from urllib.parse import urljoin
from .base_scraper import BaseScraper

class BaseHtmlScraper(BaseScraper):
    """Base class for HTML-based scrapers."""
    
    def get_page_content(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse HTML page content."""
        response = self.request_manager.get(url)
        return BeautifulSoup(response.content, 'html.parser')

    def clean_html_text(self, text: str) -> str:
        """Clean text from HTML and normalize whitespace."""
        if not text:
            return ""
        cleaned = text.strip()
        cleaned = re.sub(r'[\n\r\t\f\v]+', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'[^\S\r\n]+', ' ', cleaned)
        cleaned = re.sub(r'¶|•|■|▪|►|▼|▲|◄|★|☆|⚡', '', cleaned)
        cleaned = "".join(char for char in cleaned if unicodedata.category(char)[0] != "C")
        return cleaned.strip()

    def get_absolute_url(self, base_url: str, relative_url: str) -> str:
        """Convert relative URL to absolute."""
        return urljoin(base_url, relative_url)

    def parse_html_date(self, date_str: str, known_formats: List[str]) -> Optional[datetime]:
        """Parse date from HTML metadata or content."""
        if not date_str:
            return None

        # Try known formats first
        for date_format in known_formats:
            try:
                return datetime.strptime(date_str.strip(), date_format)
            except ValueError:
                continue

        # Try common patterns
        patterns = [
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO format
            r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}',  # MySQL format
            r'\d{2}/\d{2}/\d{4}\s\d{2}:\d{2}',        # Common web format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    return datetime.strptime(match.group(), pattern)
                except ValueError:
                    continue
        return None

    def extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract metadata from HTML head."""
        metadata = {}
        
        # Extract OpenGraph metadata
        for meta in soup.find_all('meta', property=re.compile(r'^og:')):
            key = meta.get('property', '').replace('og:', '')
            value = meta.get('content', '')
            if value:
                metadata[key] = value

        # Extract Twitter card metadata
        for meta in soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')}):
            key = meta.get('name', '').replace('twitter:', '')
            value = meta.get('content', '')
            if value:
                metadata[key] = value

        # Extract standard metadata
        for meta in soup.find_all('meta', attrs={'name': True}):
            key = meta.get('name', '')
            value = meta.get('content', '')
            if value:
                metadata[key] = value

        return metadata

    def extract_main_image(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract main article image data."""
        # Try OpenGraph image first
        og_image = soup.find('meta', property='og:image')
        if og_image:
            return {
                'url': og_image.get('content'),
                'width': self._get_meta_value(soup, 'og:image:width'),
                'height': self._get_meta_value(soup, 'og:image:height'),
                'alt': self._get_meta_value(soup, 'og:image:alt')
            }

        # Try article header image
        article_image = soup.find('img', class_=re.compile(r'(header|main|featured|hero)'))
        if article_image:
            return {
                'url': article_image.get('src'),
                'width': article_image.get('width'),
                'height': article_image.get('height'),
                'alt': article_image.get('alt')
            }

        return None

    def _get_meta_value(self, soup: BeautifulSoup, property_name: str) -> Optional[str]:
        """Helper to get meta tag value."""
        meta = soup.find('meta', property=property_name)
        return meta.get('content') if meta else None
