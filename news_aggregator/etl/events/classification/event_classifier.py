from typing import List, Dict, Any
from collections import defaultdict
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from etl.common.database.database_manager import db_manager
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class EventClassifier:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.class_threshold = 0.7
        self.topic_classes = {
            'politics': ['election', 'government', 'policy', 'democracy', 'parliament'],
            'business': ['economy', 'market', 'finance', 'trade', 'industry'],
            'technology': ['innovation', 'digital', 'software', 'internet', 'tech'],
            'science': ['research', 'discovery', 'space', 'climate', 'biology'],
            'health': ['medical', 'healthcare', 'disease', 'treatment', 'medicine'],
            'sports': ['athletics', 'tournament', 'championship', 'game', 'match'],
            'entertainment': ['film', 'music', 'celebrity', 'art', 'culture'],
            'environment': ['climate', 'sustainability', 'pollution', 'conservation', 'energy']
        }

    def classify_event(self, event_id: int):
        """Classify event into predefined topic classes."""
        try:
            event_data = self._get_event_data(event_id)
            if not event_data:
                return

            classifications = self._classify_topics(event_data)
            if classifications:
                self._save_classifications(event_id, classifications)

        except Exception as e:
            logger.error(f"Error classifying event {event_id}: {e}")

    def _get_event_data(self, event_id: int) -> Dict[str, Any]:
        """Get event data including articles."""
        query = """
        SELECT 
            e.*,
            array_agg(a.title) as article_titles,
            array_agg(a.description) as article_descriptions
        FROM events.events e
        JOIN events.event_articles ea ON e.event_id = ea.event_id
        JOIN (
            SELECT article_id, title, description FROM nyt.articles 
            UNION ALL
            SELECT article_id, title, description FROM bbc.articles
            UNION ALL
            SELECT article_id, title, description FROM cnn.articles
            UNION ALL
            SELECT article_id, title, description FROM guardian.articles
        ) a ON ea.article_id = a.article_id
        WHERE e.event_id = %(event_id)s
        GROUP BY e.event_id;
        """
        
        result = db_manager.execute_query(query, {'event_id': event_id})
        return result[0] if result else None

    def _classify_topics(self, event_data: Dict[str, Any]) -> List[Dict[str, float]]:
        """Classify event into topic classes based on content."""
        # Combine all text content
        content = ' '.join([
            event_data['title'] or '',
            event_data['description'] or '',
            *[title for title in event_data['article_titles'] if title],
            *[desc for desc in event_data['article_descriptions'] if desc]
        ]).lower()

        # Create content embedding
        content_embedding = self.model.encode([content])[0]

        # Calculate similarities with each topic class
        classifications = []
        for topic, keywords in self.topic_classes.items():
            # Create embeddings for topic keywords
            keyword_embeddings = self.model.encode(keywords)
            
            # Calculate similarity with each keyword
            similarities = cosine_similarity([content_embedding], keyword_embeddings)[0]
            
            # Use average similarity as confidence score
            confidence = float(similarities.mean())
            
            if confidence >= self.class_threshold:
                classifications.append({
                    'topic': topic,
                    'confidence': confidence
                })

        return sorted(classifications, key=lambda x: x['confidence'], reverse=True)

    def _save_classifications(self, event_id: int, classifications: List[Dict[str, float]]):
        """Save topic classifications to database."""
        query = """
        INSERT INTO events.event_classifications (
            event_id,
            topic_class,
            confidence_score,
            created_at
        ) VALUES %s
        ON CONFLICT (event_id, topic_class) 
        DO UPDATE SET
            confidence_score = EXCLUDED.confidence_score,
            updated_at = CURRENT_TIMESTAMP;
        """
        
        values = [(
            event_id,
            classification['topic'],
            classification['confidence'],
            datetime.now(timezone.utc)
        ) for classification in classifications]
        
        db_manager.execute_many(query, values)
