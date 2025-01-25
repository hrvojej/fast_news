from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import requests
from etl.common.base.base_rss_scraper import BaseRssScraper
from etl.portals.nyt.nyt_keyword_extractor import NYTKeywordExtractor
from etl.common.logging.logging_manager import logging_manager
from etl.common.database.db_manager import DatabaseManager

logger = logging_manager.get_logger(__name__)

class BBCArticleProcessor(BaseRssScraper):
    def __init__(self):
        super().__init__(
            portal_id=2,
            portal_name="BBC",
            portal_domain="bbc.com"
        )
        self.keyword_extractor = NYTKeywordExtractor()

    def get_categories(self) -> List[Dict[str, Any]]:
        """Fetch and parse BBC RSS categories."""
        categories = []
        
        # Get existing categories from database
        try:
            db_categories = self.db_manager.execute_query("""
                SELECT category_id, atom_link, name 
                FROM bbc.categories 
                WHERE atom_link IS NOT NULL 
                ORDER BY category_id;
            """)
            
            for cat in db_categories:
                categories.append({
                    'name': cat['name'],
                    'slug': cat['name'].lower().replace(' ', '_'),
                    'portal_id': self.portal_id,
                    'path': self.clean_ltree(cat['name']),
                    'level': 1,
                    'title': cat['name'],
                    'link': f"https://www.bbc.com/{cat['name'].lower().replace(' ', '-')}",
                    'atom_link': cat['atom_link'],
                    'description': f"BBC {cat['name']} news feed",
                    'language': 'en'
                })
                
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            
        return categories

    def get_articles(self, category_id: int, category_url: str) -> List[Dict[str, Any]]:
        """Fetch and parse articles for a category."""
        logger.info(f"Starting to fetch articles for category {category_id} from {category_url}")
        articles = []
        is_valid, soup, error = self.validate_rss(category_url)
        
        if not is_valid:
            logger.error(f"Invalid RSS feed for category {category_id}: {error}")
            return articles

        logger.info(f"Successfully validated RSS feed. Found {len(soup.find_all('item'))} items.")
        items = soup.find_all('item')
        
        for item in items:
            logger.debug(f"Processing item: {item.find('title').text if item.find('title') else 'No title'}")
            try:
                article = self.parse_article(item, category_id)
                logger.debug(f"Parsed article: {article}")
                articles.append(article)
            except Exception as e:
                logger.error(f"Error parsing article: {str(e)}")
                continue

        logger.info(f"Finished processing. Returning {len(articles)} articles.")
        print(f"=== ARTICLES RETURNED BY get_articles ===")
        print(f"Total articles: {len(articles)}")
        if articles:
            for i, article in enumerate(articles, 1):
                print(f"Article {i}:")
                print(f"Title: {article.get('title', 'No title')}")
                print(f"URL: {article.get('url', 'No URL')}")
                print(f"Description: {article.get('description', 'No description')}")
                print("-" * 50)
        else:
            print("No articles found or returned.")
        print("=" * 50)
        return articles

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
        except Exception as e:
            logger.error(f"Error processing category {category_name}: {e}")
            raise
        return stats

    def clean_ltree(self, text: str) -> str:
        """Clean text to be used in ltree paths.
        
        Args:
            text: Input text to clean
            
        Returns:
            Cleaned string suitable for ltree
        """
        # Convert to lowercase
        text = text.lower()
        # Replace special characters and spaces with single underscore
        text = ''.join('_' if c in ' &!@#$%^&*()[]{};:,./<>?\|`~=+' else c for c in text)
        # Remove consecutive underscores
        while '__' in text:
            text = text.replace('__', '_')
        # Remove leading/trailing underscores
        text = text.strip('_')
        # Ensure it's not empty
        return text or 'root'

    def parse_article(self, item: BeautifulSoup, category_id: int) -> Dict:
        """Parse a single BBC RSS article."""
        logger.debug("Starting to parse article")
        
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
        
        logger.debug(f"Item being parsed: {item}")
        
        logger.debug(f"Parsed basic article fields: {article}")

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
