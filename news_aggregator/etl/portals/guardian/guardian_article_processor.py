from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from etl.common.base.base_rss_scraper import BaseRssScraper
from etl.portals.nyt.nyt_keyword_extractor import NYTKeywordExtractor
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class GuardianArticleProcessor(BaseRssScraper):
    def __init__(self):
        super().__init__(
            portal_id=4,
            portal_name="The Guardian",
            portal_domain="theguardian.com"
        )
        self.keyword_extractor = NYTKeywordExtractor()

    def process_articles(self):
        """Process Guardian RSS articles."""
        try:
            categories = self.db_manager.execute_query("""
                SELECT category_id, atom_link, name 
                FROM guardian.categories 
                WHERE atom_link IS NOT NULL 
                ORDER BY category_id;
            """)

            logger.info(f"Found {len(categories)} categories to process")
            
            stats = {'articles': 0, 'with_images': 0, 'with_keywords': 0}
            for category in categories:
                try:
                    category_stats = self.process_category_articles(
                        category['category_id'],
                        category['atom_link'],
                        category['name']
                    )
                    stats['articles'] += category_stats['articles']
                    stats['with_images'] += category_stats['with_images']
                    stats['with_keywords'] += category_stats['with_keywords']
                except Exception as e:
                    logger.error(f"Error processing category {category['name']}: {str(e)}")
                    continue

            logger.info("\nProcessing complete. Final statistics:")
            logger.info(f"Total articles: {stats['articles']}")
            logger.info(f"With images: {stats['with_images']}")
            logger.info(f"With keywords: {stats['with_keywords']}")

        except Exception as e:
            logger.error(f"Error in article processing: {str(e)}")
            raise

    def process_category_articles(self, category_id: int, atom_link: str, category_name: str) -> Dict[str, int]:
        """Process articles for a single category."""
        stats = {'articles': 0, 'with_images': 0, 'with_keywords': 0}
        
        try:
            soup = self.get_feed_content(atom_link)
            if not soup:
                return stats

            items = soup.find_all('item')
            logger.info(f"Found {len(items)} items in feed {category_name}")

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
                        logger.error(f"Error parsing article: {str(e)}")
                        continue

                if articles:
                    stats['articles'] += self.upsert_articles(articles)
                    
            logger.info(f"Category {category_name} complete:")
            logger.info(f"Articles: {stats['articles']}")
            logger.info(f"With images: {stats['with_images']}")
            logger.info(f"With keywords: {stats['with_keywords']}")

        except Exception as e:
            logger.error(f"Error processing feed {atom_link}: {str(e)}")

        return stats

    def parse_article(self, item: BeautifulSoup, category_id: int) -> Dict:
        """Parse a single Guardian RSS article."""
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

        # Parse publication date
        pub_date = item.find('pubDate')
        if pub_date and pub_date.text:
            try:
                dt = datetime.strptime(pub_date.text.strip(), '%a, %d %b %Y %H:%M:%S %z')
                article['pub_date'] = dt.astimezone(timezone.utc)
            except Exception as e:
                logger.warning(f"Could not parse date {pub_date.text}: {e}")

        # Extract authors
        dc_creators = item.find_all('dc:creator')
        if dc_creators:
            article['author'] = [creator.text.strip() for creator in dc_creators]

        # Extract keywords
        keywords = []
        for category in item.find_all('category'):
            keyword = category.text.strip()
            if keyword and len(keyword) > 2:
                keywords.append(keyword)

        # Add additional keywords from title
        title_keywords = self.keyword_extractor.extract_keywords(article['title'])
        if title_keywords:
            keywords.extend(title_keywords)
        article['keywords'] = list(set(keywords))

        # Extract media content
        media_content = item.find('media:content')
        if media_content:
            article['image_url'] = media_content.get('url')
            width = media_content.get('width')
            article['image_width'] = int(width) if width and width.isdigit() else None
            credit = media_content.find('media:credit')
            article['image_credit'] = credit.text.strip() if credit else 'The Guardian'

        return article
