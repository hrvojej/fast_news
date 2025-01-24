"""
NYT RSS Scraper Tests

Run specific test:
python -m unittest tests/unit/portals/test_nyt_scraper.py -v

Run single test case:
python -m unittest tests/unit/portals/test_nyt_scraper.py TestNYTRssScraper.test_fetch_categories -v

Run all portal tests:
python -m unittest discover tests/unit/portals -v

Environment setup required:
- Set NEWS_ENV=development
- Database must be initialized
- Internet connection required for RSS feeds
"""

import unittest
from etl.portals.nyt.nyt_rss_scraper import NYTRssScraper
from etl.portals.nyt.nyt_rss_article_processor import NYTArticleProcessor

class TestNYTRssScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = NYTRssScraper()
        self.article_processor = NYTArticleProcessor()

    def test_fetch_categories(self):
        categories = self.scraper.get_categories()
        self.assertIsNotNone(categories)
        self.assertGreater(len(categories), 0)
        
        first_cat = categories[0]
        self.assertIn('title', first_cat)
        self.assertIn('link', first_cat)
        self.assertIn('atom_link', first_cat)
        
    def test_process_articles(self):
        # Test with known NYT RSS feed
        test_feed = "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"
        category_id = 1
        
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
