#!/usr/bin/env python
"""
Reuters Sitemap Articles Parser with Automated Cookie Acceptance
Fetches Reuters sitemap pages using Chromium DevTools (via pychrome),
automatically accepts cookies if present, parses article elements,
and stores them using SQLAlchemy ORM.

This version has been upgraded to detect the total number of pages
by first fetching page 1 (e.g. https://www.reuters.com/sitemap/2025-02/10/1/)
and parsing the pagination text:
    <span data-testid="SitemapFeedPaginationText" ...>1 to 10 of 219</span>
It then calculates the total number of pages (e.g. 22 pages for 219 articles).
"""

import os
import sys
import time
import random
import argparse
import re
import math
from datetime import datetime, timezone

import pychrome
from lxml import html
from sqlalchemy import text

# Add package root to path (if needed)
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Import dynamic model factory functions and database context
from db_scripts.models.models import create_portal_article_model, create_portal_category_model
from db_scripts.db_context import DatabaseContext

def fetch_portal_id_by_prefix(portal_prefix: str, env: str = 'dev'):
    """
    Fetch the portal_id from the news_portals table using the provided portal_prefix.
    """
    db_context = DatabaseContext.get_instance(env)
    with db_context.session() as session:
        result = session.execute(
            text("SELECT portal_id FROM public.news_portals WHERE portal_prefix = :prefix"),
            {'prefix': portal_prefix}
        ).fetchone()
        if result:
            return result[0]
        raise Exception(f"Portal with prefix '{portal_prefix}' not found.")

def slugify(text_str: str) -> str:
    """
    Simple slugify function: lowercases, replaces spaces with hyphens,
    and removes non-alphanumeric characters.
    """
    slug = text_str.lower()
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    return slug

def fetch_page_content(url: str) -> str:
    """
    Opens the specified URL in a new Chromium tab using pychrome,
    waits a random delay between 4 and 7 seconds for the page to load, and:
      - Injects a JS snippet to automatically click on an "Accept Cookies" button (if found)
      - Cleans the page by removing unwanted elements.
    Returns the cleaned HTML.
    """
    browser = pychrome.Browser(url="http://127.0.0.1:9222")
    tab = browser.new_tab()
    try:
        def handle_exception(msg):
            print(f"Debug: {msg}")
        tab.set_listener("exception", handle_exception)
        tab.start()
        tab.Page.enable()
        tab.Runtime.enable()
        tab.Page.navigate(url=url)
        
        # Wait for page to load
        delay = random.uniform(4, 7)
        print(f"Waiting {delay:.2f} seconds for page to load: {url}")
        time.sleep(delay)
        
        # --- AUTOMATE COOKIE ACCEPTANCE ---
        cookie_js = """
        (function() {
            // Try different selectors if needed; adjust the attribute or text to match Reuters' button.
            var btn = document.querySelector('button[aria-label="Accept Cookies"], button[data-testid="CookieBanner-accept"]');
            if (btn) { 
                btn.click(); 
                return "Clicked cookie button";
            }
            return "No cookie button found";
        })();
        """
        result_cookie = tab.Runtime.evaluate(expression=cookie_js)
        print("Cookie acceptance result:", result_cookie.get("result", {}).get("value"))
        
        # Allow time for cookie acceptance to complete
        time.sleep(2)
        
        # --- CLEAN THE HTML ---
        clean_html_js = """
        (function cleanHTML() {
            const elements = document.querySelectorAll('script, style, iframe, link, meta');
            elements.forEach(el => el.remove());
            return document.documentElement.outerHTML;
        })();
        """
        result = tab.Runtime.evaluate(expression=clean_html_js)
        html_content = result["result"]["value"]
        return html_content
    except Exception as e:
        print(f"Error fetching page {url}: {e}")
        return ""
    finally:
        tab.stop()
        browser.close_tab(tab)

def get_or_create_category(session, category_name: str, portal_id, category_model):
    """
    Given a category name, attempts to find an existing category.
    If not found, creates a new category record.
    """
    if not category_name:
        category_name = "Uncategorized"
    # Case-insensitive search
    existing = session.query(category_model).filter(
        category_model.name.ilike(category_name)
    ).first()
    if existing:
        return existing.category_id
    else:
        new_category = category_model(
            name=category_name,
            slug=slugify(category_name),
            portal_id=portal_id,
            path=category_name,
            level=1,
            description=None,
            link=None,
            atom_link=None,
            is_active=True
        )
        session.add(new_category)
        session.commit()  # Commit so that new_category.category_id is generated
        print(f"Created new category: {category_name}")
        return new_category.category_id

class ReutersSitemapParser:
    """
    Parser for Reuters sitemap pages.
    Iterates through sitemap pages, extracts article elements, and stores them.
    """
    def __init__(self, portal_id, env, article_model, category_model):
        self.portal_id = portal_id
        self.env = env
        self.article_model = article_model
        self.category_model = category_model

    def run(self):
        print("Starting Reuters Sitemap Parsing...")
        db_context = DatabaseContext.get_instance(self.env)
        with db_context.session() as session:
            try:
                today = datetime.now()
                date_path = today.strftime("%Y-%m/%d")
                base_url = f"https://www.reuters.com/sitemap/{date_path}/"
                # First page URL for pagination detection
                first_page_url = f"{base_url}1/"
                print(f"Fetching first page for pagination detection: {first_page_url}")
                first_page_html = fetch_page_content(first_page_url)
                if not first_page_html:
                    print("Failed to fetch first page for pagination detection.")
                    return

                # Parse the pagination text to extract total number of articles
                tree = html.fromstring(first_page_html)
                pagination_text_elements = tree.xpath("//span[@data-testid='SitemapFeedPaginationText']/text()")
                if pagination_text_elements:
                    pagination_text = pagination_text_elements[0].strip()
                    print(f"Pagination text found: '{pagination_text}'")
                    match = re.search(r'of\s+(\d+)', pagination_text)
                    if match:
                        total_articles = int(match.group(1))
                        total_pages = math.ceil(total_articles / 10)
                        print(f"Detected total articles: {total_articles} => Total pages: {total_pages}")
                    else:
                        print("Failed to parse pagination text. Using default of 50 pages.")
                        total_pages = 50
                else:
                    print("Pagination text element not found. Using default of 50 pages.")
                    total_pages = 50

                # Process the first page (using the HTML already fetched)
                print(f"\nProcessing page: {first_page_url}")
                self.process_page(session, 1, first_page_html)

                # Process the remaining pages (2 to total_pages) in random order
                remaining_pages = list(range(2, total_pages + 1))
                random.shuffle(remaining_pages)
                for page_num in remaining_pages:
                    page_url = f"{base_url}{page_num}/"
                    print(f"\nProcessing page: {page_url}")
                    page_html = fetch_page_content(page_url)
                    if not page_html:
                        print(f"Failed to fetch content for {page_url}, skipping.")
                        continue
                    self.process_page(session, page_num, page_html)
                    sleep_time = random.uniform(5, 9)
                    print(f"Sleeping for {sleep_time:.2f} seconds before next page...")
                    time.sleep(sleep_time)
                print("Reuters Sitemap Parsing completed successfully.")
            except Exception as e:
                print(f"Error during parsing: {e}")
                session.rollback()
                raise

    def process_page(self, session, page_num, page_html):
        """
        Processes a single sitemap page: parses the article elements and stores them.
        """
        tree = html.fromstring(page_html)
        article_elements = tree.xpath("//li[@data-testid='FeedListItem']")
        print(f"Found {len(article_elements)} article(s) on page {page_num}.")
        for article_el in article_elements:
            article_data = self.parse_article(article_el)
            # Temporarily hold category name in the data and then get or create a category_id.
            category_name = article_data.pop("category_name", "Uncategorized")
            category_id = get_or_create_category(session, category_name, self.portal_id, self.category_model)
            article_data['category_id'] = category_id

            # Use the full URL as the GUID.
            existing_article = session.query(self.article_model).filter(
                self.article_model.guid == article_data['guid']
            ).first()
            if existing_article:
                # Update if publication date has changed.
                if existing_article.pub_date != article_data['pub_date']:
                    for key, value in article_data.items():
                        setattr(existing_article, key, value)
                    print(f"Updated article: {article_data['title']}")
            else:
                new_article = self.article_model(**article_data)
                session.add(new_article)
                print(f"Added new article: {article_data['title']}")
        session.commit()

    def parse_article(self, article_el) -> dict:
        """
        Extracts all required fields from an article element.
        If a field is missing, a default or empty value is set.
        """
        # --- Title ---
        title_list = article_el.xpath('.//span[@data-testid="TitleHeading"]//text()')
        title = " ".join(title_list).strip() if title_list else "Untitled"

        # --- URL & GUID ---
        url_list = article_el.xpath('.//a[@data-testid="TitleLink"]/@href')
        relative_url = url_list[0].strip() if url_list else ""
        if relative_url.startswith("/"):
            full_url = "https://www.reuters.com" + relative_url
        else:
            full_url = relative_url
        guid = full_url  # use full URL as unique identifier

        # --- Description & Content ---
        desc_list = article_el.xpath('.//p[@data-testid="Description"]//text()')
        description = " ".join(desc_list).strip() if desc_list else None
        content = description  # Using description as content fallback

        # --- Publication Date ---
        pub_date_list = article_el.xpath('.//time[@data-testid="DateLineText"]//text()')
        pub_date_text = " ".join(pub_date_list).strip() if pub_date_list else ""
        try:
            if "ago" in pub_date_text.lower():
                pub_date = datetime.now(timezone.utc)
            else:
                from dateutil import parser
                pub_date = parser.parse(pub_date_text)
        except Exception:
            pub_date = datetime.now(timezone.utc)

        # --- Authors ---
        # Reuters may not always provide author info.
        authors_attr = article_el.get("data-are-authors", "false")
        authors = [] if authors_attr.lower() == "false" else []

        # --- Image URL ---
        img_list = article_el.xpath('.//img/@src')
        image_url = img_list[0].strip() if img_list else None

        # --- Category (for grouping) ---
        category_list = article_el.xpath('.//span[@data-testid="KickerText"]//text()')
        category_name = " ".join(category_list).strip() if category_list else "Uncategorized"

        # --- Reading Time (estimate: 200 words per minute) ---
        combined_text = f"{title} {description or ''} {content or ''}"
        word_count = len(combined_text.split())
        reading_time_minutes = max(1, round(word_count / 200))

        # --- Assemble Article Data ---
        article_data = {
            'title': title,
            'url': full_url,
            'guid': guid,
            'description': description,
            'content': content,
            'author': authors,
            'pub_date': pub_date,
            'keywords': [],  # No keywords available on the sitemap page
            'reading_time_minutes': reading_time_minutes,
            'language_code': 'en',
            'image_url': image_url,
            'sentiment_score': 0.0,  # Default neutral sentiment
            'share_count': 0,
            'view_count': 0,
            'comment_count': 0,
            # Temporarily store the category name
            'category_name': category_name
        }
        return article_data

def main():
    argparser = argparse.ArgumentParser(description="Reuters Sitemap Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    try:
        portal_id = fetch_portal_id_by_prefix("pt_reuters", env=args.env)
    except Exception as e:
        print(f"Failed to fetch portal id: {e}")
        return

    # Create dynamic models for Reuters
    ReutersArticle = create_portal_article_model("pt_reuters")
    ReutersCategory = create_portal_category_model("pt_reuters")

    parser = ReutersSitemapParser(
        portal_id=portal_id,
        env=args.env,
        article_model=ReutersArticle,
        category_model=ReutersCategory
    )
    parser.run()

if __name__ == "__main__":
    main()
