import requests
from bs4 import BeautifulSoup
from psycopg2.extras import execute_values
import re
import os
import logging

from config.environment.environment_config_manager import config_manager
from etl.common.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)
db_manager = DatabaseManager(env='development') # Initialize DatabaseManager with 'development' env

def fetch_and_store_nyt_categories():
    url = "https://www.nytimes.com/rss"
    portal_id = 1 # Assuming NYT portal_id is 1, needs to be configurable

    connection = None
    cursor = None

    try:
        print("Step 1: Connecting to PostgreSQL and recreating categories table...")
        # Use DatabaseManager to get connection
        with db_manager.get_connection() as connection:
            cursor = connection.cursor()

            # Recreate categories table in schema `nyt`
            recreate_table_query = """
            DROP SCHEMA IF EXISTS nyt CASCADE;
            CREATE SCHEMA nyt;

            CREATE TABLE IF NOT EXISTS nyt.categories (
                category_id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                slug VARCHAR(255) NOT NULL,
                portal_id INT NOT NULL REFERENCES public.news_portals(portal_id) ON DELETE CASCADE,
                path LTREE NOT NULL,
                level INT NOT NULL,
                title TEXT,
                link TEXT,
                atom_link TEXT,
                description TEXT,
                language VARCHAR(50),
                copyright_text TEXT,
                last_build_date TIMESTAMPTZ,
                pub_date TIMESTAMPTZ,
                image_title TEXT,
                image_url TEXT,
                image_link TEXT,
                UNIQUE (slug, portal_id)
            );
            """
            cursor.execute(recreate_table_query)
            connection.commit()
            print("Categories table recreated successfully.")

        print("Step 2: Fetching HTML content from the NYT RSS page...")
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        print("HTML content fetched successfully.")

        # Step 3: Parse RSS feed links for categories
        print("Step 3: Parsing RSS feed links...")
        rss_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'rss' in href and href.endswith('.xml'):
                rss_links.append(href)

        unique_rss_links = list(set(rss_links))
        print(f"Found {len(unique_rss_links)} unique RSS links.")

        # Step 4: Fetch and parse each RSS feed for category metadata
        print("Step 4: Fetching and parsing each RSS feed for category metadata...")
        categories = []
        for rss_url in unique_rss_links:
            print(f"Fetching RSS feed: {rss_url}")
            rss_response = requests.get(rss_url)
            rss_response.raise_for_status()
            rss_soup = BeautifulSoup(rss_response.content, 'xml')

            channel = rss_soup.find('channel')
            if channel:
                category = parse_category_metadata(channel)
                if category:
                    categories.append(category)

        print(f"Parsed metadata for {len(categories)} categories.")

        # Step 5: Insert categories into the table
        print("Step 5: Inserting categories into the database...")
        insert_query = """
        INSERT INTO nyt.categories (
            name, slug, portal_id, path, level, title, link, atom_link, description,
            language, copyright_text, last_build_date, pub_date,
            image_title, image_url, image_link
        )
        VALUES %s
        ON CONFLICT (slug, portal_id) DO NOTHING;
        """
        values = prepare_category_values(categories, portal_id)

        execute_values(cursor, insert_query, values)
        connection.commit()
        print("Data insertion complete.")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")

    except psycopg2.Error as e:
        print(f"Database error: {e}")

    finally:
        if cursor:
            cursor.close()
            print("Database cursor closed.")
        if connection:
            connection.close()
            print("Database connection closed.")

def parse_category_metadata(channel):
    title_tag = channel.find('title')
    title = title_tag.text.strip() if title_tag else None
    link_tag = channel.find('link')
    link = link_tag.text.strip() if link_tag else None
    atom_link_tag = channel.find('atom:link')
    atom_link = atom_link_tag['href'] if atom_link_tag and 'href' in atom_link_tag.attrs else None
    description_tag = channel.find('description')
    description = description_tag.text.strip()  if description_tag else None
    language_tag = channel.find('language')
    language = language_tag.text.strip() if language_tag else None
    copyright_text_tag = channel.find('copyright')
    copyright_text = copyright_text_tag.text.strip() if copyright_text_tag else None
    last_build_date_tag = channel.find('lastBuildDate')
    last_build_date = last_build_date_tag.text.strip() if last_build_date_tag else None
    pub_date_tag = channel.find('pubDate')
    pub_date = pub_date_tag.text.strip() if pub_date_tag else None
    image = channel.find('image')
    image_title = image.find('title').text.strip() if image and image.find('title') else None
    image_url = image.find('url').text.strip() if image and image.find('url') else None
    image_link = image.find('link').text.strip() if image and image.find('link') else None

    return {
        'title': title,
        'link': link,
        'atom_link': atom_link,
        'description': description,
        'language': language,
        'copyright_text': copyright_text,
        'last_build_date': last_build_date,
        'pub_date': pub_date,
        'image_title': image_title,
        'image_url': image_url,
        'image_link': image_link
    }

def prepare_category_values(categories, portal_id):
    def clean_ltree(value):
        if not value:
            return "unknown"
        value = value.replace(">", ".").strip()
        value = re.sub(r"[^a-zA-Z0-9.]+", "_", value.lower())
        value = re.sub(r"[._]{2,}", ".", value)
        return value.strip("._")

    values = []
    for category in categories:
        slug = clean_ltree(category['title'] or 'unknown')
        path = clean_ltree(category['title'] or 'unknown')
        level = 1  # Default level
        values.append((
            category['title'], slug, portal_id, path, level, category['title'],
            category['link'], category['atom_link'], category['description'],
            category['language'], category['copyright_text'],
            category['last_build_date'], category['pub_date'],
            category['image_title'], category['image_url'], category['image_link']
        ))
    return values

if __name__ == "__main__":
    fetch_and_store_nyt_categories()
