import psycopg2
from psycopg2.extras import execute_values
import requests
from bs4 import BeautifulSoup

def process_bbc_articles():
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

        print("Step 2: Fetching RSS feeds...")
        # Fetch categories with atom_link
        cursor.execute("SELECT category_id, atom_link FROM bbc.categories WHERE atom_link IS NOT NULL;")
        categories = cursor.fetchall()
        print(f"Found {len(categories)} categories with atom_link.")

        articles = []
        keywords = []
        media_entries = []

        for category_id, atom_link in categories:
            try:
                print(f"\nFetching RSS feed: {atom_link}")
                response = requests.get(atom_link, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'xml')

                items = soup.find_all('item')
                print(f"Found {len(items)} items in feed")

                for item in items:
                    try:
                        # Extract core article fields
                        title = item.find('title').text.strip() if item.find('title') else None
                        link = item.find('link').text.strip() if item.find('link') else None
                        guid = item.find('guid').text.strip() if item.find('guid') else link
                        description = item.find('description').text.strip() if item.find('description') else None

                        pub_date = item.find('pubDate').text.strip() if item.find('pubDate') else None
                        
                        articles.append((
                            title, link, guid, description, [], pub_date, category_id, 'now()', 'now()'
                        ))

                        # Extract media content
                        thumbnail = item.find('media:thumbnail')
                        if thumbnail:
                            url = thumbnail.get('url')
                            height = thumbnail.get('height')
                            width = thumbnail.get('width')

                            media_entries.append((
                                guid, url, 'image', int(width) if width else None, int(height) if height else None,
                                'BBC News', 'BBC News Image', 'now()', 'now()'
                            ))

                        # Extract keywords from channel description
                        channel = item.find_parent('channel')
                        if channel and channel.find('description'):
                            desc = channel.find('description').text.strip()
                            if desc.startswith('BBC News - '):
                                keyword = desc.split(' - ', 1)[1]
                                keywords.append((
                                    guid, 'section', keyword, 'now()', 'now()'
                                ))

                    except Exception as e:
                        print(f"Error processing item: {str(e)}")
                        continue

            except Exception as e:
                print(f"Error processing feed {atom_link}: {str(e)}")
                continue

        print(f"\nParsed {len(articles)} articles total.")
        print(f"Found {len(keywords)} keywords total.")
        print(f"Found {len(media_entries)} media entries total.")

        # Step 3: Insert articles
        print("\nStep 3: Inserting data...")

        if articles:
            guids = [article[2] for article in articles]  # GUID is at index 2

            # Fetch existing articles with GUIDs
            cursor.execute("""
                SELECT guid, article_id 
                FROM bbc.articles 
                WHERE guid = ANY(%s)
            """, (guids,))
            existing_articles = {row[0]: row[1] for row in cursor.fetchall()}

            articles_to_insert = [article for article in articles if article[2] not in existing_articles]

            print(f"Found {len(articles_to_insert)} new articles.")

            article_map = existing_articles.copy()

            if articles_to_insert:
                insert_articles_query = """
                INSERT INTO bbc.articles (
                    title, url, guid, description, author, pub_date, category_id, created_at, updated_at
                )
                VALUES %s
                ON CONFLICT (guid) DO NOTHING
                RETURNING article_id, guid;
                """
                execute_values(cursor, insert_articles_query, articles_to_insert, fetch=True)
                new_article_ids = cursor.fetchall()
                article_map.update({row[1]: row[0] for row in new_article_ids})

            # Insert keywords
            if keywords:
                processed_keywords = [
                    (article_map[k[0]], k[1], k[2], k[3], k[4])
                    for k in keywords if k[0] in article_map
                ]

                if processed_keywords:
                    print(f"Inserting {len(processed_keywords)} keywords...")
                    cursor.execute("""
                        DELETE FROM bbc.keywords 
                        WHERE article_id = ANY(%s)
                    """, ([article_map[k[0]] for k in keywords if k[0] in article_map],))

                    insert_keywords_query = """
                    INSERT INTO bbc.keywords (
                        article_id, domain, keyword, created_at, updated_at
                    )
                    VALUES %s;
                    """
                    execute_values(cursor, insert_keywords_query, processed_keywords)

            # Insert media
            if media_entries:
                processed_media = [
                    (article_map[m[0]], m[1], m[2], m[3], m[4], m[5], m[6], m[7], m[8])
                    for m in media_entries if m[0] in article_map
                ]

                if processed_media:
                    print(f"Inserting {len(processed_media)} media entries...")
                    cursor.execute("""
                        DELETE FROM bbc.media 
                        WHERE article_id = ANY(%s)
                    """, ([article_map[m[0]] for m in media_entries if m[0] in article_map],))

                    insert_media_query = """
                    INSERT INTO bbc.media (
                        article_id, url, medium, width, height, credit, description, created_at, updated_at
                    )
                    VALUES %s;
                    """
                    execute_values(cursor, insert_media_query, processed_media)

        connection.commit()
        print("All data inserted successfully.")

    except Exception as e:
        print(f"Error: {str(e)}")
        if connection:
            connection.rollback()

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == "__main__":
    process_bbc_articles()
