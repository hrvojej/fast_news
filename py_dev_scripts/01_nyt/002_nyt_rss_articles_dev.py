import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values

def recreate_tables():
    # Database configuration
    db_config = {
        'dbname': 'news_aggregator',
        'user': 'news_admin',
        'password': 'fasldkflk423mkj4k24jk242',
        'host': 'localhost',
        'port': '5432',
    }

    connection = None
    cursor = None

    try:
        print("Step 1: Connecting to PostgreSQL...")
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        print("Step 2: Dropping and recreating tables...")

        # Drop and recreate tables
        cursor.execute("""
        DROP TABLE IF EXISTS nyt.media;
        DROP TABLE IF EXISTS nyt.keywords;
        DROP TABLE IF EXISTS nyt.articles;

        CREATE TABLE nyt.articles (
            article_id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            guid TEXT UNIQUE,
            description TEXT,
            author TEXT[],
            pub_date TIMESTAMPTZ,
            category_id INT NOT NULL REFERENCES nyt.categories(category_id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE nyt.keywords (
            keyword_id SERIAL PRIMARY KEY,
            article_id INT NOT NULL REFERENCES nyt.articles(article_id) ON DELETE CASCADE,
            domain TEXT NOT NULL,
            keyword TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (article_id, domain, keyword)
        );

        CREATE TABLE nyt.media (
            media_id SERIAL PRIMARY KEY,
            article_id INT NOT NULL REFERENCES nyt.articles(article_id) ON DELETE CASCADE,
            url TEXT NOT NULL,
            medium TEXT,
            width INT,
            height INT,
            credit TEXT,
            description TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)
        connection.commit()
        print("Tables recreated successfully.")

    except psycopg2.Error as e:
        print(f"Database error: {e}")

    finally:
        # Close the database connection
        if cursor:
            cursor.close()
            print("Database cursor closed.")
        if connection:
            connection.close()
            print("Database connection closed.")

def fetch_and_store_articles_and_keywords():
    # Database configuration
    db_config = {
        'dbname': 'news_aggregator',
        'user': 'news_admin',
        'password': 'fasldkflk423mkj4k24jk242',
        'host': 'localhost',
        'port': '5432',
    }

    connection = None
    cursor = None

    try:
        print("Step 1: Connecting to PostgreSQL...")
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        # Fetch categories with atom_link
        cursor.execute("SELECT category_id, atom_link FROM nyt.categories WHERE atom_link IS NOT NULL;")
        categories = cursor.fetchall()
        print(f"Found {len(categories)} categories with atom_link.")

        articles = []
        keywords = []
        media_entries = []

        for category_id, atom_link in categories:
            print(f"Fetching RSS feed: {atom_link}")
            response = requests.get(atom_link)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'xml')

            for item in soup.find_all('item'):
                # Extract core article fields
                title = item.find('title').text if item.find('title') else None
                link = item.find('link').text if item.find('link') else None
                guid = item.find('guid').text if item.find('guid') else None
                description = item.find('description').text if item.find('description') else None
                author = [creator.text for creator in item.find_all('dc:creator')] if item.find('dc:creator') else []
                pub_date = item.find('pubDate').text if item.find('pubDate') else None

                # Append article data
                articles.append((
                    title, link, guid, description, author, pub_date, category_id, 'now()', 'now()'
                ))

        print(f"Parsed {len(articles)} articles.")

        # Insert articles into the database
        insert_articles_query = """
        INSERT INTO nyt.articles (
            title, url, guid, description, author, pub_date, category_id, created_at, updated_at
        )
        VALUES %s
        ON CONFLICT (guid) DO NOTHING;
        """
        execute_values(cursor, insert_articles_query, articles)
        connection.commit()

        # Fetch article IDs for inserted articles
        cursor.execute("SELECT article_id, guid FROM nyt.articles;")
        article_map = {row[1]: row[0] for row in cursor.fetchall()}

        # Prepare keywords and media with correct article_id
        for item in soup.find_all('item'):
            guid = item.find('guid').text if item.find('guid') else None
            article_id = article_map.get(guid)

            # Extract keywords
            for category in item.find_all('category'):
                domain = category.get('domain', 'unknown')
                keyword = category.text.strip()
                keywords.append((article_id, domain, keyword, 'now()', 'now()'))

            # Extract media content
            for media in item.find_all('media:content'):
                url = media.get('url')
                medium = media.get('medium')
                width = media.get('width')
                height = media.get('height')
                credit = item.find('media:credit').text if item.find('media:credit') else None
                description = item.find('media:description').text if item.find('media:description') else None
                media_entries.append((article_id, url, medium, width, height, credit, description, 'now()', 'now()'))

        print(f"Parsed {len(keywords)} keywords and {len(media_entries)} media entries.")

        # Insert keywords into the database
        insert_keywords_query = """
        INSERT INTO nyt.keywords (
            article_id, domain, keyword, created_at, updated_at
        )
        VALUES %s
        ON CONFLICT DO NOTHING;
        """
        execute_values(cursor, insert_keywords_query, keywords)

        # Insert media into the database
        insert_media_query = """
        INSERT INTO nyt.media (
            article_id, url, medium, width, height, credit, description, created_at, updated_at
        )
        VALUES %s
        ON CONFLICT DO NOTHING;
        """
        execute_values(cursor, insert_media_query, media_entries)

        connection.commit()
        print("Articles, keywords, and media entries inserted successfully.")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching RSS feed: {e}")

    except psycopg2.Error as e:
        print(f"Database error: {e}")

    finally:
        # Close the database connection
        if cursor:
            cursor.close()
            print("Database cursor closed.")
        if connection:
            connection.close()
            print("Database connection closed.")



if __name__ == "__main__":
    recreate_tables()
    fetch_and_store_articles_and_keywords()
