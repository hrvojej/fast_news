#!/usr/bin/env python3
"""
Reuters Sitemap Parser

This script fetches Reuters sitemap pages using Chromium DevTools (via pychrome),
automatically accepts cookies if present, parses article metadata, and stores new
articles (or updates existing ones) in the pt_reuters articles table. Article content
updating is handled separately.
"""

import sys
import os
import argparse
import random
import time
import re
import math
from datetime import datetime, timezone

import pychrome
from lxml import html
from dateutil import parser as dateutil_parser

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from portals.modules.logging_config import setup_script_logging
from db_scripts.models.models import (
    create_portal_category_model,
    create_portal_article_model
)
from db_scripts.db_context import DatabaseContext
from portals.modules.portal_db import fetch_portal_id_by_prefix  # shared utility

logger = setup_script_logging(__file__)

# Dynamically create models for the Reuters portal.
ReutersCategory = create_portal_category_model("pt_reuters")
ReutersArticle = create_portal_article_model("pt_reuters")


def slugify(text_str: str) -> str:
    """
    Lowercase the text, replace spaces with hyphens, and remove non-alphanumeric characters.
    """
    slug = text_str.lower()
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    return slug


def fetch_page_content(url: str) -> str:
    """
    Opens the specified URL in a new Chromium tab using pychrome,
    waits a random delay between 4 and 7 seconds for the page to load,
    automatically clicks any "Accept Cookies" button if present,
    and then cleans the HTML by removing unwanted elements.
    Returns the cleaned HTML.
    """
    try:
        browser = pychrome.Browser(url="http://127.0.0.1:9222")
        tab = browser.new_tab()
        tab.start()
        tab.Page.enable()
        tab.Runtime.enable()
        tab.Page.navigate(url=url)

        delay = random.uniform(4, 7)
        logger.info(f"Waiting {delay:.2f} seconds for page to load: {url}")
        time.sleep(delay)

        # AUTOMATE COOKIE ACCEPTANCE
        cookie_js = """
        (function() {
            var btn = document.querySelector('button[aria-label="Accept Cookies"], button[data-testid="CookieBanner-accept"]');
            if (btn) { 
                btn.click(); 
                return "Clicked cookie button";
            }
            return "No cookie button found";
        })();
        """
        result_cookie = tab.Runtime.evaluate(expression=cookie_js)
        logger.info("Cookie acceptance result: %s", result_cookie.get("result", {}).get("value"))
        time.sleep(2)

        # CLEAN THE HTML: remove unwanted elements
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
        logger.error(f"Error fetching page {url}: {e}")
        return ""
    finally:
        try:
            tab.stop()
            browser.close_tab(tab)
        except Exception:
            pass


def get_or_create_category(session, category_name: str, portal_id, category_model):
    """
    Given a category name, looks for an existing category (case-insensitive).
    If not found, creates a new category record.
    """
    if not category_name:
        category_name = "Uncategorized"
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
        session.commit()
        logger.info(f"Created new category: {category_name}")
        return new_category.category_id


class ReutersSitemapParser:
    """
    Iterates through today's Reuters sitemap pages, extracts article metadata,
    and stores them in the database.
    """
    def __init__(self, env: str, portal_id):
        self.env = env
        self.portal_id = portal_id
        self.db_context = DatabaseContext.get_instance(env)

    def run(self):
        logger.info("Starting Reuters Sitemap Parsing...")
        today = datetime.now()
        date_path = today.strftime("%Y-%m/%d")
        base_url = f"https://www.reuters.com/sitemap/{date_path}/"
        first_page_url = f"{base_url}1/"
        logger.info(f"Fetching first page for pagination detection: {first_page_url}")
        first_page_html = fetch_page_content(first_page_url)
        if not first_page_html:
            logger.error("Failed to fetch first page for pagination detection.")
            return

        tree = html.fromstring(first_page_html)
        pagination_text_elements = tree.xpath("//span[@data-testid='SitemapFeedPaginationText']/text()")
        if pagination_text_elements:
            pagination_text = pagination_text_elements[0].strip()
            logger.info(f"Pagination text found: '{pagination_text}'")
            match = re.search(r'of\s+(\d+)', pagination_text)
            if match:
                total_articles = int(match.group(1))
                total_pages = math.ceil(total_articles / 10)
                logger.info(f"Detected total articles: {total_articles} => Total pages: {total_pages}")
            else:
                logger.warning("Failed to parse pagination text. Using default of 50 pages.")
                total_pages = 50
        else:
            logger.warning("Pagination text element not found. Using default of 50 pages.")
            total_pages = 50

        with self.db_context.session() as session:
            logger.info(f"Processing first page: {first_page_url}")
            self.process_page(session, 1, first_page_html)

            remaining_pages = list(range(2, total_pages + 1))
            random.shuffle(remaining_pages)
            for page_num in remaining_pages:
                page_url = f"{base_url}{page_num}/"
                logger.info(f"Processing page: {page_url}")
                page_html = fetch_page_content(page_url)
                if not page_html:
                    logger.warning(f"Failed to fetch content for {page_url}, skipping.")
                    continue
                self.process_page(session, page_num, page_html)
                sleep_time = random.uniform(5, 9)
                logger.info(f"Sleeping for {sleep_time:.2f} seconds before next page...")
                time.sleep(sleep_time)
        logger.info("Reuters Sitemap Parsing completed successfully.")

    def process_page(self, session, page_num: int, page_html: str):
        tree = html.fromstring(page_html)
        article_elements = tree.xpath("//li[@data-testid='FeedListItem']")
        logger.info(f"Found {len(article_elements)} article(s) on page {page_num}.")
        for article_el in article_elements:
            article_data = self.parse_article(article_el)
            # Resolve the category by name (or default to Uncategorized)
            category_name = article_data.pop("category_name", "Uncategorized")
            category_id = get_or_create_category(session, category_name, self.portal_id, ReutersCategory)
            article_data['category_id'] = category_id

            # Use the article's URL as a unique identifier (guid)
            existing_article = session.query(ReutersArticle).filter(
                ReutersArticle.guid == article_data['guid']
            ).first()
            if existing_article:
                # Update fields if publication date has changed
                if existing_article.pub_date != article_data['pub_date']:
                    for key, value in article_data.items():
                        setattr(existing_article, key, value)
                    logger.info(f"Updated article: {article_data['title']}")
            else:
                new_article = ReutersArticle(**article_data)
                session.add(new_article)
                logger.info(f"Added new article: {article_data['title']}")
        session.commit()

    def parse_article(self, article_el) -> dict:
        # --- Title ---
        title_list = article_el.xpath('.//span[@data-testid="TitleHeading"]//text()')
        title = " ".join(title_list).strip() if title_list else "Untitled"

        # --- URL & GUID ---
        url_list = article_el.xpath('.//a[@data-testid="TitleLink"]/@href')
        relative_url = url_list[0].strip() if url_list else ""
        full_url = "https://www.reuters.com" + relative_url if relative_url.startswith("/") else relative_url
        guid = full_url  # use full URL as unique identifier

        # --- Description & Content (placeholder until detailed content is fetched) ---
        desc_list = article_el.xpath('.//p[@data-testid="Description"]//text()')
        description = " ".join(desc_list).strip() if desc_list else None
        content = description

        # --- Publication Date ---
        pub_date_list = article_el.xpath('.//time[@data-testid="DateLineText"]//text()')
        pub_date_text = " ".join(pub_date_list).strip() if pub_date_list else ""
        try:
            if "ago" in pub_date_text.lower():
                pub_date = datetime.now(timezone.utc)
            else:
                pub_date = dateutil_parser.parse(pub_date_text)
        except Exception:
            pub_date = datetime.now(timezone.utc)

        # --- Authors ---
        authors_attr = article_el.get("data-are-authors", "false")
        authors = [] if authors_attr.lower() == "false" else []

        # --- Image URL ---
        img_list = article_el.xpath('.//img/@src')
        image_url = img_list[0].strip() if img_list else None

        # --- Category (temporary, will be resolved to a category_id) ---
        category_list = article_el.xpath('.//span[@data-testid="KickerText"]//text()')
        category_name = " ".join(category_list).strip() if category_list else "Uncategorized"

        # --- Reading Time Estimate (assuming 200 words per minute) ---
        combined_text = f"{title} {description or ''} {content or ''}"
        word_count = len(combined_text.split())
        reading_time_minutes = max(1, round(word_count / 200))

        article_data = {
            'title': title,
            'url': full_url,
            'guid': guid,
            'description': description,
            'content': content,
            'author': authors,
            'pub_date': pub_date,
            'keywords': [],
            'reading_time_minutes': reading_time_minutes,
            'language_code': 'en',
            'image_url': image_url,
            'sentiment_score': 0.0,
            'share_count': 0,
            'view_count': 0,
            'comment_count': 0,
            # Temporarily store the category name; will be replaced by category_id
            'category_name': category_name
        }
        return article_data


def main():
    argparser = argparse.ArgumentParser(description="Reuters Sitemap Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    try:
        # Fetch the portal_id using the shared utility (similar to the pt_abc parser)
        portal_id = fetch_portal_id_by_prefix("pt_reuters", env=args.env)
    except Exception as e:
        logger.error(f"Failed to fetch portal id: {e}")
        return

    parser_instance = ReutersSitemapParser(env=args.env, portal_id=portal_id)
    parser_instance.run()


if __name__ == "__main__":
    main()
