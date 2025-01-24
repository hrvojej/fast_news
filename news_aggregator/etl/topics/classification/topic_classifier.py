from typing import List, Dict, Any, Optional
from collections import Counter
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime, timezone
from etl.common.database.database_manager import db_manager
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class TopicClassifier:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.parent_threshold = 0.8
        self.child_threshold = 0.7

    def classify_topic(self, topic_id: int):
        try:
            topic_data = self._get_topic_data(topic_id)
            if not topic_data:
                return

            parent_topics = self._find_parent_topics(topic_data)
            child_topics = self._find_child_topics(topic_data)

            self._save_topic_relations(topic_id, parent_topics, child_topics)

        except Exception as e:
            logger.error(f"Error classifying topic {topic_id}: {e}")

    def _get_topic_data(self, topic_id: int) -> Optional[Dict[str, Any]]:
        query = """
        SELECT 
            t.*,
            array_agg(DISTINCT e.title) as event_titles,
            array_agg(DISTINCT e.description) as event_descriptions,
            array_agg(DISTINCT ec.category_name) as categories,
            array_agg(DISTINCT cl.topic_class) as classifications
        FROM topics.topics t
        JOIN topics.topic_events te ON t.topic_id = te.topic_id
        JOIN events.events e ON te.event_id = e.event_id
        LEFT JOIN events.event_categories ec ON e.event_id = ec.event_id
        LEFT JOIN events.event_classifications cl ON e.event_id = cl.event_id
        WHERE t.topic_id = %(topic_id)s
        GROUP BY t.topic_id;
        """
        result = db_manager.execute_query(query, {'topic_id': topic_id})
        return result[0] if result else None

    def _find_parent_topics(self, topic_data: Dict[str, Any]) -> List[Dict[str, float]]:
        query = """
        SELECT topic_id, name, description
        FROM topics.topics
        WHERE created_at < %(created_at)s
        AND topic_id != %(topic_id)s;
        """
        potential_parents = db_manager.execute_query(query, {
            'created_at': topic_data['created_at'],
            'topic_id': topic_data['topic_id']
        })

        topic_embedding = self._create_topic_embedding(topic_data)
        parent_topics = []

        for parent in potential_parents:
            parent_embedding = self._create_topic_embedding(parent)
            similarity = float(cosine_similarity([topic_embedding], [parent_embedding])[0][0])
            
            if similarity >= self.parent_threshold:
                parent_topics.append({
                    'topic_id': parent['topic_id'],
                    'confidence': similarity
                })

        return sorted(parent_topics, key=lambda x: x['confidence'], reverse=True)

    def _find_child_topics(self, topic_data: Dict[str, Any]) -> List[Dict[str, float]]:
        query = """
        SELECT topic_id, name, description
        FROM topics.topics
        WHERE created_at > %(created_at)s
        AND topic_id != %(topic_id)s;
        """
        potential_children = db_manager.execute_query(query, {
            'created_at': topic_data['created_at'],
            'topic_id': topic_data['topic_id']
        })

        topic_embedding = self._create_topic_embedding(topic_data)
        child_topics = []

        for child in potential_children:
            child_embedding = self._create_topic_embedding(child)
            similarity = float(cosine_similarity([topic_embedding], [child_embedding])[0][0])
            
            if similarity >= self.child_threshold:
                child_topics.append({
                    'topic_id': child['topic_id'],
                    'confidence': similarity
                })

        return sorted(child_topics, key=lambda x: x['confidence'], reverse=True)

    def _create_topic_embedding(self, topic_data: Dict[str, Any]) -> np.ndarray:
        text = f"{topic_data['name']} {topic_data['description'] or ''}"
        if topic_data.get('event_titles'):
            text += f" {' '.join(topic_data['event_titles'])}"
        if topic_data.get('categories'):
            text += f" {' '.join(topic_data['categories'])}"
        if topic_data.get('classifications'):
            text += f" {' '.join(topic_data['classifications'])}"
        return self.model.encode([text])[0]

    def _save_topic_relations(self, topic_id: int, parent_topics: List[Dict[str, float]], child_topics: List[Dict[str, float]]):
        # Save parent relations
        for parent in parent_topics:
            query = """
            INSERT INTO topics.topic_relations (
                parent_topic_id,
                child_topic_id,
                confidence_score,
                created_at
            ) VALUES (
                %(parent_id)s,
                %(child_id)s,
                %(confidence)s,
                CURRENT_TIMESTAMP
            ) ON CONFLICT (parent_topic_id, child_topic_id) DO UPDATE SET
                confidence_score = EXCLUDED.confidence_score,
                updated_at = CURRENT_TIMESTAMP;
            """
            db_manager.execute_query(query, {
                'parent_id': parent['topic_id'],
                'child_id': topic_id,
                'confidence': parent['confidence']
            })

        # Save child relations
        for child in child_topics:
            query = """
            INSERT INTO topics.topic_relations (
                parent_topic_id,
                child_topic_id,
                confidence_score,
                created_at
            ) VALUES (
                %(parent_id)s,
                %(child_id)s,
                %(confidence)s,
                CURRENT_TIMESTAMP
            ) ON CONFLICT (parent_topic_id, child_topic_id) DO UPDATE SET
                confidence_score = EXCLUDED.confidence_score,
                updated_at = CURRENT_TIMESTAMP;
            """
            db_manager.execute_query(query, {
                'parent_id': topic_id,
                'child_id': child['topic_id'],
                'confidence': child['confidence']
            })
