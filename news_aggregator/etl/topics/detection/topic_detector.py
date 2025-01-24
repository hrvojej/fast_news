from typing import List, Dict, Any, Optional
from collections import Counter
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
import numpy as np
from etl.common.database.database_manager import db_manager
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class TopicDetector:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.min_articles = 3
        self.eps = 0.3
        self.min_samples = 2

    def detect_topics(self):
        """Detect topics from recent events."""
        try:
            recent_events = self._get_recent_events()
            if not recent_events:
                return []

            event_embeddings = self._create_event_embeddings(recent_events)
            topic_clusters = self._cluster_events(event_embeddings)
            topics = self._create_topics(recent_events, topic_clusters)

            return topics

        except Exception as e:
            logger.error(f"Error detecting topics: {e}")
            return []

    def _get_recent_events(self) -> List[Dict[str, Any]]:
        """Get events from the last 7 days."""
        query = """
        WITH recent_events AS (
            SELECT 
                e.event_id,
                e.title,
                e.description,
                e.start_time,
                e.confidence_score,
                array_agg(ea.article_id) as article_ids
            FROM events.events e
            JOIN events.event_articles ea ON e.event_id = ea.event_id
            WHERE e.start_time >= NOW() - INTERVAL '7 days'
            GROUP BY e.event_id
            HAVING COUNT(ea.article_id) >= %(min_articles)s
        )
        SELECT e.*, 
               array_agg(DISTINCT c.category_name) as categories,
               array_agg(DISTINCT cl.topic_class) as topic_classes
        FROM recent_events e
        LEFT JOIN events.event_categories c ON e.event_id = c.event_id
        LEFT JOIN events.event_classifications cl ON e.event_id = cl.event_id
        GROUP BY e.event_id, e.title, e.description, e.start_time, 
                 e.confidence_score, e.article_ids;
        """
        return db_manager.execute_query(query, {'min_articles': self.min_articles})

    def _create_event_embeddings(self, events: List[Dict[str, Any]]) -> np.ndarray:
        """Create embeddings for events."""
        texts = []
        for event in events:
            text = f"{event['title']} {event['description'] or ''}"
            if event['categories']:
                text += f" {' '.join(event['categories'])}"
            if event['topic_classes']:
                text += f" {' '.join(event['topic_classes'])}"
            texts.append(text)

        return self.model.encode(texts)

    def _cluster_events(self, embeddings: np.ndarray) -> np.ndarray:
        """Cluster events using DBSCAN."""
        clustering = DBSCAN(eps=self.eps, min_samples=self.min_samples)
        return clustering.fit_predict(embeddings)

    def _create_topics(self, events: List[Dict[str, Any]], clusters: np.ndarray) -> List[Dict[str, Any]]:
        """Create topics from event clusters."""
        topics = []
        unique_clusters = np.unique(clusters)
        
        for cluster_id in unique_clusters:
            if cluster_id == -1:  # Skip noise points
                continue

            # Get events in cluster
            cluster_mask = clusters == cluster_id
            cluster_events = [e for i, e in enumerate(events) if cluster_mask[i]]

            # Extract common categories and classifications
            all_categories = []
            all_classes = []
            for event in cluster_events:
                all_categories.extend(event['categories'] or [])
                all_classes.extend(event['topic_classes'] or [])

            # Create topic
            topic = {
                'name': self._generate_topic_name(cluster_events),
                'description': self._generate_topic_description(cluster_events),
                'categories': [cat for cat, _ in Counter(all_categories).most_common(3)],
                'topic_classes': [cls for cls, _ in Counter(all_classes).most_common(3)],
                'event_ids': [event['event_id'] for event in cluster_events],
                'confidence_score': float(np.mean([e['confidence_score'] for e in cluster_events]))
            }
            topics.append(topic)

        return topics

    def _generate_topic_name(self, events: List[Dict[str, Any]]) -> str:
        """Generate a name for the topic from its events."""
        # Use the title of the most confident event
        most_confident = max(events, key=lambda x: x['confidence_score'])
        return most_confident['title']

    def _generate_topic_description(self, events: List[Dict[str, Any]]) -> str:
        """Generate a description for the topic."""
        return f"Topic covering {len(events)} related events from the past week."

    def save_topics(self, topics: List[Dict[str, Any]]):
        """Save detected topics to database."""
        for topic in topics:
            # Insert/update topic
            query = """
            INSERT INTO topics.topics (
                name, 
                description,
                confidence_score,
                created_at
            ) VALUES (
                %(name)s,
                %(description)s,
                %(confidence_score)s,
                CURRENT_TIMESTAMP
            ) RETURNING topic_id;
            """
            result = db_manager.execute_query(query, topic)
            topic_id = result[0]['topic_id']

            # Create event mappings
            self._create_event_mappings(topic_id, topic['event_ids'], topic['confidence_score'])
