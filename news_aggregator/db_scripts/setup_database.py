import psycopg2
import sys

def setup_database(environment='dev'):
    config = {
        'dev': {
            'dbname': 'news_aggregator_dev',
            'user': 'postgres',
            'host': '/var/run/postgresql'  # Use Unix socket
        },
        'prod': {
            'dbname': 'news_aggregator_prod',
            'user': 'postgres',
            'host': '/var/run/postgresql'  # Use Unix socket
        }
    }[environment]

    conn = psycopg2.connect(**config)
    conn.set_session(autocommit=True)
    cur = conn.cursor()

    try:
        # Create portal schema table in public schema
        cur.execute("""
        CREATE TABLE IF NOT EXISTS public.news_portals(
            portal_id SERIAL NOT NULL,
            portal_name varchar(100) NOT NULL,
            portal_domain varchar(255) NOT NULL,
            bucket_prefix varchar(50) NOT NULL,
            created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(portal_id)
        );
        """)

        # Insert portal data if table is empty
        cur.execute("SELECT COUNT(*) FROM public.news_portals")
        if cur.fetchone()[0] == 0:
            cur.execute("""
            INSERT INTO news_portals (portal_name, portal_domain, bucket_prefix) VALUES
            ('New York Times', 'nytimes.com', 'nyt'),
            ('BBC', 'bbc.com', 'bbc'),
            ('CNN', 'cnn.com', 'cnn'),
            ('The Guardian', 'theguardian.com', 'guardian'),
            ('Reuters', 'reuters.com', 'reuters'),
            ('Washington Post', 'washingtonpost.com', 'wapo'),
            ('Al Jazeera', 'aljazeera.com', 'aljazeera'),
            ('Fox News', 'foxnews.com', 'fox'),
            ('CNBC', 'cnbc.com', 'cnbc'),
            ('Bloomberg', 'bloomberg.com', 'bloomberg'),
            ('Financial Times', 'ft.com', 'ft'),
            ('Forbes', 'forbes.com', 'forbes'),
            ('Politico', 'politico.com', 'politico'),
            ('NPR', 'npr.org', 'npr'),
            ('ABC News', 'abcnews.go.com', 'abcnews'),
            ('NBC News', 'nbcnews.com', 'nbcnews'),
            ('The Hindu', 'thehindu.com', 'hindu'),
            ('Times of India', 'timesofindia.indiatimes.com', 'toi'),
            ('South China Morning Post', 'scmp.com', 'scmp'),
            ('Le Monde', 'lemonde.fr', 'lemonde');
            """)

        # Execute the complete schema creation
        with open('/home/opc/news_dagster-etl/news_aggregator/db_scripts/schemas/create_complete_schema.sql', 'r') as f:
            cur.execute(f.read())


        print(f"Successfully set up {environment} database")

    except Exception as e:
        print(f"Error setting up database: {str(e)}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['dev', 'prod']:
        setup_database(sys.argv[1])
    else:
        print("Please specify environment: dev or prod")
        sys.exit(1)