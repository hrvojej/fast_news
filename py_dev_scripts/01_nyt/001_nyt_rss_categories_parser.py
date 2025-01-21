import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values
import re

def fetch_and_store_categories():
    # Database configuration
    db_config = {
        'dbname': 'news_aggregator',
        'user': 'news_admin',
        'password': 'fasldkflk423mkj4k24jk242',
        'host': 'localhost',
        'port': '5432',
    }

    # NYT categories page
    url = "https://www.nytimes.com/rss"

    connection = None
    cursor = None

    try:
        print("Step 1: Connecting to PostgreSQL and recreating categories table...")
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        # Recreate categories table in schema `nyt`
        recreate_table_query = """
        DROP SCHEMA IF EXISTS nyt CASCADE;
        CREATE SCHEMA nyt;

        CREATE TABLE nyt.categories (
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
                title = channel.find('title').text if channel.find('title') else None
                link = channel.find('link').text if channel.find('link') else None
                atom_link = channel.find('atom:link')['href'] if channel.find('atom:link') else None
                description = channel.find('description').text if channel.find('description') else None
                language = channel.find('language').text if channel.find('language') else None
                copyright_text = channel.find('copyright').text if channel.find('copyright') else None
                last_build_date = channel.find('lastBuildDate').text if channel.find('lastBuildDate') else None
                pub_date = channel.find('pubDate').text if channel.find('pubDate') else None

                # Add image data if available
                image = channel.find('image')
                image_title = image.find('title').text if image and image.find('title') else None
                image_url = image.find('url').text if image and image.find('url') else None
                image_link = image.find('link').text if image and image.find('link') else None

                categories.append({
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
                })

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

        def clean_ltree(value):
            """
            Converts a category title into a valid ltree path.
            Maintains hierarchy using '.' and replaces invalid characters.
            """
            if not value:
                return "unknown"
            value = value.replace(">", ".").strip()
            value = re.sub(r"[^a-zA-Z0-9.]+", "_", value.lower())
            value = re.sub(r"[._]{2,}", ".", value)
            return value.strip("._")

        values = []
        for category in categories:
            slug = clean_ltree(category['title'] or 'unknown')
            portal_id = 1  # Assuming '1' is the portal_id for NYT
            path = clean_ltree(category['title'] or 'unknown')
            level = 1  # Default level
            values.append((
                category['title'], slug, portal_id, path, level, category['title'],
                category['link'], category['atom_link'], category['description'],
                category['language'], category['copyright_text'],
                category['last_build_date'], category['pub_date'],
                category['image_title'], category['image_url'], category['image_link']
            ))

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

if __name__ == "__main__":
    fetch_and_store_categories()