import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values
import re
import time
from urllib.parse import urljoin

BASE_URL = 'https://www.theguardian.com'

def validate_html_content(html_content):
    """Validate if the HTML content is properly accessible and contains expected elements"""
    print("\nValidating HTML content...")
    
    if not html_content:
        print("ERROR: Empty HTML content")
        return False
        
    print(f"HTML content length: {len(html_content)} characters")
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Try to find main navigation links
    nav_links = soup.find_all('a', class_='dcr-7612kl')
    if not nav_links:
        print("\nERROR: Could not find main navigation links")
        return False
        
    print(f"\nValidation successful! Found {len(nav_links)} main navigation links")
    return True

def extract_categories(html_content):
    """Extract main categories and their subcategories from Guardian navigation"""
    print("\nExtracting categories from Guardian HTML...")
    
    if not validate_html_content(html_content):
        print("HTML validation failed - cannot proceed with extraction")
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    categories = []
    
    # Find main category links
    main_links = soup.find_all('a', class_='dcr-7612kl')
    print(f"Found {len(main_links)} main categories")
    
    for idx, main_link in enumerate(main_links, 1):
        href = main_link.get('href', '')
        if href == '/':
            href = '/news'  # Special case for home/news
            
        full_url = urljoin(BASE_URL, href)
        title = main_link.text.strip()
        
        print(f"\nProcessing main category {idx}/{len(main_links)}: {title}")
        print(f"URL: {full_url}")
        
        main_category = {
            'title': title,
            'link': full_url,
            'atom_link': f"{full_url}/rss",
            'description': None,
            'language': 'en',
            'copyright_text': None,
            'last_build_date': None,
            'pub_date': None,
            'image_title': None,
            'image_url': None,
            'image_link': None,
            'subcategories': []
        }
        
        # Fetch subcategories from the category page
        try:
            response = requests.get(full_url, timeout=30)
            if response.status_code == 200:
                sub_soup = BeautifulSoup(response.text, 'html.parser')
                sub_links = sub_soup.find_all('li', class_='dcr-5wkng0')
                
                print(f"Found {len(sub_links)} subcategories")
                
                for sub_idx, sub_item in enumerate(sub_links, 1):
                    sub_link = sub_item.find('a')
                    if sub_link:
                        sub_href = sub_link.get('href', '')
                        sub_full_url = urljoin(BASE_URL, sub_href)
                        sub_title = sub_link.text.strip()
                        
                        print(f"  - Subcategory {sub_idx}: {sub_title}")
                        print(f"    Link: {sub_full_url}")
                        
                        subcategory = {
                            'title': sub_title,
                            'link': sub_full_url,
                            'atom_link': f"{sub_full_url}/rss",
                            'description': None,
                            'language': 'en',
                            'copyright_text': None,
                            'last_build_date': None,
                            'pub_date': None,
                            'image_title': None,
                            'image_url': None,
                            'image_link': None
                        }
                        main_category['subcategories'].append(subcategory)
            else:
                print(f"Failed to fetch subcategories for {title}. Status code: {response.status_code}")
        except Exception as e:
            print(f"Error fetching subcategories for {title}: {str(e)}")
        
        # Add delay between requests
        time.sleep(2)
        categories.append(main_category)
    
    return categories

def setup_guardian_categories(html_content):
    """Set up Guardian categories table and populate it"""
    print("\nStarting Guardian categories setup...")
    
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
        print("\nStep 1: Connecting to database and creating schema...")
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        print("Creating Guardian schema if it doesn't exist...")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS guardian;")

        print("\nRecreating categories table...")
        recreate_table_query = """
        DROP TABLE IF EXISTS guardian.categories CASCADE;
        
        CREATE TABLE guardian.categories (
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

        print("\nStep 2: Processing categories...")
        categories = extract_categories(html_content)
        
        if not categories:
            print("No categories found - please check the HTML content and structure")
            return
            
        print("\nStep 3: Preparing data for insertion...")
        values = []
        
        # Process main categories
        for idx, category in enumerate(categories, 1):
            print(f"\nProcessing main category {idx}/{len(categories)}: {category['title']}")
            
            main_slug = generate_slug(category['link'])
            main_path = clean_ltree(category['title'])
            
            print(f"Main category path: {main_path}")
            
            # Add main category
            values.append((
                category['title'],
                main_slug,
                4,  # portal_id for Guardian
                main_path,
                1,  # level
                category['title'],
                category['link'],
                category['atom_link'],
                category['description'],
                category['language'],
                category['copyright_text'],
                category['last_build_date'],
                category['pub_date'],
                category['image_title'],
                category['image_url'],
                category['image_link']
            ))
            
            # Add subcategories
            for sub_idx, subcategory in enumerate(category['subcategories'], 1):
                print(f"  Processing subcategory {sub_idx}: {subcategory['title']}")
                
                sub_slug = generate_slug(subcategory['link'])
                sub_path = f"{main_path}.{clean_ltree(subcategory['title'])}"
                print(f"  Subcategory path: {sub_path}")
                
                values.append((
                    subcategory['title'],
                    sub_slug,
                    4,  # portal_id for Guardian
                    sub_path,
                    2,  # level
                    subcategory['title'],
                    subcategory['link'],
                    subcategory['atom_link'],
                    subcategory['description'],
                    subcategory['language'],
                    subcategory['copyright_text'],
                    subcategory['last_build_date'],
                    subcategory['pub_date'],
                    subcategory['image_title'],
                    subcategory['image_url'],
                    subcategory['image_link']
                ))

        print(f"\nStep 4: Inserting {len(values)} total records...")
        if values:
            insert_query = """
            INSERT INTO guardian.categories (
                name, slug, portal_id, path, level, title, link, atom_link, description,
                language, copyright_text, last_build_date, pub_date,
                image_title, image_url, image_link
            )
            VALUES %s
            ON CONFLICT (slug, portal_id) DO NOTHING;
            """
            
            execute_values(cursor, insert_query, values)
            connection.commit()
            print(f"Successfully inserted {len(values)} categories and subcategories.")
        else:
            print("No categories found to insert.")

    except Exception as e:
        print(f"\nERROR in main process: {str(e)}")
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def clean_ltree(value):
    """Cleans a string for use as ltree path"""
    if not value:
        return "unknown"
    value = value.replace(">", ".").strip()
    value = re.sub(r"[^a-zA-Z0-9.]+", "_", value.lower())
    value = re.sub(r"[._]{2,}", ".", value)
    return value.strip("._")

def generate_slug(url):
    """Generate a unique slug from URL"""
    try:
        path = url.split('//')[1].split('/')[1:]
        path = [p for p in path if p and p not in ['index.html', 'article', 'articles']]
        if not path:
            return 'home'
        return '_'.join(path)
    except:
        return 'unknown'

def fetch_guardian_html():
    """Fetch HTML content from Guardian website"""
    print("\nFetching HTML content from Guardian...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    
    url = 'https://www.theguardian.com'
    
    try:
        print(f"Requesting URL: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"Response status code: {response.status_code}")
        print(f"Response length: {len(response.text)} characters")
        
        return response.text
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Guardian homepage: {str(e)}")
        return None

if __name__ == "__main__":
    try:
        print("Starting Guardian categories parser...")
        
        # Fetch HTML content from Guardian website
        html_content = fetch_guardian_html()
        
        if not html_content:
            print("Failed to fetch HTML content from Guardian. Exiting.")
            exit(1)
        
        setup_guardian_categories(html_content)
        print("\nScript completed successfully.")
    except Exception as e:
        print(f"\nFATAL ERROR: {str(e)}")
        raise