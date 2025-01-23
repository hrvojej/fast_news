from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from config.environment.environment_config_manager import config_manager
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        self.db_config = config_manager.get_database_config()
        self._connection = None
        
    @contextmanager
    def get_connection(self):
        """Get a database connection using context manager."""
        try:
            if not self._connection or self._connection.closed:
                self._connection = psycopg2.connect(**self.db_config)
            yield self._connection
        except psycopg2.Error as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
        finally:
            if self._connection and not self._connection.closed:
                self._connection.close()
                self._connection = None
    
    @contextmanager
    def get_cursor(self, cursor_factory=None):
        """Get a database cursor using context manager."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except psycopg2.Error as e:
                conn.rollback()
                logger.error(f"Database operation error: {str(e)}")
                raise
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[list]:
        """Execute a query and return results."""
        with self.get_cursor(RealDictCursor) as cursor:
            cursor.execute(query, params)
            if cursor.description:
                return cursor.fetchall()
            return None
    
    def execute_many(self, query: str, params: list) -> None:
        """Execute a query with multiple parameter sets."""
        with self.get_cursor() as cursor:
            cursor.executemany(query, params)
    
    def execute_transaction(self, queries: list) -> None:
        """Execute multiple queries in a transaction."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                for query, params in queries:
                    cursor.execute(query, params)

# Singleton instance
db_manager = DatabaseManager()
