# path: /home/opc/news_dagster-etl/news_aggregator/db_scripts/db_utils.py
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import sqlalchemy as sa
from sqlalchemy import inspect
from contextlib import contextmanager
from .models import (
    create_portal_category_model,
    create_portal_article_model,
    Base
)

CONFIG_PATH = Path(__file__).parent.parent / "config"
PORTAL_MODEL_REGISTRY: Dict[str, Any] = {}

def load_db_config() -> Optional[Dict[str, Any]]:
    """
    Load database configuration from YAML file.
    
    Returns:
        Optional[Dict[str, Any]]: Database configuration dictionary or None if loading fails
    """
    config_path = CONFIG_PATH / "database" / "database_config.yaml"
    try:
        with open(config_path, 'r') as stream:
            return yaml.safe_load(stream)
    except (yaml.YAMLError, IOError) as exc:
        print(f"Error loading database config: {exc}")
        return None

def ensure_schema_exists(connection: sa.engine.Connection, schema_name: str) -> None:
    """
    Ensure that a schema exists in the database.
    
    Args:
        connection: SQLAlchemy connection object
        schema_name: Name of the schema to create
    """
    connection.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))

@contextmanager
def portal_schema_session(engine: sa.engine.Engine):
    """
    Context manager for handling portal schemas.
    
    Args:
        engine: SQLAlchemy engine object
    
    Yields:
        sa.engine.Connection: Database connection
    """
    with engine.begin() as connection:
        try:
            # Get all portal prefixes
            result = connection.execute(
                sa.text("SELECT portal_prefix FROM public.news_portals")
            )
            
            for (prefix,) in result:
                # Ensure schema exists
                ensure_schema_exists(connection, prefix)
                
                # Ensure tables exist
                ensure_portal_tables_exist(connection, engine, prefix)
            
            yield connection
            
        except Exception as e:
            print(f"Error in portal schema session: {e}")
            raise

def init_db(engine: sa.engine.Engine) -> None:
    """
    Initialize database with required schemas and tables.
    
    Args:
        engine: SQLAlchemy engine object
    """
    # Create public schema tables (Base models)
    Base.metadata.create_all(engine)
    
    # Initialize portal schemas
    with portal_schema_session(engine):
        pass  # The context manager will handle schema and table creation

# Example usage
if __name__ == '__main__':
    from news_aggregator.db_scripts.db_context import DatabaseContext
    
    try:
        # Initialize database
        db_context = DatabaseContext.get_instance('dev')
        init_db(db_context.engine)
        print("Database initialized successfully")
        
    except Exception as e:
        print(f"Database initialization failed: {e}")