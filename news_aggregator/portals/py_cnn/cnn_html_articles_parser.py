#!/usr/bin/env python
import argparse
import os
import sys
import re
import unicodedata
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse
from uuid import UUID

import requests
from bs4 import BeautifulSoup
from sqlalchemy import text

# Add package root to path.
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from db_scripts.models.models import create_portal_category_model, create_portal_article_model
from portals.modules.logging_config import setup_script_logging
from portals.modules.keyword_extractor import KeywordExtractor
from portals.modules.portal_db import fetch_portal_id_by_prefix

# Configure logger.
logger = setup_script_logging(__file__)

# Dynamically create models for CNN portal.
CNNCategory = create_portal_category_model("pt_cnn")
CNNArticle = create_portal_article_model("pt_cnn")


class BaseHTMLParser:
    """
    Base class for HTML parsers.
    Provides common functionality such as database session management
    and page fetching with a retry mechanism.
    """
    def __init__(self, portal_id: UUID, env: str = 'dev'):
        self.portal_id = portal_id
        self.env = env
        from db_scripts.db_context import DatabaseContext
        self.db_context = DatabaseContext.get_instance(env)

    def get_session(self):
        """Obtain a database session."""
        return self.db_context.session().__enter__()

    def fetch_page(self, url: str, max_retries: int = 3) -> str:
        """
        Fetches page content using a retry mechanism.
        :param url: URL to fetch.
        :param max_retries: Maximum number of retries.
        :return: HTML content as text.
        """
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/58.0.3029.110 Safari/537.3'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }

        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                logger.error("Error fetching URL %s: %s", url, e)
                if attempt == max_retries - 1:
                    raise
                time.sleep(2)


class CNNArticlesParser(BaseHTMLParser):
    """
    CNN HTML articles parser.
    Inherits common functionality from BaseHTMLParser.
    """
    def __init__(self, portal_id: UUID, env: str = 'dev'):
        super().__init__(portal_id, env)
        self.model = CNNArticle
        self.keyword_extractor = KeywordExtractor()

    @staticmethod
    def extract_pub_date_from_url(url: str) -> str:
        """
        Extract publication date from a URL using a regex.
        :param url: URL string.
        :return: Publication date in YYYY-MM-DD format, or None.
        """
        path = urlparse(url).path
        match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', path)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month}-{day}"
        return None

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean text from unwanted characters and normalize whitespace.
        :param text: Raw text.
        :return: Cleaned text.
        """
        if not text:
            return ""
        cleaned = text.strip()
        cleaned = re.sub(r'[\n\r\t\f\v]+', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'¶|•|■|▪|►|▼|▲|◄|★|☆|⚡', '', cleaned)
        cleaned = "".join(char for char in cleaned if unicodedata.category(char)[0] != "C")
        return cleaned.strip()

    def parse_article(self, card: BeautifulSoup, category_id: UUID, base_url: str) -> dict:
        """
        Parse a single CNN article card.
        :param card: BeautifulSoup element containing article info.
        :param category_id: Category identifier.
        :param base_url: Base URL for joining relative links.
        :return: Dictionary with article data or None if parsing fails.
        """
        link_elem = card.find('a', class_='container__link') or card.find('a', href=True)
        if not link_elem or not link_elem.get('href'):
            return None

        relative_url = link_elem.get('href').strip()
        full_url = urljoin(base_url, relative_url)
        publication_date = self.extract_pub_date_from_url(relative_url)

        # Extract title from dedicated elements.
        title = None
        title_elem = card.find('span', class_='container__headline-text')
        if title_elem:
            title = self.clean_text(title_elem.get_text())
        if not title:
            headline_div = link_elem.find('div', class_='container__headline')
            if headline_div:
                title = self.clean_text(headline_div.get_text())
        if not title:
            link_text = self.clean_text(link_elem.get_text())
            if len(link_text) > 10:
                title = link_text
        if not title or len(title) < 10:
            return None

        # Extract author from its dedicated element.
        author = None
        author_elem = card.find('span', class_='metadata__byline__author')
        if author_elem:
            author = self.clean_text(author_elem.get_text())
            author = re.sub(r'^By\s+', '', author)

        # Further clean the title.
        title = re.sub(r'►\s*Video\s*►\s*', '', title)
        title = re.sub(r'▶\s*', '', title)
        title = re.sub(r'\s*\d+:\d+\s*$', '', title)

        # Extract image URL.
        image = card.find('img')
        image_url = None
        if image:
            image_url = image.get('src') or image.get('data-src')
            if image_url:
                image_url = image_url.strip()

        # Calculate reading time based on title word count.
        word_count = len(title.split())
        reading_time = max(1, round(word_count / 200))

        # Extract keywords using the shared keyword extractor.
        keywords = self.keyword_extractor.extract_keywords(title) if title else []

        article_data = {
            'title': title,
            'url': full_url,
            'guid': full_url,
            'category_id': category_id,
            'description': None,
            'content': None,
            'author': [author] if author else [],
            'pub_date': publication_date,
            'keywords': keywords,
            'reading_time_minutes': reading_time,
            'language_code': 'en',
            'image_url': image_url,
            'sentiment_score': 0.0,
            'share_count': 0,
            'view_count': 0,
            'comment_count': 0
        }
        return article_data

    def process_category(self, category: tuple) -> tuple:
        """
        Process a single category: fetch the page, parse article cards,
        and insert new articles into the database.
        :param category: Tuple of (category_id, link, category_name)
        :return: Tuple (new_count, skipped_count) for this category.
        """
        category_id, link, category_name = category
        logger.info("Processing category: %s", category_name)
        new_count = 0
        skipped_count = 0

        try:
            html_content = self.fetch_page(link)
            soup = BeautifulSoup(html_content, 'html.parser')
            article_cards = []
            for selector in ['div[data-component-name="card"]', 'div.container__item', 'div[data-uri*="card"]']:
                cards = soup.select(selector)
                if cards:
                    article_cards = cards
                    break
            logger.info("Found %d article cards for category %s", len(article_cards), category_name)

            with self.db_context.session() as session:
                for idx, card in enumerate(article_cards, 1):
                    article_data = self.parse_article(card, category_id, link)
                    if article_data:
                        existing = session.query(self.model).filter(
                            self.model.url == article_data['url']
                        ).first()
                        if not existing:
                            logger.info("Adding new article: %s", article_data['title'])
                            article = self.model(**article_data)
                            session.add(article)
                            session.commit()
                            new_count += 1
                        else:
                            # logger.info("Article already exists, skipping: %s", article_data['title'])
                            skipped_count += 1
                session.commit()
                logger.info("Category %s processed successfully", category_name)
        except Exception as e:
            logger.error("Error processing category %s: %s", category_name, e)
        return new_count, skipped_count

    def run(self):
        """
        Main method to process all active categories and print a final report.
        """
        logger.info("Starting CNN HTML parser run")
        total_new = 0
        total_skipped = 0

        with self.db_context.session() as session:
            categories = session.execute(
                text("""
                    SELECT category_id, link, name 
                    FROM pt_cnn.categories 
                    WHERE is_active = true 
                      AND link IS NOT NULL 
                      AND link != '' 
                    ORDER BY category_id;
                """)
            ).fetchall()

        logger.info("Found %d categories", len(categories))
        for category in categories:
            new_count, skipped_count = self.process_category(category)
            total_new += new_count
            total_skipped += skipped_count

        # Print final report.
        final_report = (
            f"\nFinal Report:\n"
            f"----------------------\n"
            f"Newly added articles: {total_new}\n"
            f"Existing (skipped) articles: {total_skipped}\n"
            f"Total processed articles: {total_new + total_skipped}\n"
            f"----------------------"
        )
        logger.info(final_report)
        print(final_report)


def main():
    argparser = argparse.ArgumentParser(description="CNN HTML Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    try:
        portal_id = fetch_portal_id_by_prefix("pt_cnn", env=args.env)
        parser = CNNArticlesParser(portal_id=portal_id, env=args.env)
        parser.run()
    except Exception as e:
        logger.error("Script execution failed: %s", e)
        raise


if __name__ == "__main__":
    main()
