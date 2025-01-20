import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import time
from typing import Optional, Dict, Any
import xml.etree.ElementTree as ET
from dateutil import parser as date_parser

def fetch_rss_data(url: str) -> Optional[Dict[str, Any]]:
    """Fetch and parse RSS feed data"""
    print(f"\nFetching RSS feed: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/rss+xml,application/xml',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse XML content
        root = ET.fromstring(response.content)
        channel = root.find('channel')
        
        if channel is None:
            print(f"No channel element found in RSS feed: {url}")
            return None
            
        # Find image details
        image = channel.find('image')
        image_data = {}
        if image is not None:
            image_data = {
                'image_title': get_element_text(image, 'title'),
                'image_url': get_element_text(image, 'url'),
                'image_link': get_element_text(image, 'link')
            }
        
        # Extract feed data
        feed_data = {
            'title': get_element_text(channel, 'title'),
            'link': get_element_text(channel, 'link'),
            'description': get_element_text(channel, 'description'),
            'language': get_element_text(channel, 'language'),
            'copyright_text': get_element_text(channel, 'copyright'),
            'last_build_date': parse_date(get_element_text(channel, 'lastBuildDate')),
            'pub_date': parse_date(get_element_text(channel, 'pubDate')),
            **image_data
        }
        
        # Remove "| The Guardian" from title if present
        if feed_data['title']:
            feed_data['title'] = feed_data['title'].replace(' | The Guardian', '')
        
        return feed_data
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching RSS feed {url}: {str(e)}")
        return None
    except ET.ParseError as e:
        print(f"Error parsing RSS feed {url}: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error processing RSS feed {url}: {str(e)}")
        return None

def get_element_text(element: ET.Element, tag: str) -> Optional[str]:
    """Safely extract text from an XML element"""
    el = element.find(tag)
    return el.text.strip() if el is not None and el.text else None

def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string to datetime object"""
    if not date_str:
        return None
    try:
        return date_parser.parse(date_str)
    except (ValueError, TypeError):
        return None

def update_guardian_categories():
    """Update Guardian categories with RSS feed data"""
    print("\nStarting Guardian categories RSS update...")
    
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
        print("\nConnecting to database...")
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        # Get all Guardian categories with RSS links
        print("\nFetching categories with RSS links...")
        cursor.execute("""
            SELECT category_id, atom_link 
            FROM guardian.categories 
            WHERE atom_link IS NOT NULL 
            AND portal_id = 4
        """)
        categories = cursor.fetchall()

        print(f"\nFound {len(categories)} categories to update")
        
        for idx, (category_id, atom_link) in enumerate(categories, 1):
            print(f"\nProcessing category {idx}/{len(categories)}")
            print(f"RSS Link: {atom_link}")
            
            # Fetch RSS data
            rss_data = fetch_rss_data(atom_link)
            
            if not rss_data:
                print(f"Skipping category {category_id} - no RSS data available")
                continue
            
            # Update category with RSS data
            update_query = """
            UPDATE guardian.categories
            SET 
                title = COALESCE(%s, title),
                link = COALESCE(%s, link),
                description = COALESCE(%s, description),
                language = COALESCE(%s, language),
                copyright_text = COALESCE(%s, copyright_text),
                last_build_date = COALESCE(%s, last_build_date),
                pub_date = COALESCE(%s, pub_date),
                image_title = COALESCE(%s, image_title),
                image_url = COALESCE(%s, image_url),
                image_link = COALESCE(%s, image_link),
                updated_at = CURRENT_TIMESTAMP
            WHERE category_id = %s
            """
            
            cursor.execute(update_query, (
                rss_data.get('title'),
                rss_data.get('link'),
                rss_data.get('description'),
                rss_data.get('language'),
                rss_data.get('copyright_text'),
                rss_data.get('last_build_date'),
                rss_data.get('pub_date'),
                rss_data.get('image_title'),
                rss_data.get('image_url'),
                rss_data.get('image_link'),
                category_id
            ))
            
            # Commit each update individually
            connection.commit()
            print(f"Updated category {category_id} successfully")
            
            # Add delay between requests
            time.sleep(2)

        print("\nCategory update process completed successfully")

    except Exception as e:
        print(f"\nERROR in update process: {str(e)}")
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            print("\nDatabase connection closed")

if __name__ == "__main__":
    try:
        update_guardian_categories()
    except Exception as e:
        print(f"\nFATAL ERROR: {str(e)}")
        raise