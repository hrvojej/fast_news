#!/usr/bin/env python3
import unittest
from unittest.mock import patch, MagicMock
from news_aggregator.portals.nyt.rss_categories_parser import NYTRSSCategoriesParser
from news_aggregator.db_scripts.db_context import DatabaseContext
from sqlalchemy import text


class TestNYTRSSParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sqlalchemy import text
        cls.db_context = DatabaseContext.get_instance('dev')
        
        with cls.db_context.session() as session:
            portal_data = session.execute(
                text("SELECT portal_id FROM public.news_portals WHERE portal_prefix = 'pt_nyt'")
            ).first()
            cls.portal_id = portal_data[0]

    def setUp(self):
        print("\n--- Starting new test ---")
        self.parser = NYTRSSCategoriesParser(
            portal_id=self.portal_id,
            env='dev'
        )

    def test_clean_ltree(self):
        print("\nTesting ltree path cleaning")
        test_cases = [
            ('World > Asia', 'world.asia'),
            ('Business Day >> Technology', 'business_day.technology'),
            ('Science & Health', 'science_health'),
            ('', 'unknown'),
            ('Sports/Baseball', 'sports.baseball'),
            ('U.S. News', 'u_s_news')
        ]
        
        for input_str, expected in test_cases:
            with self.subTest(input_str=input_str):
                result = self.parser.clean_ltree(input_str)
                print(f"Input: '{input_str}' -> Result: '{result}' -> Expected: '{expected}'")
                self.assertEqual(result, expected)

    @patch('requests.get')
    def test_fetch_rss_feeds(self, mock_get):
        print("\nTesting RSS feed fetching")
        mock_directory_response = MagicMock()
        mock_directory_response.content = '''
        <html><body>
            <a href="https://rss.nytimes.com/services/xml/rss/nyt/World.xml">World News</a>
            <a href="https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml">Technology</a>
        </body></html>
        '''
        
        mock_world_response = MagicMock()
        mock_world_response.content = '''
        <rss version="2.0"><channel>
            <title>NYT > World News</title>
            <link>https://www.nytimes.com/section/world</link>
            <description>World news from The New York Times.</description>
        </channel></rss>
        '''
        
        mock_tech_response = MagicMock()
        mock_tech_response.content = '''
        <rss version="2.0"><channel>
            <title>NYT > Technology</title>
            <link>https://www.nytimes.com/section/technology</link>
            <description>Technology news from The New York Times.</description>
        </channel></rss>
        '''
        
        def mock_get_response(*args, **kwargs):
            url = args[0]
            print(f"Mocking request to URL: {url}")
            if url == self.parser.base_url:
                return mock_directory_response
            elif 'World.xml' in url:
                return mock_world_response
            elif 'Technology.xml' in url:
                return mock_tech_response
            raise Exception(f"Unexpected URL: {url}")
        
        mock_get.side_effect = mock_get_response
        
        feeds = self.parser.fetch_rss_feeds()
        print(f"\nFetched {len(feeds)} feeds:")
        for feed in feeds:
            print(f"Feed: {feed}")

        world_feed = next(f for f in feeds if f['title'] == 'NYT > World News')
        tech_feed = next(f for f in feeds if f['title'] == 'NYT > Technology')
        
        print("\nValidating World feed:")
        print(f"Description: {world_feed['description']}")
        print(f"Path: {world_feed['path']}")
        
        print("\nValidating Technology feed:")
        print(f"Description: {tech_feed['description']}")
        print(f"Path: {tech_feed['path']}")


    def test_store_categories(self):
        test_category = {
            'title': 'Test Category',
            'link': 'https://www.nytimes.com/section/test',
            'description': 'Test category description',
            'path': 'test_category',
            'level': 1
        }
        
        with self.db_context.session() as session:
            session.execute(
                text("""
                    INSERT INTO pt_nyt.categories 
                    (name, url, description, path, level, is_active, created_at, updated_at)
                    VALUES (:title, :link, :description, :path, :level, true, NOW(), NOW())
                """),
                test_category
            )
            session.commit()


        @classmethod
        def tearDownClass(cls):
            print("\n=== Tearing down TestNYTRSSParser ===")
            if hasattr(cls, 'db_context'):
                cls.db_context.dispose()
                print("Database context disposed")

if __name__ == '__main__':
    unittest.main(verbose=True)