import unittest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup
from etl.common.base.base_scraper import BaseScraper
from etl.common.base.base_html_scraper import BaseHtmlScraper
from etl.common.base.base_rss_scraper import BaseRssScraper

class TestBaseScraperMethods(unittest.TestCase):
    def setUp(self):
        self.scraper = BaseScraper(
            portal_id=1,
            portal_name="Test Portal",
            portal_domain="test.com"
        )

    def test_clean_text(self):
        text = "  Test   with\n\nextra   spaces\t\t "
        cleaned = self.scraper.clean_text(text)
        self.assertEqual(cleaned, "Test with extra spaces")

    def test_parse_date(self):
        formats = ["%Y-%m-%d", "%d/%m/%Y"]
        
        # Test valid date
        valid_date = "2024-01-24"
        parsed = self.scraper.parse_date(valid_date, formats)
        self.assertIsNotNone(parsed)
        
        # Test invalid date
        invalid_date = "invalid-date"
        parsed = self.scraper.parse_date(invalid_date, formats)
        self.assertIsNone(parsed)

    def test_validate_url(self):
        # Test relative URL
        relative = "/news/article"
        absolute = self.scraper.validate_url(relative)
        self.assertTrue(absolute.startswith("http"))
        
        # Test absolute URL
        absolute_url = "https://test.com/news"
        validated = self.scraper.validate_url(absolute_url)
        self.assertEqual(validated, absolute_url)

class TestBaseHtmlScraperMethods(unittest.TestCase):
    def setUp(self):
        self.scraper = BaseHtmlScraper(
            portal_id=1,
            portal_name="Test Portal",
            portal_domain="test.com"
        )

    @patch('etl.common.utils.request_manager.RequestManager.get')
    def test_get_page_content(self, mock_get):
        # Mock successful response
        mock_response = MagicMock()
        mock_response.content = "<html><body>Test</body></html>"
        mock_get.return_value = mock_response
        
        soup = self.scraper.get_page_content("https://test.com")
        self.assertIsInstance(soup, BeautifulSoup)
        self.assertEqual(soup.body.text, "Test")

        # Mock failed response
        mock_get.side_effect = Exception("Connection error")
        soup = self.scraper.get_page_content("https://test.com")
        self.assertIsNone(soup)

    def test_clean_html_text(self):
        html = "<p>Test  with\n\n<b>HTML</b>   tags\t\t</p>"
        cleaned = self.scraper.clean_html_text(html)
        self.assertEqual(cleaned, "Test with HTML tags")

class TestBaseRssScraperMethods(unittest.TestCase):
    def setUp(self):
        self.scraper = BaseRssScraper(
            portal_id=1,
            portal_name="Test Portal",
            portal_domain="test.com"
        )

    @patch('etl.common.utils.request_manager.RequestManager.get')
    def test_get_feed_content(self, mock_get):
        # Mock successful RSS response
        mock_response = MagicMock()
        mock_response.content = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
            </channel>
        </rss>"""
        mock_get.return_value = mock_response
        
        soup = self.scraper.get_feed_content("https://test.com/rss")
        self.assertIsInstance(soup, BeautifulSoup)
        self.assertEqual(soup.channel.title.text, "Test Feed")

        # Mock failed response
        mock_get.side_effect = Exception("Connection error")
        soup = self.scraper.get_feed_content("https://test.com/rss")
        self.assertIsNone(soup)

    def test_parse_feed_metadata(self):
        xml = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
                <link>https://test.com</link>
                <description>Test Description</description>
                <language>en</language>
            </channel>
        </rss>"""
        
        soup = BeautifulSoup(xml, 'xml')
        metadata = self.scraper.parse_feed_metadata(soup.channel)
        
        self.assertEqual(metadata['title'], "Test Feed")
        self.assertEqual(metadata['link'], "https://test.com")
        self.assertEqual(metadata['description'], "Test Description")
        self.assertEqual(metadata['language'], "en")

if __name__ == '__main__':
    unittest.main()
