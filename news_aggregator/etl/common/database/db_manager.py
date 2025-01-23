import psycopg2
from psycopg2.extras import DictCursor
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
import yaml
import os

class DatabaseManager:
    """Manages database connections and operations for the ETL framework."""
    
    def __init__(self, env: str = 'dev'):
        self.env = env
        self.config = self._load_config()
        self._connection = None
        self.logger = logging.getLogger(__name__)

    def _load_config(self) -> Dict[str, Any]:
        """Load database configuration from YAML file."""
        config_path = os.path.join(
            os.path.dirname(__file__), 
            '../../../config/database/database_config.yaml'
        )
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config[self.env]

    @contextmanager
    def get_connection(self, autocommit: bool = False):
        """Get a database connection with context management."""
        try:
            if not self._connection or self._connection.closed:
                self._connection = psycopg2.connect(**self.config)
            
            self._connection.autocommit = autocommit
            yield self._connection
            
            if not autocommit:
                self._connection.commit()
                
        except Exception as e:
            if self._connection and not autocommit:
                self._connection.rollback()
            self.logger.error(f"Database error: {str(e)}")
            raise
        
    @contextmanager
    def get_cursor(self, cursor_factory=DictCursor):
        """Get a database cursor with context management."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
            finally:
                cursor.close()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> None:
        """Execute a query without returning results."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)

    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict]:
        """Execute a query and return one result."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()

    def fetch_all(self, query: str, params: Optional[tuple] = None) -> list:
        """Execute a query and return all results."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
