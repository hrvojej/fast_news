import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values
import re

def clean_cdata(text):
    """Remove CDATA tags and clean the text"""
    if not text:
        return None
    # Remove CDATA sections and clean whitespace
    cleaned = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', str(text)).strip()
    return cleaned if cleaned else None

def generate_slug(url, title):
    """
    Generate a unique slug from URL and title
    Example: https://feeds.bbci.co.uk/news/world/europe/rss.xml -> news_world_europe
    """
    if not url:
        return clean_ltree(title or 'unknown')
        
    # Extract path from URL
    path = url.split('//')[1].split('/')[2:-1]  # Skip domain and 'rss.xml'
    if not path:
        return clean_ltree(title or 'unknown')
        
    # Join path parts with underscores
    return '_'.join(path)

def clean_ltree(value):
    """
    Converts a category title into a valid ltree path.
    Maintains hierarchy using '.' and replaces invalid characters.
    """
    if not value:
        return "unknown"
    # Replace '>' with '.' to represent hierarchy
    value = value.replace(">", ".").strip()
    # Replace non-alphanumeric characters (except '.') with underscores
    value = re.sub(r"[^a-zA-Z0-9.]+", "_", value.lower())
    # Remove consecutive dots or underscores
    value = re.sub(r"[._]{2,}", ".", value)
    # Trim leading or trailing dots or underscores
    return value.strip("._")

def is_valid_rss(rss_url):
    """
    Check if RSS feed is valid and contains actual content
    Returns (is_valid, soup, error_message)
    """
    try:
        print(f"\nValidating RSS feed: {rss_url}")
        response = requests.get(rss_url, timeout=10)
        response.raise_for_status()
        
        # Parse the content
        soup = BeautifulSoup(response.content, 'xml')
        
        # Check if it has basic RSS structure
        channel = soup.find('channel')
        if not channel:
            return False, None, "No channel element found"
            
        # Check if it has a title
        title = channel.find('title')
        if not title:
            return False, None, "No title element found"
        
        # Check if it has items
        items = channel.find_all('item')
        if not items:
            print(f"Warning: No items found in feed {rss_url}")
        
        # Print feed details for debugging
        print(f"Feed title: {title.text}")
        if channel.find('description'):
            print(f"Description: {channel.find('description').text}")
            
        return True, soup, None
        
    except requests.exceptions.RequestException as e:
        return False, None, f"HTTP error: {str(e)}"
    except Exception as e:
        return False, None, f"Error: {str(e)}"

def fetch_and_store_bbc_categories():
    # Known BBC RSS patterns
    base_urls = [
        "https://feeds.bbci.co.uk/news/rss.xml",  # Main news
        "https://feeds.bbci.co.uk/news/world/rss.xml",  # World news
        "https://feeds.bbci.co.uk/news/uk/rss.xml",  # UK news
        "https://feeds.bbci.co.uk/news/business/rss.xml",  # Business
        "https://feeds.bbci.co.uk/news/technology/rss.xml",  # Technology
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",  # Science
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",  # Entertainment
        "https://feeds.bbci.co.uk/news/health/rss.xml",  # Health
        "https://feeds.bbci.co.uk/news/education/rss.xml",  # Education
        "https://feeds.bbci.co.uk/news/politics/rss.xml",  # Politics
        
        # Sport sections
        "https://feeds.bbci.co.uk/sport/rss.xml",  # Main sport
        "https://feeds.bbci.co.uk/sport/football/rss.xml",  # Football
        "https://feeds.bbci.co.uk/sport/cricket/rss.xml",  # Cricket
        "https://feeds.bbci.co.uk/sport/formula1/rss.xml",  # Formula 1
        "https://feeds.bbci.co.uk/sport/rugby-union/rss.xml",  # Rugby Union
        "https://feeds.bbci.co.uk/sport/tennis/rss.xml",  # Tennis
        "https://feeds.bbci.co.uk/sport/golf/rss.xml",  # Golf
        "https://feeds.bbci.co.uk/sport/athletics/rss.xml",  # Athletics
        "https://feeds.bbci.co.uk/sport/cycling/rss.xml",  # Cycling
        
        # Regional news
        "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",  # US & Canada
        "https://feeds.bbci.co.uk/news/world/africa/rss.xml",  # Africa
        "https://feeds.bbci.co.uk/news/world/asia/rss.xml",  # Asia
        "https://feeds.bbci.co.uk/news/world/australia/rss.xml",  # Australia
        "https://feeds.bbci.co.uk/news/world/europe/rss.xml",  # Europe
        "https://feeds.bbci.co.uk/news/world/latin_america/rss.xml",  # Latin America
        "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",  # Middle East
        
        # Special sections
        "https://feeds.bbci.co.uk/news/in_pictures/rss.xml",  # In Pictures
        "https://feeds.bbci.co.uk/news/have_your_say/rss.xml",  # Have Your Say
        "https://feeds.bbci.co.uk/news/live/rss.xml"  # Live news
    ]

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
        print("Step 1: Connecting to PostgreSQL and recreating categories table...")
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        # Recreate categories table in schema `bbc`
        recreate_table_query = """
        DROP TABLE IF EXISTS bbc.categories CASCADE;
        
        CREATE TABLE bbc.categories (
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
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (slug, portal_id)
        );
        """
        cursor.execute(recreate_table_query)
        connection.commit()
        print("Categories table recreated successfully.")

        # Step 2: Process each known RSS feed
        print("\nStep 2: Processing known RSS feeds...")
        categories = []
        
        for index, rss_url in enumerate(base_urls, 1):
            try:
                print(f"\n[{index}/{len(base_urls)}] Processing RSS feed: {rss_url}")
                is_valid, rss_soup, error_msg = is_valid_rss(rss_url)
                
                if not is_valid:
                    print(f"❌ Skipping invalid RSS feed: {rss_url}")
                    if error_msg:
                        print(f"Error details: {error_msg}")
                    continue

                print("✓ Feed is valid, extracting metadata...")
                
                channel = rss_soup.find('channel')
                if channel:
                    title = clean_cdata(channel.find('title').string if channel.find('title') else None)
                    link = clean_cdata(channel.find('link').string if channel.find('link') else None)
                    atom_link = channel.find('atom:link')['href'] if channel.find('atom:link') else None
                    description = clean_cdata(channel.find('description').string if channel.find('description') else None)
                    language = clean_cdata(channel.find('language').string if channel.find('language') else None)
                    copyright_text = clean_cdata(channel.find('copyright').string if channel.find('copyright') else None)
                    last_build_date = clean_cdata(channel.find('lastBuildDate').string if channel.find('lastBuildDate') else None)
                    
                    # Add image data if available
                    image = channel.find('image')
                    image_title = clean_cdata(image.find('title').string if image and image.find('title') else None)
                    image_url = clean_cdata(image.find('url').string if image and image.find('url') else None)
                    image_link = clean_cdata(image.find('link').string if image and image.find('link') else None)

                    category_data = {
                        'title': title,
                        'link': link,
                        'atom_link': atom_link,
                        'description': description,
                        'language': language,
                        'copyright_text': copyright_text,
                        'last_build_date': last_build_date,
                        'pub_date': None,
                        'image_title': image_title,
                        'image_url': image_url,
                        'image_link': image_link
                    }
                    
                    print("\nExtracted category data:")
                    for key, value in category_data.items():
                        print(f"  {key}: {value}")
                    
                    categories.append(category_data)
                    print(f"✓ Successfully processed: {title}")
                
            except Exception as e:
                print(f"❌ Error processing feed {rss_url}: {str(e)}")
                continue

        print(f"\nProcessed {len(categories)} out of {len(base_urls)} feeds successfully.")
        print("\nSuccessfully processed categories:")
        for idx, category in enumerate(categories, 1):
            print(f"{idx}. {category['title']} ({category['link']})")

        # Step 3: Insert categories into the table
        print("\nStep 3: Inserting categories into the database...")
        insert_query = """
        INSERT INTO bbc.categories (
            name, slug, portal_id, path, level, title, link, atom_link, description,
            language, copyright_text, last_build_date, pub_date,
            image_title, image_url, image_link, created_at, updated_at
        )
        VALUES %s
        ON CONFLICT (slug, portal_id) DO NOTHING;
        """

        values = []
        for category in categories:
            slug = generate_slug(category['atom_link'], category['title'])
            print(f"Generated slug for {category['title']}: {slug}")  # Debug output
            portal_id = 2  # portal_id for BBC
            path = clean_ltree(category['title'] or 'unknown')
            level = len(slug.split('_'))  # Use depth in URL as level
            
            values.append((
                category['title'], slug, portal_id, path, level, category['title'],
                category['link'], category['atom_link'], category['description'],
                category['language'], category['copyright_text'],
                category['last_build_date'], category['pub_date'],
                category['image_title'], category['image_url'], category['image_link'],
                'now()', 'now()'
            ))

        execute_values(cursor, insert_query, values)
        connection.commit()
        print("Data insertion complete.")

    except Exception as e:
        print(f"Error in main process: {str(e)}")
        if connection:
            connection.rollback()

    finally:
        if cursor:
            cursor.close()
            print("Database cursor closed.")
        if connection:
            connection.close()
            print("Database connection closed.")

if __name__ == "__main__":
    fetch_and_store_bbc_categories()