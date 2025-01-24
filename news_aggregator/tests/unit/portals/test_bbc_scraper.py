"""
Base Scraper Unit Tests

Run all base scraper tests:
python -m unittest tests/unit/portals/test_base_scrapers.py -v

Run specific test class:
python -m unittest tests/unit/portals/test_base_scrapers.py TestBaseScraperMethods -v
python -m unittest tests/unit/portals/test_base_scrapers.py TestBaseHtmlScraperMethods -v
python -m unittest tests/unit/portals/test_base_scrapers.py TestBaseRssScraperMethods -v

Run single test:
python -m unittest tests/unit/portals/test_base_scrapers.py TestBaseScraperMethods.test_clean_text -v

Environment setup required:
- Set NEWS_ENV=development
- No database or internet connection required (uses mocks)
"""

import unittest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup
from etl.common.base.base_scraper import BaseScraper
from etl.common.base.base_html_scraper import BaseHtmlScraper
from etl.common.base.base_rss_scraper import BaseRssScraper
from etl.portals.bbc.bbc_rss_category_parser import BBCRssCategoryParser
from etl.portals.bbc.bbc_rss_article_processor import BBCArticleProcessor

class TestBBCRssScraper(unittest.TestCase):
    def setUp(self):
        self.category_parser = BBCRssCategoryParser()
        self.article_processor = BBCArticleProcessor()

    def test_fetch_categories(self):
        categories = self.category_parser.fetch_and_parse_categories()
        self.assertIsNotNone(categories)
        self.assertGreater(len(categories), 0)
        
        # Verify first category structure
        first_cat = categories[0]
        self.assertIn('title', first_cat)
        self.assertIn('link', first_cat)
        self.assertIn('atom_link', first_cat)

    def test_process_single_category(self):
        # Use a known BBC RSS feed
        test_feed = "https://feeds.bbci.co.uk/news/world/rss.xml"
        category_id = 1  # Use a test category_id
        
        stats = self.article_processor.process_category_articles(
            category_id=category_id,
            atom_link=test_feed,
            category_name="World News"
        )
        
        self.assertIsInstance(stats, dict)
        self.assertIn('articles', stats)
        self.assertIn('with_images', stats)
        self.assertIn('with_keywords', stats)

if __name__ == '__main__':
    unittest.main()
