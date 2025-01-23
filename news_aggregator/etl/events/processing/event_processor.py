from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from etl.common.database.database_manager import db_manager 
from etl.common.logging.logging_manager import logging_manager
from etl.events.detection.event_detector import EventDetector

logger = logging_manager.get_logger(__name__)

class EventProcessor:
    def __init__(self):
        self.event_detector = EventDetector()
        self.merge_threshold = 0.85

    def process_events(self):
        """Process detected events and manage their lifecycle."""
        try:
            # Detect new events
            new_events = self.event_detector.detect_events()
            
            # Process each new event
            for event in new_events:
                try:
                    self._process_single_event(event)
                except Exception as e:
                    logger.error(f"Error processing event: {str(e)}")
                    continue

            # Update existing events
            self._update_existing_events()

        except Exception as e:
            logger.error(f"Error in event processing: {str(e)}")
            raise

    def _process_single_event(self, event: Dict[str, Any]):
        """Process a single detected event."""
        try:
            # Check for similar existing events
            similar_event = self._find_similar_event(event)

            if similar_event:
                # Merge with existing event
                self._merge_events(similar_event['event_id'], event)
            else:
                # Create new event
                self._create_new_event(event)

        except Exception as e:
            logger.error(f"Error processing event: {str(e)}")
            raise

    def _find_similar_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find similar existing active event."""
        query = """
        SELECT 
            e.event_id,
            e.title,
            e.description,
            e.start_time,
            e.confidence_score
        FROM events.events e
        WHERE e.status = 'active'
        AND e.start_time >= NOW() - INTERVAL '24 hours'
        """
        
        existing_events = db_manager.execute_query(query)
        if not existing_events:
            return None

        # Compare title similarity using embeddings
        event_embedding = self.event_detector.model.encode([event['title']])[0]
        
        for existing in existing_events:
            existing_embedding = self.event_detector.model.encode([existing['title']])[0]
            similarity = float(self.event_detector.model.cos_sim(
                [event_embedding], 
                [existing_embedding]
            )[0][0])
            
            if similarity >= self.merge_threshold:
                return existing

        return None

    def _create_new_event(self, event: Dict[str, Any]):
        """Create a new event and its article mappings."""
        # Insert event
        insert_event_query = """
        INSERT INTO events.events (
            title, description, start_time, status, confidence_score
        ) VALUES (
            %(title)s, %(description)s, %(start_time)s, %(status)s, %(confidence_score)s
        ) RETURNING event_id;
        """
        
        result = db_manager.execute_query(insert_event_query, event)
        event_id = result[0]['event_id']

        # Insert article mappings
        self._create_article_mappings(event_id, event['related_articles'])

    def _merge_events(self, existing_event_id: int, new_event: Dict[str, Any]):
        """Merge new event information into existing event."""
        update_query = """
        UPDATE events.events
        SET 
            confidence_score = GREATEST(confidence_score, %(confidence_score)s),
            updated_at = CURRENT_TIMESTAMP
        WHERE event_id = %(event_id)s
        """
        
        db_manager.execute_query(update_query, {
            'confidence_score': new_event['confidence_score'],
            'event_id': existing_event_id
        })

        # Add new article mappings
        self._create_article_mappings(existing_event_id, new_event['related_articles'])

    def _create_article_mappings(self, event_id: int, articles: List[Dict[str, Any]]):
        """Create mappings between event and articles."""
        insert_query = """
        INSERT INTO events.event_articles (
            event_id, article_id, portal_id, similarity_score
        ) VALUES %s
        ON CONFLICT (event_id, article_id, portal_id) 
        DO UPDATE SET similarity_score = EXCLUDED.similarity_score;
        """
        
        values = [(
            event_id,
            article['article_id'],
            self._get_portal_id(article['article_id']),
            article['similarity_score']
        ) for article in articles]
        
        db_manager.execute_many(insert_query, values)

    def _update_existing_events(self):
        """Update status of existing events."""
        update_query = """
        UPDATE events.events
        SET status = 'inactive'
        WHERE status = 'active'
        AND start_time < NOW() - INTERVAL '24 hours'
        """
        
        db_manager.execute_query(update_query)

    def _get_portal_id(self, article_id: int) -> int:
        """Get portal_id for an article."""
        query = """
        SELECT portal_id 
        FROM news_portals 
        WHERE bucket_prefix = (
            SELECT 'nyt' WHERE EXISTS (SELECT 1 FROM nyt.articles WHERE article_id = %(article_id)s)
            UNION ALL
            SELECT 'bbc' WHERE EXISTS (SELECT 1 FROM bbc.articles WHERE article_id = %(article_id)s)
            UNION ALL
            SELECT 'cnn' WHERE EXISTS (SELECT 1 FROM cnn.articles WHERE article_id = %(article_id)s)
            UNION ALL
            SELECT 'guardian' WHERE EXISTS (SELECT 1 FROM guardian.articles WHERE article_id = %(article_id)s)
        )
        """
        
        result = db_manager.execute_query(query, {'article_id': article_id})
        return result[0]['portal_id'] if result else None
