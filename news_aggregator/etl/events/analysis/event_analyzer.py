from typing import Dict, Any, List, Optional
import numpy as np
from collections import Counter
from etl.common.database.database_manager import db_manager
from etl.portals.nyt.nyt_keyword_extractor import NYTKeywordExtractor
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class EventAnalyzer:
    def __init__(self):
        self.keyword_extractor = NYTKeywordExtractor()

    def analyze_event(self, event_id: int) -> Dict[str, Any]:
        """Analyze event articles to extract key insights."""
        try:
            articles = self._get_event_articles(event_id)
            if not articles:
                return {}

            analysis = {
                'event_id': event_id,
                'total_articles': len(articles),
                'portal_coverage': self._analyze_portal_coverage(articles),
                'common_keywords': self._extract_common_keywords(articles),
                'sentiment_summary': self._analyze_sentiment(articles),
                'timeline': self._create_timeline(articles),
                'key_quotes': self._extract_key_quotes(articles)
            }

            self._save_analysis(analysis)
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing event {event_id}: {e}")
            return {}

    def _get_event_articles(self, event_id: int) -> List[Dict[str, Any]]:
        """Get all articles related to an event."""
        query = """
        WITH event_article_ids AS (
            SELECT ea.article_id, ea.portal_id
            FROM events.event_articles ea
            WHERE ea.event_id = %(event_id)s
        )
        SELECT 
            a.*, p.portal_name
        FROM event_article_ids ea
        LEFT JOIN (
            SELECT 'nyt' as source, * FROM nyt.articles
            UNION ALL
            SELECT 'bbc' as source, * FROM bbc.articles
            UNION ALL
            SELECT 'cnn' as source, * FROM cnn.articles
            UNION ALL
            SELECT 'guardian' as source, * FROM guardian.articles
        ) a ON ea.article_id = a.article_id
        LEFT JOIN public.news_portals p ON ea.portal_id = p.portal_id
        ORDER BY a.pub_date ASC;
        """
        return db_manager.execute_query(query, {'event_id': event_id})

    def _analyze_portal_coverage(self, articles: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze how different portals cover the event."""
        portal_counts = Counter(article['portal_name'] for article in articles)
        return dict(portal_counts)

    def _extract_common_keywords(self, articles: List[Dict[str, Any]]) -> List[str]:
        """Extract common keywords across articles."""
        all_keywords = []
        for article in articles:
            text = f"{article['title']} {article['description']}"
            keywords = self.keyword_extractor.extract_keywords(text)
            all_keywords.extend(keywords)

        keyword_counts = Counter(all_keywords)
        return [kw for kw, count in keyword_counts.most_common(10)]

    def _analyze_sentiment(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment patterns across articles."""
        # Basic sentiment analysis using keyword matching
        positive_words = {'success', 'breakthrough', 'agreement', 'victory', 'progress'}
        negative_words = {'crisis', 'conflict', 'failure', 'disaster', 'threat'}

        sentiments = []
        for article in articles:
            text = f"{article['title']} {article['description']}".lower()
            pos_count = sum(1 for word in positive_words if word in text)
            neg_count = sum(1 for word in negative_words if word in text)
            
            if pos_count > neg_count:
                sentiments.append('positive')
            elif neg_count > pos_count:
                sentiments.append('negative')
            else:
                sentiments.append('neutral')

        sentiment_counts = Counter(sentiments)
        return dict(sentiment_counts)

    def _create_timeline(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create event timeline from articles."""
        timeline = []
        for article in articles:
            timeline_entry = {
                'timestamp': article['pub_date'],
                'portal': article['portal_name'],
                'title': article['title'],
                'url': article['url']
            }
            timeline.append(timeline_entry)

        return sorted(timeline, key=lambda x: x['timestamp'])

    def _extract_key_quotes(self, articles: List[Dict[str, Any]]) -> List[str]:
        """Extract key quotes from articles."""
        quotes = []
        for article in articles:
            description = article.get('description', '')
            if not description:
                continue

            # Simple quote extraction - look for text between quotes
            quote_start = description.find('"')
            quote_end = description.find('"', quote_start + 1)
            
            if quote_start >= 0 and quote_end > quote_start:
                quote = description[quote_start + 1:quote_end].strip()
                if len(quote) > 10:  # Minimum quote length
                    quotes.append(quote)

        return quotes[:5]  # Return top 5 quotes

    def _save_analysis(self, analysis: Dict[str, Any]):
        """Save analysis results to database."""
        query = """
        INSERT INTO events.event_analysis (
            event_id,
            total_articles,
            portal_coverage,
            common_keywords,
            sentiment_summary,
            timeline,
            key_quotes,
            created_at
        ) VALUES (
            %(event_id)s,
            %(total_articles)s,
            %(portal_coverage)s,
            %(common_keywords)s,
            %(sentiment_summary)s,
            %(timeline)s,
            %(key_quotes)s,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (event_id) 
        DO UPDATE SET
            total_articles = EXCLUDED.total_articles,
            portal_coverage = EXCLUDED.portal_coverage,
            common_keywords = EXCLUDED.common_keywords,
            sentiment_summary = EXCLUDED.sentiment_summary,
            timeline = EXCLUDED.timeline,
            key_quotes = EXCLUDED.key_quotes,
            updated_at = CURRENT_TIMESTAMP;
        """
        
        db_manager.execute_query(query, analysis)
