import psycopg2
import sys

def cleanup_database(environment='dev'):
    config = {
        'dev': {
            'dbname': 'news_aggregator_dev',
            'user': 'postgres',
            'password': '',
            'host': 'localhost',
            'port': '5432'
        },
        'prod': {
            'dbname': 'news_aggregator_prod',
            'user': 'postgres',
            'password': '',
            'host': 'localhost',
            'port': '5432'
        }
    }[environment]

    conn = psycopg2.connect(**config)
    conn.set_session(autocommit=True)
    cur = conn.cursor()

    try:
        cur.execute("""
            DROP SCHEMA public CASCADE;
            CREATE SCHEMA public;
            GRANT ALL ON SCHEMA public TO postgres;
            GRANT ALL ON SCHEMA public TO news_admin_dev, news_admin_prod;
            GRANT ALL ON SCHEMA public TO public;
        """)
        print("Reset public schema")

        cur.execute("""
            SELECT nspname 
            FROM pg_namespace 
            WHERE nspname NOT LIKE 'pg_%' 
            AND nspname != 'information_schema'
            AND nspname != 'public';
        """)
        schemas = [record[0] for record in cur.fetchall()]

        for schema in schemas:
            cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
            print(f"Dropped schema: {schema}")

        print(f"Successfully cleaned up {environment} database")

    except Exception as e:
        print(f"Error cleaning up database: {str(e)}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['dev', 'prod']:
        cleanup_database(sys.argv[1])
    else:
        print("Please specify environment: dev or prod")
        sys.exit(1)