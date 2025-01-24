"""
CNN HTML Scraper Tests

Run specific test:
python -m unittest tests/unit/portals/test_cnn_scraper.py -v

Run single test case:
python -m unittest tests/unit/portals/test_cnn_scraper.py TestCNNHtmlScraper.test_fetch_categories -v

Run all portal tests: 
python -m unittest discover tests/unit/portals -v

Environment setup required:
- Set NEWS_ENV=development
- Database must be initialized
- Internet connection required for scraping
"""

import unittest
from etl.portals.cnn.cnn_html_category_scraper import CNNHtmlCategoryScraper
from etl.portals.cnn.cnn_html_article_scraper import CNNHtmlArticleScraper

class TestCNNHtmlScraper(unittest.TestCase):
    def setUp(self):
        self.category_scraper = CNNHtmlCategoryScraper()
        self.article_scraper = CNNHtmlArticleScraper()

    def test_fetch_categories(self):
        categories = self.category_scraper.get_categories()
        self.assertIsNotNone(categories)
        self.assertGreater(len(categories), 0)
        
        first_cat = categories[0]
        self.assertIn('title', first_cat)
        self.assertIn('link', first_cat)

    def test_process_articles(self):
        # Test with known CNN category URL
        test_url = "https://edition.cnn.com/world"
        category_id = 1
        
        articles = self.article_scraper.get_category_articles(
            category_id=category_id,
            category_url=test_url
        )
        
        self.assertIsInstance(articles, list)
        self.assertGreater(len(articles), 0)
        
        first_article = articles[0]
        self.assertIn('title', first_article)
        self.assertIn('url', first_article)
        self.assertIn('category_id', first_article)

if __name__ == '__main__':
    unittest.main()
