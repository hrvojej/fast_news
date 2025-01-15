import psycopg2
from psycopg2.extras import execute_values
import requests
from bs4 import BeautifulSoup
import yake

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

    def is_valid_title(title):
        """Provjeri je li naslov validan (nije datum)."""
        if not title:
            return False
        invalid_phrases = ["January", "February", "March", "April", "May", "June", 
                            "July", "August", "September", "October", "November", "December"]
        return not any(phrase in title for phrase in invalid_phrases)

    def filter_keywords(keywords):
        """Filtriraj ključne riječi uklanjanjem pojedinačnih riječi koje se nalaze unutar fraza."""
        keywords = sorted(keywords, key=len, reverse=True)  # Sortiraj prema duljini (najduže prvo)
        filtered = []
        for word in keywords:
            if not any(word in longer for longer in filtered if word != longer):
                filtered.append(word)
        return filtered[:5]  # Limitiraj na prvih 5 riječi ili fraza

    def extract_keywords_with_yake(title):
        """Extract top keywords or phrases using YAKE! and filter redundancies."""
        if not title:
            return []

        language = "en"
        max_ngram_size = 3  # Povećaj na 3 za fraze do tri riječi
        deduplication_threshold = 0.9
        numOfKeywords = 10  # Generiraj više ključnih riječi prije filtriranja

        kw_extractor = yake.KeywordExtractor(
            lan=language,
            n=max_ngram_size,
            dedupLim=deduplication_threshold,
            top=numOfKeywords,
            features=None,
        )

        keywords = [kw[0] for kw in kw_extractor.extract_keywords(title)]
        filtered_keywords = filter_keywords(keywords)  # Filtriraj redundanciju
        return filtered_keywords

    try:
        print("Step 1: Connecting to PostgreSQL...")
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        print("Step 2: Dropping and recreating tables...")

        # Drop and recreate tables
        cursor.execute("""
        DROP TABLE IF EXISTS bbc.media;
        DROP TABLE IF EXISTS bbc.keywords;
        DROP TABLE IF EXISTS bbc.articles;

        CREATE TABLE bbc.articles (
            article_id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            guid TEXT UNIQUE,
            description TEXT,
            author TEXT[],
            pub_date TIMESTAMPTZ,
            category_id INT NOT NULL REFERENCES bbc.categories(category_id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE bbc.keywords (
            keyword_id SERIAL PRIMARY KEY,
            article_id INT NOT NULL REFERENCES bbc.articles(article_id) ON DELETE CASCADE,
            domain TEXT NOT NULL,
            keyword TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (article_id, domain, keyword)
        );

        CREATE TABLE bbc.media (
            media_id SERIAL PRIMARY KEY,
            article_id INT NOT NULL REFERENCES bbc.articles(article_id) ON DELETE CASCADE,
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

        print("Step 3: Fetching RSS feeds...")
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
                        if not is_valid_title(title):
                            print(f"Skipping invalid title: {title}")
                            continue

                        link = item.find('link').text.strip() if item.find('link') else None
                        guid = item.find('guid').text.strip() if item.find('guid') else link
                        description = item.find('description').text.strip() if item.find('description') else None

                        pub_date = item.find('pubDate').text.strip() if item.find('pubDate') else None
                        
                        articles.append((
                            title, link, guid, description, [], pub_date, category_id, 'now()', 'now()'
                        ))

                        # Extract keywords using YAKE!
                        extracted_keywords = extract_keywords_with_yake(title)
                        print(f"Keywords for '{title}': {extracted_keywords}")
                        for keyword in extracted_keywords:
                            keywords.append((guid, "title", keyword, 'now()', 'now()'))

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
                            print(f"Media for '{title}': {url}")

                    except Exception as e:
                        print(f"Error processing item: {str(e)}")
                        continue

            except Exception as e:
                print(f"Error processing feed {atom_link}: {str(e)}")
                continue

        print(f"\nParsed {len(articles)} articles total.")
        print(f"Found {len(keywords)} keywords total.")
        print(f"Found {len(media_entries)} media entries total.")

        # Step 4: Insert articles
        print("\nStep 4: Inserting data...")

        if articles:
            guids = [article[2] for article in articles]  # GUID is at index 2

            # Fetch existing articles with GUIDs
            cursor.execute("""
                SELECT guid, article_id 
                FROM bbc.articles 
                WHERE guid = ANY(%s)
            """, (guids,))
            existing_articles = {row[0]: row[1] for row in cursor.fetchall()}
            print(f"Existing articles: {existing_articles}")

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
                print(f"Inserted articles: {new_article_ids}")
                article_map.update({row[1]: row[0] for row in new_article_ids})

            # Insert keywords
            if keywords:
                processed_keywords = [
                    (article_map.get(k[0]), k[1], k[2], k[3], k[4])
                    for k in keywords if k[0] in article_map
                ]

                print(f"Processed keywords: {processed_keywords}")

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
                    (article_map.get(m[0]), m[1], m[2], m[3], m[4], m[5], m[6], m[7], m[8])
                    for m in media_entries if m[0] in article_map
                ]

                print(f"Processed media: {processed_media}")

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
