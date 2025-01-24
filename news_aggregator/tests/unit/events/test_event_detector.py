"""
Event Detection System Tests

Run specific test:
python -m unittest tests/unit/events/test_event_detector.py -v

Run single test case:
python -m unittest tests/unit/events/test_event_detector.py TestEventDetector.test_detect_events -v

Run all event tests:
python -m unittest discover tests/unit/events -v

Environment setup required:
- Set NEWS_ENV=development
- Database must be initialized with articles
- SentenceTransformer model must be downloaded
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import numpy as np
from etl.events.detection.event_detector import EventDetector

class TestEventDetector(unittest.TestCase):
    def setUp(self):
        self.detector = EventDetector()

    def test_detect_events(self):
        with patch('etl.common.database.database_manager.db_manager.execute_query') as mock_query:
            # Mock articles data
            mock_query.return_value = [
                {
                    'portal': 'nyt',
                    'article_id': 1,
                    'title': 'Major Event Happens',
                    'description': 'Description of major event',
                    'pub_date': datetime.now(),
                    'category_id': 1
                },
                {
                    'portal': 'bbc',
                    'article_id': 2,
                    'title': 'Major Event Takes Place',
                    'description': 'Another description of same event',
                    'pub_date': datetime.now(),
                    'category_id': 2
                }
            ]

            events = self.detector.detect_events()
            self.assertIsNotNone(events)
            self.assertGreater(len(events), 0)

    def test_group_by_time_window(self):
        articles = [
            {
                'pub_date': datetime.now(),
                'title': 'Article 1'
            },
            {
                'pub_date': datetime.now() - timedelta(hours=2),
                'title': 'Article 2'
            },
            {
                'pub_date': datetime.now() - timedelta(hours=13),
                'title': 'Article 3'
            }
        ]

        groups = self.detector._group_by_time_window(articles)
        self.assertGreater(len(groups), 0)
        self.assertLessEqual(len(groups[0]), 2)  # First group should have 2 articles

    @patch('sentence_transformers.SentenceTransformer.encode')
    def test_process_time_window(self, mock_encode):
        # Mock embeddings
        mock_encode.return_value = np.array([[0.1, 0.2], [0.15, 0.25]])
        
        articles = [
            {
                'article_id': 1,
                'title': 'Event A',
                'description': 'Description A',
                'pub_date': datetime.now()
            },
            {
                'article_id': 2,
                'title': 'Event A happens',
                'description': 'Description A continues',
                'pub_date': datetime.now()
            }
        ]

        events = self.detector._process_time_window(articles)
        self.assertGreater(len(events), 0)
        self.assertIn('title', events[0])
        self.assertIn('confidence_score', events[0])

if __name__ == '__main__':
    unittest.main()
