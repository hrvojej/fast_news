"""
Guardian Portal Tests

Run specific test:
python -m unittest tests/unit/portals/test_guardian_scraper.py -v

Run single test case:
python -m unittest tests/unit/portals/test_guardian_scraper.py TestGuardianScraper.test_fetch_categories -v

Run all portal tests:
python -m unittest discover tests/unit/portals -v

Environment setup required:
- Set NEWS_ENV=development
- Database must be initialized
- Internet connection required for scraping/RSS feeds
"""

import unittest
from etl.portals.guardian.guardian_html_category_scraper import GuardianHtmlCategoryScraper
from etl.portals.guardian.guardian_rss_feed_updater import GuardianRssFeedUpdater
from etl.portals.guardian.guardian_article_processor import GuardianArticleProcessor

class TestGuardianScraper(unittest.TestCase):
    def setUp(self):
        self.category_scraper = GuardianHtmlCategoryScraper()
        self.feed_updater = GuardianRssFeedUpdater()
        self.article_processor = GuardianArticleProcessor()

    def test_fetch_categories(self):
        categories = self.category_scraper.get_categories()
        self.assertIsNotNone(categories)
        self.assertGreater(len(categories), 0)
        
        first_cat = categories[0]
        self.assertIn('title', first_cat)
        self.assertIn('link', first_cat)
        self.assertIn('atom_link', first_cat)

    def test_update_feeds(self):
        result = self.feed_updater.update_category_feeds()
        self.assertIsNotNone(result)

    def test_process_articles(self):
        # Test with known Guardian RSS feed
        test_feed = "https://www.theguardian.com/world/rss"
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
