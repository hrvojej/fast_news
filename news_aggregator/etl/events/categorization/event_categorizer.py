from typing import List, Dict, Any
from collections import Counter
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from etl.common.database.database_manager import db_manager
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class EventCategorizer:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.similarity_threshold = 0.7

    def categorize_event(self, event_id: int):
        """Categorize event based on its articles."""
        try:
            event_data = self._get_event_data(event_id)
            if not event_data:
                return

            # Get category predictions based on articles
            predictions = self._predict_categories(event_data['articles'])
            
            if predictions:
                # Save category predictions
                self._save_predictions(event_id, predictions)

        except Exception as e:
            logger.error(f"Error categorizing event {event_id}: {e}")

    def _get_event_data(self, event_id: int) -> Dict[str, Any]:
        """Get event data and its articles."""
        query = """
        WITH event_articles AS (
            SELECT 
                a.*,
                c.name as category_name
            FROM events.event_articles ea
            JOIN (
                SELECT *, 'nyt' as source FROM nyt.articles
                UNION ALL
                SELECT *, 'bbc' as source FROM bbc.articles
                UNION ALL
                SELECT *, 'cnn' as source FROM cnn.articles
                UNION ALL
                SELECT *, 'guardian' as source FROM guardian.articles
            ) a ON ea.article_id = a.article_id
            JOIN (
                SELECT category_id, name FROM nyt.categories
                UNION ALL
                SELECT category_id, name FROM bbc.categories
                UNION ALL
                SELECT category_id, name FROM cnn.categories
                UNION ALL
                SELECT category_id, name FROM guardian.categories
            ) c ON a.category_id = c.category_id
            WHERE ea.event_id = %(event_id)s
        )
        SELECT 
            e.*,
            array_agg(DISTINCT a.category_name) as categories,
            array_agg(DISTINCT a.title) as article_titles,
            array_agg(DISTINCT a.description) as article_descriptions
        FROM events.events e
        JOIN event_articles a ON e.event_id = %(event_id)s
        WHERE e.event_id = %(event_id)s
        GROUP BY e.event_id;
        """
        
        result = db_manager.execute_query(query, {'event_id': event_id})
        return result[0] if result else None

    def _predict_categories(self, articles: List[Dict[str, Any]]) -> List[Dict[str, float]]:
        """Predict categories for event based on article categories."""
        # Get list of all possible categories
        query = """
        SELECT DISTINCT name 
        FROM (
            SELECT name FROM nyt.categories
            UNION ALL
            SELECT name FROM bbc.categories
            UNION ALL
            SELECT name FROM cnn.categories
            UNION ALL
            SELECT name FROM guardian.categories
        ) all_categories;
        """
        categories = [row['name'] for row in db_manager.execute_query(query)]

        # Create embeddings for categories
        category_embeddings = self.model.encode(categories)

        # Combine article titles and descriptions
        article_texts = []
        for article in articles:
            text = f"{article['title']} {article['description'] or ''}"
            article_texts.append(text)

        # Create embeddings for articles
        article_embeddings = self.model.encode(article_texts)

        # Calculate similarities
        similarities = cosine_similarity(article_embeddings, category_embeddings)
        
        # Average similarities across all articles
        avg_similarities = similarities.mean(axis=0)

        # Get top categories above threshold
        predictions = []
        for idx, score in enumerate(avg_similarities):
            if score >= self.similarity_threshold:
                predictions.append({
                    'category': categories[idx],
                    'confidence': float(score)
                })

        return sorted(predictions, key=lambda x: x['confidence'], reverse=True)

    def _save_predictions(self, event_id: int, predictions: List[Dict[str, float]]):
        """Save category predictions to database."""
        query = """
        INSERT INTO events.event_categories (
            event_id,
            category_name,
            confidence_score,
            created_at
        ) VALUES %s
        ON CONFLICT (event_id, category_name) 
        DO UPDATE SET
            confidence_score = EXCLUDED.confidence_score,
            updated_at = CURRENT_TIMESTAMP;
        """
        
        values = [(
            event_id,
            pred['category'],
            pred['confidence'],
            datetime.now(timezone.utc)
        ) for pred in predictions]
        
        db_manager.execute_many(query, values)
