from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
import re
from datetime import datetime
from etl.common.utils.request_manager import request_manager
from etl.common.database.database_manager import db_manager
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class BaseScraper(ABC):
    def __init__(self, portal_id: int, portal_name: str, portal_domain: str):
        self.portal_id = portal_id
        self.portal_name = portal_name
        self.portal_domain = portal_domain
        self.request_manager = request_manager
        self.db_manager = db_manager
        
    @abstractmethod
    def get_categories(self) -> List[Dict[str, Any]]:
        """Fetch and parse portal categories."""
        pass
    
    @abstractmethod
    def get_articles(self, category_id: int, category_url: str) -> List[Dict[str, Any]]:
        """Fetch and parse articles for a category."""
        pass
    
    def clean_text(self, text: str) -> str:
        """Clean text from special characters and normalize whitespace."""
        if not text:
            return ""
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        return text

    def parse_date(self, date_str: str, formats: List[str]) -> Optional[datetime]:
        """Try to parse date string using multiple formats."""
        if not date_str:
            return None
            
        for date_format in formats:
            try:
                return datetime.strptime(date_str, date_format)
            except ValueError:
                continue
        return None

    def validate_url(self, url: str) -> str:
        """Ensure URL is absolute and properly formatted."""
        if not url:
            return ""
        if not url.startswith(('http://', 'https://')):
            url = f"https://{self.portal_domain.strip('/')}/{url.lstrip('/')}"
        return url

    def get_soup(self, url: str, parser: str = 'html.parser') -> BeautifulSoup:
        """Get BeautifulSoup object for a URL."""
        response = self.request_manager.get(url, timeout=30)
        return BeautifulSoup(response.content, parser)

    def save_categories(self, categories: List[Dict[str, Any]]) -> None:
        """Save categories to database."""
        if not categories:
            return

        query = """
        INSERT INTO categories (
            name, slug, portal_id, path, level, title, link, 
            atom_link, description, language
        ) VALUES (
            %(name)s, %(slug)s, %(portal_id)s, %(path)s, %(level)s,
            %(title)s, %(link)s, %(atom_link)s, %(description)s, %(language)s
        ) ON CONFLICT (slug, portal_id) DO NOTHING
        """
        
        self.db_manager.execute_many(query, categories)

    def save_articles(self, articles: List[Dict[str, Any]]) -> None:
        """Save articles to database."""
        if not articles:
            return

        query = """
        INSERT INTO articles (
            title, url, guid, description, author, pub_date, 
            category_id, keywords, image_url, image_width, image_credit
        ) VALUES (
            %(title)s, %(url)s, %(guid)s, %(description)s, %(author)s,
            %(pub_date)s, %(category_id)s, %(keywords)s, %(image_url)s,
            %(image_width)s, %(image_credit)s
        ) ON CONFLICT (guid) DO NOTHING
        """
        
        self.db_manager.execute_many(query, articles)