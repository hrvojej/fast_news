from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
from etl.common.base.base_rss_scraper import BaseRssScraper
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class BBCRssCategoryParser(BaseRssScraper):
    def __init__(self):
        super().__init__(
            portal_id=2,
            portal_name="BBC",
            portal_domain="bbc.com"
        )
        self.base_urls = [
            "https://feeds.bbci.co.uk/news/rss.xml",  # Main news
            "https://feeds.bbci.co.uk/news/world/rss.xml",  # World news
            "https://feeds.bbci.co.uk/news/uk/rss.xml",  # UK news
            "https://feeds.bbci.co.uk/news/business/rss.xml",  # Business
            "https://feeds.bbci.co.uk/news/technology/rss.xml",  # Technology
            "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",  # Science
            "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",  # Entertainment
            "https://feeds.bbci.co.uk/news/health/rss.xml",  # Health
            "https://feeds.bbci.co.uk/news/education/rss.xml",  # Education
            "https://feeds.bbci.co.uk/news/politics/rss.xml",  # Politics
            "https://feeds.bbci.co.uk/sport/rss.xml",  # Main sport
            "https://feeds.bbci.co.uk/sport/football/rss.xml",  # Football
            "https://feeds.bbci.co.uk/sport/cricket/rss.xml",  # Cricket
            "https://feeds.bbci.co.uk/sport/formula1/rss.xml",  # Formula 1
            "https://feeds.bbci.co.uk/sport/rugby-union/rss.xml",  # Rugby Union
            "https://feeds.bbci.co.uk/sport/tennis/rss.xml",  # Tennis
            "https://feeds.bbci.co.uk/sport/golf/rss.xml",  # Golf
            "https://feeds.bbci.co.uk/sport/athletics/rss.xml",  # Athletics
            "https://feeds.bbci.co.uk/sport/cycling/rss.xml",  # Cycling
            "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",  # US & Canada
            "https://feeds.bbci.co.uk/news/world/africa/rss.xml",  # Africa
            "https://feeds.bbci.co.uk/news/world/asia/rss.xml",  # Asia
            "https://feeds.bbci.co.uk/news/world/australia/rss.xml",  # Australia
            "https://feeds.bbci.co.uk/news/world/europe/rss.xml",  # Europe
            "https://feeds.bbci.co.uk/news/world/latin_america/rss.xml",  # Latin America
            "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",  # Middle East
            "https://feeds.bbci.co.uk/news/in_pictures/rss.xml",  # In Pictures
            "https://feeds.bbci.co.uk/news/have_your_say/rss.xml",  # Have Your Say
            "https://feeds.bbci.co.uk/news/live/rss.xml"  # Live news
        ]

    def get_categories(self) -> List[Dict[str, Any]]:
        """Fetch and parse BBC RSS categories."""
        categories = []
        
        for rss_url in self.base_urls:
            try:
                is_valid, soup, error = self.validate_rss(rss_url)
                
                if not is_valid:
                    logger.error(f"Skipping invalid RSS feed {rss_url}: {error}")
                    continue

                channel = soup.find('channel')
                metadata = self.parse_feed_metadata(channel)
                
                path = rss_url.split('//')[1].split('/')[2:-1]
                slug = '_'.join(path) if path else 'main'
                
                categories.append({
                    'name': metadata['title'],
                    'slug': slug,
                    'portal_id': self.portal_id,
                    'path': self.clean_ltree(metadata['title']),
                    'level': len(path),
                    'title': metadata['title'],
                    'link': metadata['link'],
                    'atom_link': rss_url,
                    'description': metadata['description'],
                    'language': metadata['language'],
                    'copyright_text': metadata.get('copyright'),
                    'last_build_date': metadata.get('last_build_date'),
                    'pub_date': metadata.get('pub_date'),
                    'image_title': metadata.get('image_title'),
                    'image_url': metadata.get('image_url'),
                    'image_link': metadata.get('image_link')
                })

                logger.info(f"Successfully processed: {metadata['title']}")
                
            except Exception as e:
                logger.error(f"Error processing feed {rss_url}: {str(e)}")
                continue

        return categories

    def get_articles(self, category_id: int, category_url: str) -> List[Dict[str, Any]]:
        """Fetch and parse articles for a category."""
        articles = []
        is_valid, soup, error = self.validate_rss(category_url)
        
        if not is_valid:
            logger.error(f"Invalid RSS feed for category {category_id}: {error}")
            return articles

        items = soup.find_all('item')
        for item in items:
            try:
                article = self.parse_feed_item(item, category_id)
                articles.append(article)
            except Exception as e:
                logger.error(f"Error parsing article: {str(e)}")
                continue

        return articles

    def clean_ltree(self, value: str) -> str:
        """Clean string for use as ltree path."""
        if not value:
            return "unknown"
        value = value.replace(">", ".").strip()
        value = re.sub(r"[^a-zA-Z0-9.]+", "_", value.lower())
        value = re.sub(r"[._]{2,}", ".", value)
        return value.strip("._")

    def validate_rss(self, rss_url: str) -> Tuple[bool, Optional[BeautifulSoup], Optional[str]]:
        """Validate RSS feed and return soup if valid."""
        try:
            logger.info(f"Validating RSS feed: {rss_url}")
            soup = self.get_feed_content(rss_url)
            
            if not soup:
                return False, None, "Failed to fetch feed content"

            if not soup.find('channel'):
                return False, None, "No channel element found"
                
            return True, soup, None
            
        except Exception as e:
            return False, None, f"Error: {str(e)}"