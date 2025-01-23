from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
from etl.common.base.base_html_scraper import BaseHtmlScraper
from etl.portals.nyt.nyt_keyword_extractor import NYTKeywordExtractor
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class CNNHtmlArticleScraper(BaseHtmlScraper):
    def __init__(self):
        super().__init__(
            portal_id=3,
            portal_name="CNN",
            portal_domain="cnn.com"
        )
        self.keyword_extractor = NYTKeywordExtractor()

    def get_category_articles(self, category_id: int, category_url: str) -> List[Dict[str, Any]]:
        """Fetch and parse articles from a CNN category page."""
        articles = []
        try:
            soup = self.get_page_content(category_url)
            if not soup:
                return articles

            article_cards = []
            for selector in [
                'div[data-component-name="card"]',
                'div.container__item',
                'div[data-uri*="card"]'
            ]:
                if not article_cards:
                    article_cards = soup.select(selector)

            logger.info(f"Found {len(article_cards)} article cards")

            for card in article_cards:
                try:
                    article = self.parse_article_card(card, category_id, category_url)
                    if article and article['title'] and article['url']:
                        articles.append(article)
                except Exception as e:
                    logger.error(f"Error parsing article card: {str(e)}")
                    continue

            logger.info(f"Successfully parsed {len(articles)} articles")
            return articles

        except Exception as e:
            logger.error(f"Error fetching category {category_url}: {str(e)}")
            return articles

    def parse_article_card(self, card: BeautifulSoup, category_id: int, base_url: str) -> Optional[Dict]:
        """Parse a single CNN article card."""
        link_elem = card.find('a', class_='container__link') or card.find('a', href=True)
        if not link_elem or not link_elem.get('href'):
            return None

        url = urljoin(base_url, link_elem.get('href', '').strip())

        # Extract title
        title = None
        title_elem = link_elem.find('span', class_='container__headline-text')
        if title_elem:
            title = self.clean_html_text(title_elem.text)
        if not title:
            headline_div = link_elem.find('div', class_='container__headline')
            if headline_div:
                title = self.clean_html_text(headline_div.text)
        if not title:
            link_text = self.clean_html_text(link_elem.get_text())
            if len(link_text) > 10:
                title = link_text

        if not title:
            return None

        # Clean title
        title = re.sub(r'►\s*Video\s*►\s*', '', title)
        title = re.sub(r'▶\s*', '', title)
        title = re.sub(r'\s*\d+:\d+\s*$', '', title)

        # Extract image
        image_data = None
        image = card.find('img')
        if image:
            image_data = {
                'url': image.get('src') or image.get('data-src'),
                'width': int(image.get('width')) if image.get('width', '').isdigit() else None,
                'credit': 'CNN'
            }

        # Generate keywords
        keywords = self.keyword_extractor.extract_keywords(title)

        return {
            'title': title,
            'url': url,
            'guid': url,
            'description': None,
            'author': [],
            'pub_date': datetime.now(),
            'category_id': category_id,
            'keywords': keywords,
            'image_url': image_data['url'] if image_data else None,
            'image_width': image_data['width'] if image_data else None,
            'image_credit': image_data['credit'] if image_data else None
        }
