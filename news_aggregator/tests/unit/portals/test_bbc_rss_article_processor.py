import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from etl.portals.bbc.bbc_rss_article_processor import BBCArticleProcessor
from etl.common.database.db_manager import DatabaseManager

class TestBBCArticleProcessor(unittest.TestCase):

    def setUp(self):
        self.processor = BBCArticleProcessor()
        self.mock_db_manager = MagicMock(spec=DatabaseManager)
        self.processor.db_manager = self.mock_db_manager

    def test_get_categories(self):
        # Mock database query result
        mock_categories = [
            {'category_id': 1, 'atom_link': 'test-link', 'name': 'Test Category'}
        ]
        self.mock_db_manager.execute_query.return_value = mock_categories

        # Get categories
        categories = self.processor.get_categories()

        # Assert results
        self.assertEqual(len(categories), 1)
        self.assertEqual(categories[0]['name'], 'Test Category')
        self.assertEqual(categories[0]['link'], 'https://www.bbc.com/test-category')
        self.assertEqual(categories[0]['atom_link'], 'test-link')

    def test_get_articles(self):
        # Mock RSS feed parsing
        mock_soup = MagicMock()
        mock_soup.find_all.return_value = [
            MagicMock(find=lambda x: MagicMock(text='Test Title' if x == 'title' else 'Test URL')),
            MagicMock(find=lambda x: MagicMock(text='Test Title' if x == 'title' else 'Test URL'))
        ]
        self.processor.validate_rss = lambda x: (True, mock_soup, None)

        # Test article retrieval
        articles = self.processor.get_articles(1, 'test-url')

        # Assert results
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]['title'], 'Test Title')
        self.assertEqual(articles[0]['url'], 'Test URL')

    def test_process_article(self):
        # Mock RSS item
        mock_item = MagicMock()
        mock_item.find.side_effect = lambda x: MagicMock(text='Test Title') if x == 'title' else \
            MagicMock(text='Test URL') if x == 'link' else \
            MagicMock(text='Test Description') if x == 'description' else None

        # Process article
        article = self.processor.parse_article(mock_item, 1)

        # Assert results
        self.assertEqual(article['title'], 'Test Title')
        self.assertEqual(article['url'], 'Test URL')
        self.assertEqual(article['description'], 'Test Description')

    def test_clean_ltree(self):
        # Test basic cleaning
        self.assertEqual(self.processor.clean_ltree('Test Category'), 'test_category')
        # Test special characters
        self.assertEqual(self.processor.clean_ltree('Test & Category!'), 'test_category')
        # Test consecutive underscores
        self.assertEqual(self.processor.clean_ltree('__Test__ Category__'), 'test_category')
        # Test empty string
        self.assertEqual(self.processor.clean_ltree(''), 'root')

if __name__ == '__main__':
    unittest.main()
