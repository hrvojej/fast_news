from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from etl.common.database.database_manager import db_manager
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class EventDetector:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.similarity_threshold = 0.75
        self.time_window_hours = 12

    def detect_events(self) -> List[Dict[str, Any]]:
        """Detect events from articles across different portals."""
        try:
            # Get recent articles within time window
            articles = self._get_recent_articles()
            if not articles:
                return []

            # Group articles by time windows
            time_groups = self._group_by_time_window(articles)
            
            # Process each time window
            events = []
            for time_group in time_groups:
                events.extend(self._process_time_window(time_group))

            return events

        except Exception as e:
            logger.error(f"Error in event detection: {str(e)}")
            raise

    def _get_recent_articles(self) -> List[Dict[str, Any]]:
        """Get articles from last 24 hours across all portals."""
        query = """
        WITH recent_articles AS (
            SELECT 
                'nyt' as portal,
                article_id,
                title,
                description,
                pub_date,
                category_id
            FROM nyt.articles 
            WHERE pub_date >= NOW() - INTERVAL '24 hours'
            UNION ALL
            SELECT 
                'bbc' as portal,
                article_id,
                title,
                description,
                pub_date,
                category_id
            FROM bbc.articles 
            WHERE pub_date >= NOW() - INTERVAL '24 hours'
            UNION ALL
            SELECT 
                'cnn' as portal,
                article_id,
                title,
                description,
                pub_date,
                category_id
            FROM cnn.articles 
            WHERE pub_date >= NOW() - INTERVAL '24 hours'
            UNION ALL
            SELECT 
                'guardian' as portal,
                article_id,
                title,
                description,
                pub_date,
                category_id
            FROM guardian.articles 
            WHERE pub_date >= NOW() - INTERVAL '24 hours'
        )
        SELECT * FROM recent_articles 
        ORDER BY pub_date DESC;
        """
        return db_manager.execute_query(query)

    def _group_by_time_window(self, articles: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group articles into overlapping time windows."""
        if not articles:
            return []

        time_groups = []
        current_group = []
        window_start = None

        for article in articles:
            pub_date = article['pub_date']
            
            if not window_start:
                window_start = pub_date
                current_group = [article]
                continue

            if (pub_date - window_start) <= timedelta(hours=self.time_window_hours):
                current_group.append(article)
            else:
                if current_group:
                    time_groups.append(current_group)
                window_start = pub_date
                current_group = [article]

        if current_group:
            time_groups.append(current_group)

        return time_groups

    def _process_time_window(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process articles within a time window to identify events."""
        events = []
        embeddings = {}
        
        # Create embeddings for all articles
        for article in articles:
            text = f"{article['title']} {article['description'] or ''}"
            embeddings[article['article_id']] = self.model.encode([text])[0]

        # Find similar article groups
        processed = set()
        for article_id, embedding in embeddings.items():
            if article_id in processed:
                continue

            similar_articles = []
            for other_id, other_embedding in embeddings.items():
                if other_id != article_id:
                    similarity = cosine_similarity([embedding], [other_embedding])[0][0]
                    if similarity >= self.similarity_threshold:
                        similar_articles.append({
                            'article_id': other_id,
                            'similarity': similarity
                        })
            
            if similar_articles:
                # Get the article details
                article = next(a for a in articles if a['article_id'] == article_id)
                event = self._create_event(article, similar_articles)
                events.append(event)
                processed.add(article_id)
                processed.update(a['article_id'] for a in similar_articles)

        return events

    def _create_event(self, primary_article: Dict[str, Any], similar_articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create an event entry with related articles."""
        return {
            'title': primary_article['title'],
            'description': primary_article['description'],
            'start_time': primary_article['pub_date'],
            'status': 'active',
            'confidence_score': np.mean([a['similarity'] for a in similar_articles]),
            'related_articles': [
                {
                    'article_id': a['article_id'],
                    'similarity_score': a['similarity']
                }
                for a in similar_articles
            ]
        }
