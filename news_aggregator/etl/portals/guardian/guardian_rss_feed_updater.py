from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
from dateutil import parser as date_parser
from etl.common.base.base_rss_scraper import BaseRssScraper
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class GuardianRssFeedUpdater(BaseRssScraper):
    def __init__(self):
        super().__init__(
            portal_id=4,
            portal_name="The Guardian",
            portal_domain="theguardian.com"
        )

    def update_category_feeds(self):
        """Update Guardian categories with RSS feed data."""
        try:
            categories = self.db_manager.execute_query("""
                SELECT category_id, atom_link 
                FROM guardian.categories 
                WHERE atom_link IS NOT NULL 
                AND portal_id = 4;
            """)

            logger.info(f"Found {len(categories)} categories to update")
            
            for category in categories:
                try:
                    self._update_category_feed(category['category_id'], category['atom_link'])
                except Exception as e:
                    logger.error(f"Error updating category {category['category_id']}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error in feed update process: {str(e)}")
            raise

    def _update_category_feed(self, category_id: int, atom_link: str):
        """Update a single category with RSS feed data."""
        try:
            rss_data = self._fetch_rss_data(atom_link)
            if not rss_data:
                return

            self._update_category_metadata(category_id, rss_data)
            logger.info(f"Updated category {category_id} successfully")

        except Exception as e:
            logger.error(f"Error updating category {category_id} feed: {str(e)}")
            raise

    def _fetch_rss_data(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse RSS feed data."""
        try:
            soup = self.get_feed_content(url)
            if not soup:
                return None

            channel = soup.find('channel')
            if not channel:
                return None

            # Find image details
            image = channel.find('image')
            image_data = {}
            if image:
                image_data = {
                    'image_title': self._get_text(image, 'title'),
                    'image_url': self._get_text(image, 'url'),
                    'image_link': self._get_text(image, 'link')
                }

            # Extract feed data
            feed_data = {
                'title': self._get_text(channel, 'title'),
                'link': self._get_text(channel, 'link'),
                'description': self._get_text(channel, 'description'),
                'language': self._get_text(channel, 'language'),
                'copyright_text': self._get_text(channel, 'copyright'),
                'last_build_date': self._parse_date(self._get_text(channel, 'lastBuildDate')),
                'pub_date': self._parse_date(self._get_text(channel, 'pubDate')),
                **image_data
            }

            # Remove "| The Guardian" from title
            if feed_data['title']:
                feed_data['title'] = feed_data['title'].replace(' | The Guardian', '')

            return feed_data

        except Exception as e:
            logger.error(f"Error fetching RSS feed {url}: {str(e)}")
            return None

    def _update_category_metadata(self, category_id: int, rss_data: Dict[str, Any]):
        """Update category with RSS metadata."""
        update_query = """
        UPDATE guardian.categories
        SET 
            title = COALESCE(%s, title),
            link = COALESCE(%s, link),
            description = COALESCE(%s, description),
            language = COALESCE(%s, language),
            copyright_text = COALESCE(%s, copyright_text),
            last_build_date = COALESCE(%s, last_build_date),
            pub_date = COALESCE(%s, pub_date),
            image_title = COALESCE(%s, image_title),
            image_url = COALESCE(%s, image_url),
            image_link = COALESCE(%s, image_link),
            updated_at = CURRENT_TIMESTAMP
        WHERE category_id = %s
        """
        
        self.db_manager.execute_query(update_query, (
            rss_data.get('title'),
            rss_data.get('link'),
            rss_data.get('description'),
            rss_data.get('language'),
            rss_data.get('copyright_text'),
            rss_data.get('last_build_date'),
            rss_data.get('pub_date'),
            rss_data.get('image_title'),
            rss_data.get('image_url'),
            rss_data.get('image_link'),
            category_id
        ))

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime."""
        if not date_str:
            return None
        try:
            return date_parser.parse(date_str)
        except (ValueError, TypeError):
            return None
