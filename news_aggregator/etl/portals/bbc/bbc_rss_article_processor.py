from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from etl.common.base.base_rss_scraper import BaseRssScraper
from etl.portals.nyt.nyt_keyword_extractor import NYTKeywordExtractor
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class BBCArticleProcessor(BaseRssScraper):
    def __init__(self):
        super().__init__(
            portal_id=2,
            portal_name="BBC",
            portal_domain="bbc.com"
        )
        self.keyword_extractor = NYTKeywordExtractor()

    def process_articles(self):
        """Process BBC RSS articles from all categories."""
        try:
            categories = self.db_manager.execute_query("""
                SELECT category_id, atom_link, name 
                FROM bbc.categories 
                WHERE atom_link IS NOT NULL 
                ORDER BY category_id;
            """)

            total_articles = 0
            total_with_images = 0
            total_with_keywords = 0

            for category in categories:
                try:
                    logger.info(f"\nProcessing category: {category['name']}")
                    processed = self.process_category_articles(
                        category['category_id'], 
                        category['atom_link'],
                        category['name']
                    )
                    total_articles += processed['articles']
                    total_with_images += processed['with_images'] 
                    total_with_keywords += processed['with_keywords']

                except Exception as e:
                    logger.error(f"Error processing category {category['name']}: {e}")
                    continue

            logger.info(f"\nProcessing complete. Stats:")
            logger.info(f"Total articles: {total_articles}")
            logger.info(f"With images: {total_with_images}")
            logger.info(f"With keywords: {total_with_keywords}")

        except Exception as e:
            logger.error(f"Error in main processing: {e}")
            raise

    def process_category_articles(self, category_id: int, atom_link: str, category_name: str) -> Dict:
        """Process articles for a single category."""
        stats = {'articles': 0, 'with_images': 0, 'with_keywords': 0}
        
        try:
            soup = self.get_feed_content(atom_link)
            if not soup:
                return stats

            items = soup.find_all('item')
            logger.info(f"Found {len(items)} items in feed")

            batch_size = 50
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                articles = []
                
                for item in batch:
                    try:
                        article = self.parse_article(item, category_id)
                        if article['title'] and article['url']:
                            articles.append(article)
                            if article['image_url']:
                                stats['with_images'] += 1
                            if article['keywords']:
                                stats['with_keywords'] += 1
                    except Exception as e:
                        logger.error(f"Error parsing article: {e}")
                        continue

                if articles:
                    inserted = self.upsert_articles(articles)
                    stats['articles'] += inserted

            logger.info(f"Category {category_name} complete:")
            logger.info(f"Articles: {stats['articles']}")
            logger.info(f"With images: {stats['with_images']}")
            logger.info(f"With keywords: {stats['with_keywords']}")

        except Exception as e:
            logger.error(f"Error processing feed {atom_link}: {e}")

        return stats

    def parse_article(self, item: BeautifulSoup, category_id: int) -> Dict:
        """Parse a single BBC RSS article."""
        article = {
            'title': item.find('title').text.strip() if item.find('title') else '',
            'url': item.find('link').text.strip() if item.find('link') else '',
            'guid': item.find('guid').text.strip() if item.find('guid') else '',
            'description': item.find('description').text.strip() if item.find('description') else '',
            'category_id': category_id,
            'author': [],
            'pub_date': None,
            'keywords': [],
            'image_url': None,
            'image_width': None,
            'image_credit': None
        }

        pub_date = item.find('pubDate')
        if pub_date and pub_date.text:
            try:
                dt = datetime.strptime(pub_date.text.strip(), '%a, %d %b %Y %H:%M:%S %z')
                article['pub_date'] = dt.astimezone(timezone.utc)
            except Exception as e:
                logger.warning(f"Could not parse date {pub_date.text}: {e}")

        # Extract keywords from categories
        categories = item.find_all('category')
        if categories:
            article['keywords'] = [cat.text.strip() for cat in categories if cat.text.strip()]

        # Add additional keywords from title
        title_keywords = self.keyword_extractor.extract_keywords(article['title'])
        if title_keywords:
            article['keywords'].extend(title_keywords)
        article['keywords'] = list(set(article['keywords']))

        # Get image from media:thumbnail
        thumbnail = item.find('media:thumbnail')
        if thumbnail:
            article['image_url'] = thumbnail.get('url')
            width = thumbnail.get('width')
            article['image_width'] = int(width) if width and width.isdigit() else None
            article['image_credit'] = 'BBC News'

        return article
