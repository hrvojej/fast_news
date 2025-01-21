import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values
import re

def validate_html_content(html_content):
    """Validate if the HTML content is properly accessible and contains expected elements"""
    print("\nValidating HTML content...")
    
    if not html_content:
        print("ERROR: Empty HTML content")
        return False
        
    print(f"HTML content length: {len(html_content)} characters")
    
    # Print first 500 characters to check content type
    print("\nFirst 500 characters of HTML content:")
    print(html_content[:500])
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Try to find the main navigation
    nav = soup.find('nav', class_='subnav')
    if not nav:
        print("\nERROR: Could not find main navigation with class 'subnav'")
        # Let's see what classes we do have
        all_navs = soup.find_all('nav')
        print(f"\nFound {len(all_navs)} nav elements with following classes:")
        for nav in all_navs:
            print(f"Nav classes: {nav.get('class', 'No class')}")
        return False
        
    # Check for sections
    sections = nav.find_all('li', class_='subnav__section')
    if not sections:
        print("\nERROR: No sections found in navigation")
        # Let's see what we do have inside nav
        print("\nNav content:")
        print(nav.prettify()[:500])  # Print first 500 chars of nav content
        return False
        
    print(f"\nValidation successful! Found {len(sections)} sections")
    return True

def extract_categories_from_footer(html_content):
    """Extract categories and subcategories from the footer navigation"""
    print("\nExtracting categories from footer HTML...")
    
    # First validate the HTML content
    if not validate_html_content(html_content):
        print("HTML validation failed - cannot proceed with extraction")
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    categories = []
    
    # Find the main navigation container
    nav = soup.find('nav', class_='subnav')
    sections = nav.find_all('li', class_='subnav__section')
    print(f"Processing {len(sections)} main sections...")
    
    for idx, section in enumerate(sections, 1):
        main_link = section.find('a', class_='subnav__section-link')
        if not main_link:
            print(f"WARNING: Section {idx} has no main link, skipping")
            print("Section content:")
            print(section.prettify())
            continue
            
        main_title = main_link.text.strip()
        main_href = main_link.get('href', '')
        print(f"\nProcessing main category {idx}/{len(sections)}: {main_title}")
        print(f"Link: {main_href}")
        
        main_category = {
            'title': main_title,
            'link': main_href,
            'atom_link': None,
            'description': f"{main_title}",
            'language': 'en',
            'copyright_text': None,
            'last_build_date': None,
            'pub_date': None,
            'image_title': None,
            'image_url': None,
            'image_link': None,
            'subcategories': []
        }
        
        # Get subcategories
        subsections = section.find_all('li', class_='subnav__subsection')
        print(f"Found {len(subsections)} subcategories")
        
        for sub_idx, subsection in enumerate(subsections, 1):
            sub_link = subsection.find('a', class_='subnav__subsection-link')
            if sub_link:
                sub_title = sub_link.text.strip()
                sub_href = sub_link.get('href', '')
                print(f"  - Subcategory {sub_idx}: {sub_title}")
                print(f"    Link: {sub_href}")
                
                subcategory = {
                    'title': sub_title,
                    'link': sub_href,
                    'atom_link': None,
                    'description': f"{main_title} - {sub_title}",
                    'language': 'en',
                    'copyright_text': None,
                    'last_build_date': None,
                    'pub_date': None,
                    'image_title': None,
                    'image_url': None,
                    'image_link': None
                }
                main_category['subcategories'].append(subcategory)
        
        categories.append(main_category)
    
    print(f"\nTotal categories extracted: {len(categories)}")
    for cat in categories:
        print(f"- {cat['title']} ({len(cat['subcategories'])} subcategories)")
    
    return categories

def setup_cnn_categories(html_content):
    """Set up CNN categories table and populate it from footer navigation"""
    print("\nStarting CNN categories setup...")
    
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
        print("\nStep 1: Connecting to database and creating schema...")
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        # Create schema if not exists
        print("Creating CNN schema if it doesn't exist...")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS cnn;")

        print("\nRecreating categories table...")
        recreate_table_query = """
        DROP TABLE IF EXISTS cnn.categories CASCADE;
        
        CREATE TABLE cnn.categories (
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
        print("Categories table created successfully.")

        print("\nStep 2: Processing categories...")
        categories = extract_categories_from_footer(html_content)
        
        if not categories:
            print("No categories found - please check the HTML content and structure")
            return
            
        print("\nStep 3: Preparing data for insertion...")
        values = []
        
        # Process main categories
        for idx, category in enumerate(categories, 1):
            print(f"\nProcessing main category {idx}/{len(categories)}: {category['title']}")
            
            main_slug = generate_slug(category['link'], category['title'])
            main_path = clean_ltree(category['title'])
            
            print(f"Main category path: {main_path}")
            
            # Add main category
            values.append((
                category['title'],
                main_slug,
                3,  # portal_id for CNN
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
                
                sub_slug = generate_slug(subcategory['link'], subcategory['title'])
                sub_path = f"{main_path}.{clean_ltree(subcategory['title'])}"
                print(f"  Subcategory path: {sub_path}")
                
                values.append((
                    subcategory['title'],
                    sub_slug,
                    3,  # portal_id for CNN
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
            INSERT INTO cnn.categories (
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
            print("\nDatabase cursor closed.")
        if connection:
            connection.close()
            print("Database connection closed.")

def clean_ltree(value):
    """Cleans a string for use as ltree path"""
    if not value:
        return "unknown"
    value = value.replace(">", ".").strip()
    value = re.sub(r"[^a-zA-Z0-9.]+", "_", value.lower())
    value = re.sub(r"[._]{2,}", ".", value)
    return value.strip("._")

def generate_slug(url, title):
    """Generate a unique slug from URL and title"""
    if not url:
        return clean_ltree(title or 'unknown')
        
    try:
        path = url.split('//')[1].split('/')[1:]
        path = [p for p in path if p and p not in ['index.html', 'article', 'articles']]
        if not path:
            return clean_ltree(title or 'unknown')
        return '_'.join(path)
    except:
        return clean_ltree(title or 'unknown')

def fetch_cnn_html():
    """Fetch HTML content from CNN website"""
    print("\nFetching HTML content from CNN...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    
    url = 'https://edition.cnn.com/'
    
    try:
        print(f"Requesting URL: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"Response status code: {response.status_code}")
        print(f"Response length: {len(response.text)} characters")
        
        return response.text
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching CNN homepage: {str(e)}")
        return None

if __name__ == "__main__":
    try:
        print("Starting CNN categories parser...")
        
        # Fetch HTML content from CNN website
        html_content = fetch_cnn_html()
        
        if not html_content:
            print("Failed to fetch HTML content from CNN. Exiting.")
            exit(1)
        
        setup_cnn_categories(html_content)
        print("\nScript completed successfully.")
    except Exception as e:
        print(f"\nFATAL ERROR: {str(e)}")
        raise