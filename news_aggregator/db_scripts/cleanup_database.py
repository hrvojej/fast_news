import psycopg2
import yaml
from pathlib import Path
from db_scripts import db_utils  # Import db_utils
from db_scripts.data_adapter import PortalDataAdapter  # Import PortalDataAdapter


CONFIG_PATH = Path(__file__).parent.parent / "config"


def cleanup_database():
    db_config = db_utils.load_db_config()
    if not db_config:
        print("Failed to load database config.")
        return

    conn = db_utils.get_db_connection('dev')  # Use 'dev' config for cleanup
    if not conn:
        print("Failed to connect to database.")
        return

    portal_adapter = PortalDataAdapter(conn)
    cur = conn.cursor()

    try:
        # Fetch all portal bucket prefixes using DataAdapter (if needed, though direct SQL is fine here for cleanup)
        cur.execute("SELECT bucket_prefix FROM public.news_portals")
        portal_prefixes = cur.fetchall()


        # Drop schemas for each news portal
        for prefix in portal_prefixes:
            schema_name = prefix[0]
            print(f"Dropping schema {schema_name}...")
            cur.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")

        # Drop events, topics, and entities schemas
        schemas_to_drop = ['events', 'topics', 'entities']
        for schema_name in schemas_to_drop:
            print(f"Dropping schema {schema_name}...")
            cur.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")

        # Drop public schema, but exclude news_portals table
        print("Dropping public schema (excluding news_portals table)...")
        cur.execute("""
            DO $$ DECLARE obj_name TEXT;
            BEGIN
                FOR obj_name IN (SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name <> 'news_portals') LOOP
                    EXECUTE FORMAT('DROP TABLE IF EXISTS public.%I CASCADE', obj_name);
                    RAISE NOTICE 'Dropped table: %', obj_name;
                END LOOP;
                FOR obj_name IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public') LOOP
                    EXECUTE FORMAT('DROP SEQUENCE IF EXISTS public.%I CASCADE', obj_name);
                    RAISE NOTICE 'Dropped sequence: %', obj_name;
                END LOOP;
                FOR obj_name IN (SELECT view_name FROM information_schema.views WHERE table_schema = 'public') LOOP
                    EXECUTE FORMAT('DROP VIEW IF EXISTS public.%I CASCADE', obj_name);
                    RAISE NOTICE 'Dropped view: %', obj_name;
                END LOOP;
            END $$;
        """)


        conn.commit()
        print("Database cleanup completed successfully.")

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    cleanup_database()
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

def cleanup_database():
    db_config = load_db_config()
    if not db_config:
        print("Failed to load database config.")
        return

    conn = None
    try:
        conn = psycopg2.connect(**db_config['dev'])  # Use 'dev' config for cleanup
        cur = conn.cursor()

        # Fetch all portal bucket prefixes
        cur.execute("SELECT bucket_prefix FROM public.news_portals")
        portal_prefixes = cur.fetchall()

        # Drop schemas for each news portal
        for prefix in portal_prefixes:
            schema_name = prefix[0]
            print(f"Dropping schema {schema_name}...")
            cur.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")

        # Drop events, topics, and entities schemas
        schemas_to_drop = ['events', 'topics', 'entities']
        for schema_name in schemas_to_drop:
            print(f"Dropping schema {schema_name}...")
            cur.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")

        # Drop public schema, but exclude news_portals table
        print("Dropping public schema (excluding news_portals table)...")
        cur.execute("""
            DO $$ DECLARE obj_name TEXT;
            BEGIN
                FOR obj_name IN (SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name <> 'news_portals') LOOP
                    EXECUTE FORMAT('DROP TABLE IF EXISTS public.%I CASCADE', obj_name);
                    RAISE NOTICE 'Dropped table: %', obj_name;
                END LOOP;
                FOR obj_name IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public') LOOP
                    EXECUTE FORMAT('DROP SEQUENCE IF EXISTS public.%I CASCADE', obj_name);
                    RAISE NOTICE 'Dropped sequence: %', obj_name;
                END LOOP;
                FOR obj_name IN (SELECT view_name FROM information_schema.views WHERE table_schema = 'public') LOOP
                    EXECUTE FORMAT('DROP VIEW IF EXISTS public.%I CASCADE', obj_name);
                    RAISE NOTICE 'Dropped view: %', obj_name;
                END LOOP;
            END $$;
        """)


        conn.commit()
        print("Database cleanup completed successfully.")

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    cleanup_database()
