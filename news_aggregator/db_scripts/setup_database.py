import psycopg2
import sys
from db_scripts import db_utils  # Import db_utils
from db_scripts.data_adapter import PortalDataAdapter  # Import PortalDataAdapter

def setup_database(environment='dev'):
    config = db_utils.load_db_config()
    if not config:
        print("Failed to load database config.")
        sys.exit(1)

    db_config = config[environment]
    conn = db_utils.get_db_connection(environment) # Use db_utils to get connection
    if not conn:
        print("Failed to connect to database.")
        sys.exit(1)

    conn.set_session(autocommit=True)
    cur = conn.cursor()
    portal_adapter = PortalDataAdapter(conn) # Initialize PortalDataAdapter

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

        # Insert portal data if table is empty using DataAdapter
        if portal_adapter.get_by_id(1) is None: # Check if any portal exists
            portals = [
                {'portal_name': 'New York Times', 'portal_domain': 'nytimes.com', 'bucket_prefix': 'nyt'},
                {'portal_name': 'BBC', 'portal_domain': 'bbc.com', 'bucket_prefix': 'bbc'},
                {'portal_name': 'CNN', 'portal_domain': 'cnn.com', 'bucket_prefix': 'cnn'},
                {'portal_name': 'The Guardian', 'portal_domain': 'theguardian.com', 'bucket_prefix': 'guardian'},
                {'portal_name': 'Reuters', 'portal_domain': 'reuters.com', 'bucket_prefix': 'reuters'},
                {'portal_name': 'Washington Post', 'portal_domain': 'washingtonpost.com', 'bucket_prefix': 'wapo'},
                {'portal_name': 'Al Jazeera', 'portal_domain': 'aljazeera.com', 'bucket_prefix': 'aljazeera'},
                {'portal_name': 'Fox News', 'portal_domain': 'foxnews.com', 'bucket_prefix': 'fox'},
                {'portal_name': 'CNBC', 'portal_domain': 'cnbc.com', 'bucket_prefix': 'cnbc'},
                {'portal_name': 'Bloomberg', 'portal_domain': 'bloomberg.com', 'bucket_prefix': 'bloomberg'},
                {'portal_name': 'Financial Times', 'portal_domain': 'ft.com', 'bucket_prefix': 'ft'},
                {'portal_name': 'Forbes', 'portal_domain': 'forbes.com', 'bucket_prefix': 'forbes'},
                {'portal_name': 'Politico', 'portal_domain': 'politico.com', 'bucket_prefix': 'politico'},
                {'portal_name': 'NPR', 'portal_domain': 'npr.org', 'bucket_prefix': 'npr'},
                {'portal_name': 'ABC News', 'portal_domain': 'abcnews.go.com', 'bucket_prefix': 'abcnews'},
                {'portal_name': 'NBC News', 'portal_domain': 'nbcnews.com', 'bucket_prefix': 'nbcnews'},
                {'portal_name': 'The Hindu', 'portal_domain': 'thehindu.com', 'bucket_prefix': 'hindu'},
                {'portal_name': 'Times of India', 'portal_domain': 'timesofindia.indiatimes.com', 'bucket_prefix': 'toi'},
                {'portal_name': 'South China Morning Post', 'portal_domain': 'scmp.com', 'bucket_prefix': 'scmp'},
                {'portal_name': 'Le Monde', 'portal_domain': 'lemonde.fr', 'bucket_prefix': 'lemonde'}
            ]
            for portal_data in portals:
                portal = Portal(**portal_data)
                portal_adapter.create(portal) # Use PortalDataAdapter to create portals


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
import psycopg2
import sys
from db_scripts import db_utils  # Import db_utils
from db_scripts.data_adapter import PortalDataAdapter, Portal  # Import PortalDataAdapter and Portal dataclass

def setup_database(environment='dev'):
    config = db_utils.load_db_config()
    if not config:
        print("Failed to load database config.")
        sys.exit(1)

    db_config = config[environment]
    conn = db_utils.get_db_connection(environment) # Use db_utils to get connection
    if not conn:
        print("Failed to connect to database.")
        sys.exit(1)

    conn.set_session(autocommit=True)
    cur = conn.cursor()
    portal_adapter = PortalDataAdapter(conn) # Initialize PortalDataAdapter

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

        # Insert portal data if table is empty using DataAdapter
        if portal_adapter.get_by_id(1) is None: # Check if any portal exists
            portals = [
                Portal(portal_id=None, portal_name='New York Times', portal_domain='nytimes.com', bucket_prefix='nyt'),
                Portal(portal_id=None, portal_name='BBC', portal_domain='bbc.com', bucket_prefix='bbc'),
                Portal(portal_id=None, portal_name='CNN', portal_domain='cnn.com', bucket_prefix='cnn'),
                Portal(portal_id=None, portal_name='The Guardian', portal_domain='theguardian.com', bucket_prefix='guardian'),
                Portal(portal_id=None, portal_name='Reuters', portal_domain='reuters.com', bucket_prefix='reuters'),
                Portal(portal_id=None, portal_name='Washington Post', portal_domain='washingtonpost.com', bucket_prefix='wapo'),
                Portal(portal_id=None, portal_name='Al Jazeera', portal_domain='aljazeera.com', bucket_prefix='aljazeera'),
                Portal(portal_id=None, portal_name='Fox News', portal_domain='foxnews.com', bucket_prefix='fox'),
                Portal(portal_id=None, portal_name='CNBC', portal_domain='cnbc.com', bucket_prefix='cnbc'),
                Portal(portal_id=None, portal_name='Bloomberg', portal_domain='bloomberg.com', bucket_prefix='bloomberg'),
                Portal(portal_id=None, portal_name='Financial Times', portal_domain='ft.com', bucket_prefix='ft'),
                Portal(portal_id=None, portal_name='Forbes', portal_domain='forbes.com', bucket_prefix='forbes'),
                Portal(portal_id=None, portal_name='Politico', portal_domain='politico.com', bucket_prefix='politico'),
                Portal(portal_id=None, portal_name='NPR', portal_domain='npr.org', bucket_prefix='npr'),
                Portal(portal_id=None, portal_name='ABC News', portal_domain='abcnews.go.com', bucket_prefix='abcnews'),
                Portal(portal_id=None, portal_name='NBC News', portal_domain='nbcnews.com', bucket_prefix='nbcnews'),
                Portal(portal_id=None, portal_name='The Hindu', portal_domain='thehindu.com', bucket_prefix='hindu'),
                Portal(portal_id=None, portal_name='Times of India', portal_domain='timesofindia.indiatimes.com', bucket_prefix='toi'),
                Portal(portal_id=None, portal_name='South China Morning Post', portal_domain='scmp.com', bucket_prefix='scmp'),
                Portal(portal_id=None, portal_name='Le Monde', portal_domain='lemonde.fr', bucket_prefix='lemonde')
            ]
            for portal in portals:
                portal_adapter.create(portal) # Use PortalDataAdapter to create portals


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
import psycopg2
import sys
from db_scripts import db_utils  # Import db_utils
from db_scripts.data_adapter import PortalDataAdapter  # Import PortalDataAdapter

def setup_database(environment='dev'):
    config = db_utils.load_db_config()
    if not config:
        print("Failed to load database config.")
        sys.exit(1)

    db_config = config[environment]
    conn = db_utils.get_db_connection(environment) # Use db_utils to get connection
    if not conn:
        print("Failed to connect to database.")
        sys.exit(1)

    conn.set_session(autocommit=True)
    cur = conn.cursor()
    portal_adapter = PortalDataAdapter(conn) # Initialize PortalDataAdapter

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

        # Insert portal data if table is empty using DataAdapter
        if portal_adapter.get_by_id(1) is None: # Check if any portal exists
            portals = [
                {'portal_name': 'New York Times', 'portal_domain': 'nytimes.com', 'bucket_prefix': 'nyt'},
                {'portal_name': 'BBC', 'portal_domain': 'bbc.com', 'bucket_prefix': 'bbc'},
                {'portal_name': 'CNN', 'portal_domain': 'cnn.com', 'bucket_prefix': 'cnn'},
                {'portal_name': 'The Guardian', 'portal_domain': 'theguardian.com', 'bucket_prefix': 'guardian'},
                {'portal_name': 'Reuters', 'portal_domain': 'reuters.com', 'bucket_prefix': 'reuters'},
                {'portal_name': 'Washington Post', 'portal_domain': 'washingtonpost.com', 'bucket_prefix': 'wapo'},
                {'portal_name': 'Al Jazeera', 'portal_domain': 'aljazeera.com', 'bucket_prefix': 'aljazeera'},
                {'portal_name': 'Fox News', 'portal_domain': 'foxnews.com', 'bucket_prefix': 'fox'},
                {'portal_name': 'CNBC', 'portal_domain': 'cnbc.com', 'bucket_prefix': 'cnbc'},
                {'portal_name': 'Bloomberg', 'portal_domain': 'bloomberg.com', 'bucket_prefix': 'bloomberg'},
                {'portal_name': 'Financial Times', 'portal_domain': 'ft.com', 'bucket_prefix': 'ft'},
                {'portal_name': 'Forbes', 'portal_domain': 'forbes.com', 'bucket_prefix': 'forbes'},
                {'portal_name': 'Politico', 'portal_domain': 'politico.com', 'bucket_prefix': 'politico'},
                {'portal_name': 'NPR', 'portal_domain': 'npr.org', 'bucket_prefix': 'npr'},
                {'portal_name': 'ABC News', 'portal_domain': 'abcnews.go.com', 'bucket_prefix': 'abcnews'},
                {'portal_name': 'NBC News', 'portal_domain': 'nbcnews.com', 'bucket_prefix': 'nbcnews'},
                {'portal_name': 'The Hindu', 'portal_domain': 'thehindu.com', 'bucket_prefix': 'hindu'},
                {'portal_name': 'Times of India', 'portal_domain': 'timesofindia.indiatimes.com', 'bucket_prefix': 'toi'},
                {'portal_name': 'South China Morning Post', 'portal_domain': 'scmp.com', 'bucket_prefix': 'scmp'},
                {'portal_name': 'Le Monde', 'portal_domain': 'lemonde.fr', 'bucket_prefix': 'lemonde'}
            ]
            for portal_data in portals:
                portal = Portal(**portal_data)
                portal_adapter.create(portal) # Use PortalDataAdapter to create portals


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
