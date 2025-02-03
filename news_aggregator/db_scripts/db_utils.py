from sqlalchemy import event, inspect
from contextlib import contextmanager
from .models import Base, NewsPortal, create_portal_category_model, create_portal_article_model
import psycopg2
import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config"

PORTAL_MODEL_REGISTRY = {}

@contextmanager
def portal_schema_session(engine):
    """Context manager for handling portal schemas"""
    with engine.connect() as connection:
        # Create schemas first
        inspector = inspect(engine)
        existing_schemas = inspector.get_schema_names()
        
        # Get all portal prefixes
        portals = connection.execute("SELECT portal_prefix FROM public.news_portals")
        
        for (prefix,) in portals:
            if prefix not in existing_schemas:
                connection.execute(f"CREATE SCHEMA {prefix}")
                
                # Generate models
                PortalCategory = create_portal_category_model(prefix)
                PortalArticle = create_portal_article_model(prefix)
                
                # Create tables
                PortalCategory.__table__.create(connection)
                PortalArticle.__table__.create(connection)
                
        yield connection


def load_db_config():
    config_path = CONFIG_PATH / "database" / "database_config.yaml"
    with open(config_path, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            return None

def get_db_connection(env='dev'):
    db_config = load_db_config()
    if not db_config:
        print("Failed to load database config.")
        return None

    try:
        db_params = db_config[env]
        conn = psycopg2.connect(
            user=db_params['user'],
            password=db_params['password'],
            host=db_params['host'],
            port=db_params['port'],
            database=db_params['name']
        )
        return conn
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        return None

def execute_query(conn, query, params=None):
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        conn.commit()
        return cursor
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Query execution error: {e}")
        return None
    finally:
        cursor.close()
