from typing import Dict, Any, List, Optional, Tuple
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from datetime import datetime, timezone
from .base_scraper import BaseScraper

class BaseRssScraper(BaseScraper):
    """Base class for RSS-based scrapers."""
    
    def get_feed_content(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse RSS feed content."""
        logger.debug(f"Fetching RSS feed from {url}")
        response = self.request_manager.get(url)
        if not response:
            logger.warning(f"Failed to fetch RSS feed from {url}")
            return None
        try:
            soup = BeautifulSoup(response.content, 'xml')
            logger.debug(f"Successfully parsed RSS feed from {url}")
            return soup
        except Exception as e:
            logger.error(f"Error parsing RSS feed from {url}: {str(e)}")
            return None

    def parse_feed_metadata(self, channel: BeautifulSoup) -> Dict[str, Any]:
        """Parse RSS feed metadata."""
        return {
            'title': self._get_text(channel, 'title'),
            'link': self._get_text(channel, 'link'),
            'description': self._get_text(channel, 'description'),
            'language': self._get_text(channel, 'language'),
            'copyright': self._get_text(channel, 'copyright'),
            'last_build_date': self._parse_date(self._get_text(channel, 'lastBuildDate')),
            'pub_date': self._parse_date(self._get_text(channel, 'pubDate')),
            'image_title': self._get_image_data(channel, 'title'),
            'image_url': self._get_image_data(channel, 'url'),
            'image_link': self._get_image_data(channel, 'link')
        }

    def parse_feed_item(self, item: BeautifulSoup, category_id: int) -> Dict[str, Any]:
        """Parse RSS feed item."""
        return {
            'title': self.clean_text(self._get_text(item, 'title')),
            'url': self._get_text(item, 'link'),
            'guid': self._get_text(item, 'guid') or self._get_text(item, 'link'),
            'description': self.clean_text(self._get_text(item, 'description')),
            'author': self._get_authors(item),
            'pub_date': self._parse_date(self._get_text(item, 'pubDate')),
            'category_id': category_id,
            'keywords': self._get_keywords(item),
            'image_url': self._get_media_content(item, 'url'),
            'image_width': self._get_media_content(item, 'width'),
            'image_credit': self._get_media_content(item, 'credit')
        }

    def _get_text(self, element: BeautifulSoup, tag: str) -> Optional[str]:
        """Extract text from XML element."""
        found = element.find(tag)
        return found.text.strip() if found else None

    def _get_image_data(self, channel: BeautifulSoup, attribute: str) -> Optional[str]:
        """Extract image data from channel."""
        image = channel.find('image')
        return image.find(attribute).text.strip() if image and image.find(attribute) else None

    def _get_authors(self, item: BeautifulSoup) -> List[str]:
        """Extract authors from item."""
        authors = []
        if item.find('author'):
            authors.append(item.find('author').text.strip())
        dc_creators = item.find_all('dc:creator')
        authors.extend([creator.text.strip() for creator in dc_creators])
        return list(set(filter(None, authors)))

    def _get_keywords(self, item: BeautifulSoup) -> List[str]:
        """Extract keywords from item."""
        categories = item.find_all('category')
        return list({cat.text.strip() for cat in categories if cat.text.strip()})

    def _get_media_content(self, item: BeautifulSoup, attribute: str) -> Optional[str]:
        """Extract media content from item."""
        media = item.find('media:content')
        if not media:
            return None
        if attribute == 'url':
            return media.get('url')
        elif attribute == 'width':
            width = media.get('width')
            return int(width) if width and width.isdigit() else None
        elif attribute == 'credit':
            credit = media.find('media:credit')
            return credit.text.strip() if credit else None
        return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime."""
        if not date_str:
            return None
        try:
            dt = date_parser.parse(date_str)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None

    def validate_rss(self, content: str) -> Tuple[bool, Optional[BeautifulSoup], Optional[str]]:
        """Validate RSS feed content.
        
        Args:
            content: Raw RSS feed content
            
        Returns:
            Tuple of (is_valid, parsed_content, error_message)
        """
        try:
            soup = BeautifulSoup(content, 'xml')
            if not soup.find('rss'):
                return False, None, "Invalid RSS format: missing <rss> tag"
            if not soup.find('channel'):
                return False, None, "Invalid RSS format: missing <channel> tag"
            return True, soup, None
        except Exception as e:
            return False, None, f"RSS parsing error: {str(e)}"
