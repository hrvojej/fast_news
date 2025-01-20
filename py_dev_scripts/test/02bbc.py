import psycopg2
from psycopg2.extras import execute_values
import requests
from bs4 import BeautifulSoup
import yake

def extract_keywords_with_yake(title):
    """Extract top keywords or phrases using YAKE!"""
    if not title:
        return []

    kw_extractor = yake.KeywordExtractor(
        lan="en", n=3, dedupLim=0.9, top=10, features=None
    )
    keywords = [kw[0] for kw in kw_extractor.extract_keywords(title)]
    return keywords[:5]

def parse_article(item, category_id):
    """Extract data for articles, keywords, and media from an RSS item."""
    title = item.find('title').text.strip()
    description = item.find('description').text.strip()
    link = item.find('link').text.strip()
    guid = item.find('guid').text.strip()
    pub_date = item.find('pubDate').text.strip()

    thumbnail = item.find('media:thumbnail')
    media_entry = None
    if thumbnail:
        media_entry = {
            'url': thumbnail.get('url'),
            'width': thumbnail.get('width'),
            'height': thumbnail.get('height'),
            'credit': 'BBC News',
            'description': 'BBC News Image'
        }

    return {
        'article': {
            'title': title,
            'url': link,
            'guid': guid,
            'description': description,
            'pub_date': pub_date,
            'category_id': category_id
        },
        'media': media_entry,
        'keywords': extract_keywords_with_yake(title)
    }

def batch_insert_articles(cursor, articles):
    insert_query = """
    INSERT INTO bbc.articles (title, url, guid, description, pub_date, category_id)
    VALUES %s
    ON CONFLICT (guid) DO NOTHING
    RETURNING article_id, guid;
    """
    article_data = [(a['title'], a['url'], a['guid'], a['description'], a['pub_date'], a['category_id'])
                    for a in articles]
    return execute_values(cursor, insert_query, article_data, fetch=True)

def batch_insert_keywords(cursor, keywords):
    insert_query = """
    INSERT INTO bbc.keywords (article_id, domain, keyword)
    VALUES %s
    ON CONFLICT DO NOTHING;
    """
    execute_values(cursor, insert_query, keywords)

def batch_insert_media(cursor, media_entries):
    insert_query = """
    INSERT INTO bbc.media (article_id, url, medium, width, height, credit, description)
    VALUES %s
    ON CONFLICT DO NOTHING;
    """
    execute_values(cursor, insert_query, media_entries)

def process_bbc_rss():
    db_config = {
        'dbname': 'news_aggregator',
        'user': 'news_admin',
        'password': 'your_password',
        'host': 'localhost',
        'port': '5432',
    }

    connection = None
    cursor = None

    try:
        print("Connecting to PostgreSQL...")
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        print("Fetching categories...")
        cursor.execute("SELECT category_id, atom_link FROM bbc.categories WHERE atom_link IS NOT NULL;")
        categories = cursor.fetchall()

        for category_id, atom_link in categories:
            print(f"Processing feed: {atom_link}")
            response = requests.get(atom_link, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'xml')

            articles = []
            keywords = []
            media_entries = []

            for item in soup.find_all('item'):
                parsed = parse_article(item, category_id)
                articles.append(parsed['article'])

                # Prepare keywords and media with placeholders for article_id
                for kw in parsed['keywords']:
                    keywords.append((None, 'title', kw))

                if parsed['media']:
                    media_entries.append((None, parsed['media']['url'], 'image', parsed['media']['width'],
                                          parsed['media']['height'], parsed['media']['credit'], parsed['media']['description']))

            # Insert articles and get article_id
            article_id_map = batch_insert_articles(cursor, articles)
            connection.commit()

            # Update keywords and media with correct article_id
            for article_id, guid in article_id_map:
                for kw in keywords:
                    if kw[0] is None and kw[2] in guid:
                        kw = (article_id, kw[1], kw[2])
                for media in media_entries:
                    if media[0] is None and media[1] in guid:
                        media = (article_id, media[1], media[2], media[3], media[4], media[5], media[6])

            # Batch insert keywords and media
            batch_insert_keywords(cursor, keywords)
            batch_insert_media(cursor, media_entries)
            connection.commit()

    except Exception as e:
        print(f"Error: {e}")
        if connection:
            connection.rollback()

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == "__main__":
    process_bbc_rss()
