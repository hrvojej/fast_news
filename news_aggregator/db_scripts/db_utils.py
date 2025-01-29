import psycopg2
import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config"

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
