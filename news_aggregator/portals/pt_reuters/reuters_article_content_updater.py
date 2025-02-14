#!/usr/bin/env python3
"""
Reuters Article Updater

This script refactors the original article update functionality into a class-based updater for the pt_reuters portal.
It uses the shared utilities for fetching HTML (with retries and error handling), updating status records, 
and processing the update loop with random sleep intervals.

Extraction Rules for pt_reuters:
  - For each article (fetched from SELECT url FROM pt_reuters.articles), skip pages starting with:
      https://www.reuters.com/pictures/
      https://www.reuters.com/graphics/
  - Attempt to extract the article content using the following methods (in order):
      1. Find a <div> with a class that begins with "article-body__content" (e.g. <div class="article-body__content__17Yit">).
      2. Find a <div> that has both the classes "story-content-container" and "past-first".
      3. Find a <div> with the attribute data-testid="paragraph-0".
      4. Find a <p> with the attribute data-testid="Body".
      5. Find a <div> with a class that contains "arena-liveblog".
  - If none of these elements are found or if the extracted text is empty, mark the article with the error flag "NO_CONTENT".
  - Before storing, clear the existing content in the "content" field and then store the pure text.
  
The script logs a final summary on the number of processed, skipped, errored, and updated articles.
"""

import sys
import os
import argparse
from datetime import datetime, timezone
from bs4 import BeautifulSoup

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from portals.modules.logging_config import setup_script_logging
from db_scripts.models.models import (
    create_portal_category_model,
    create_portal_article_model,
    create_portal_article_status_model
)
from db_scripts.db_context import DatabaseContext

# Import updater utilities from modules/article_updater_utils.py
from portals.modules.article_updater_utils import (
    random_sleep,
    fetch_html,
    update_status_error,
    update_status_success,
    get_articles_to_update,
    log_update_summary
)

# Set up shared logging
logger = setup_script_logging(__file__)

# Dynamically create models for the portal pt_reuters.
ReutersCategory = create_portal_category_model("pt_reuters")
ReutersArticle = create_portal_article_model("pt_reuters")
ReutersArticleStatus = create_portal_article_status_model("pt_reuters")

class ReutersArticleUpdater:
    def __init__(self, env='dev'):
        self.env = env
        self.logger = logger
        self.db_context = DatabaseContext.get_instance(env)
        self.ReutersArticle = ReutersArticle
        self.ReutersArticleStatus = ReutersArticleStatus
        self.counters = {
            "total": 0,
            "up_to_date": 0,
            "to_update": 0,
            "fetched": 0,
            "updated": 0,
            "failed": 0,
            "skipped": 0
        }
        self.error_counts = {}
        # Context for fetch_html to track state (e.g., consecutive 403 errors)
        self.context = {"consecutive_403_count": 0}

    def _extract_article_content(self, soup):
        """
        Try various selectors in order to extract the article's pure text.
        Returns the extracted text (if found and non-empty) or None.
        """
        # 1. <div> with a class that begins with "article-body__content"
        content_div = soup.find(lambda tag: tag.name == 'div' and tag.has_attr('class') and
                                any(cls.startswith("article-body__content") for cls in tag.get('class', [])))
        if content_div:
            text = content_div.get_text(separator="\n").strip()
            if text:
                return text

        # 2. <div> with classes "story-content-container" and "past-first"
        content_div = soup.find(lambda tag: tag.name == 'div' and tag.has_attr('class') and 
                                'story-content-container' in tag.get('class', []) and 
                                'past-first' in tag.get('class', []))
        if content_div:
            text = content_div.get_text(separator="\n").strip()
            if text:
                return text

        # 3. <div data-testid="paragraph-0">
        content_div = soup.find('div', {'data-testid': 'paragraph-0'})
        if content_div:
            text = content_div.get_text(separator="\n").strip()
            if text:
                return text

        # 4. <p data-testid="Body">
        content_p = soup.find('p', {'data-testid': 'Body'})
        if content_p:
            text = content_p.get_text(separator="\n").strip()
            if text:
                return text

        # 5. <div> with class that contains "arena-liveblog"
        content_div = soup.find(lambda tag: tag.name == 'div' and tag.has_attr('class') and
                                'arena-liveblog' in tag.get('class', []))
        if content_div:
            text = content_div.get_text(separator="\n").strip()
            if text:
                return text

        # If no valid content found
        return None

    def update_article(self, article_info):
        """
        Process an individual article update:
          - Skip pages based on URL patterns.
          - Fetch HTML content.
          - Parse and extract article content using Reuters-specific rules.
          - Update the article record (clearing any existing content first).
          - Update or create the status record.
        """
        url = article_info['url']
        self.logger.info(f"Processing article with URL: {url}")

        # Skip pages that should be ignored
        if url.startswith("https://www.reuters.com/pictures/") or url.startswith("https://www.reuters.com/graphics/"):
            self.logger.info(f"Skipping article with URL: {url} (ignored due to pictures/graphics page)")
            self.counters["skipped"] += 1
            return

        fetched_at = datetime.now(timezone.utc)
        html_content, fetch_error = fetch_html(url, self.logger, context=self.context)

        if html_content is None:
            error_type = fetch_error if fetch_error else "UNKNOWN_FETCH"
            with self.db_context.session() as session:
                update_status_error(
                    session,
                    self.ReutersArticleStatus,
                    url,
                    fetched_at,
                    article_info['pub_date'],
                    error_type,
                    status_id=article_info.get('status_id'),
                    logger=self.logger
                )
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            self.counters["failed"] += 1
            return

        soup = BeautifulSoup(html_content, 'html.parser')
        new_content = self._extract_article_content(soup)
        if not new_content:
            error_type = "NO_CONTENT"
            with self.db_context.session() as session:
                update_status_error(
                    session,
                    self.ReutersArticleStatus,
                    url,
                    fetched_at,
                    article_info['pub_date'],
                    error_type,
                    status_id=article_info.get('status_id'),
                    logger=self.logger
                )
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            self.counters["failed"] += 1
            return

        # Update the article record: first clear existing content then store new content.
        with self.db_context.session() as session:
            article_obj = session.query(self.ReutersArticle).filter(
                self.ReutersArticle.article_id == article_info["article_id"]
            ).first()
            if article_obj:
                article_obj.content = ""  # Clear existing content
                article_obj.content = new_content
                self.logger.info(f"Article {url} content updated.")
            else:
                self.logger.error(f"Article {article_info['article_id']} not found in articles table.")
                self.counters["failed"] += 1
                return

            parsed_at = datetime.now(timezone.utc)
            update_status_success(
                session,
                self.ReutersArticleStatus,
                url,
                fetched_at,
                parsed_at,
                article_info['pub_date'],
                status_id=article_info.get('status_id'),
                logger=self.logger
            )

        self.counters["fetched"] += 1
        self.counters["updated"] += 1

    def run(self):
        self.logger.info("Starting Article Content Updater for pt_reuters.")
        # Retrieve articles that require an update.
        with self.db_context.session() as session:
            articles_to_update, summary = get_articles_to_update(
                session, "pt_reuters.articles", "pt_reuters.article_status", self.logger
            )

        self.counters["total"] = summary.get("total", 0)
        self.counters["up_to_date"] = summary.get("up_to_date", 0)
        self.counters["to_update"] = summary.get("to_update", 0)
        self.logger.info(f"Total articles marked for update: {len(articles_to_update)}")

        # Process each article update.
        for idx, article in enumerate(articles_to_update, start=1):
            self.logger.info(f"Processing article {idx}/{len(articles_to_update)} with URL: {article['url']}")
            self.update_article(article)
            random_sleep(self.logger)

        # Log summary statistics.
        log_update_summary(self.logger, self.counters, self.error_counts)

def main():
    parser = argparse.ArgumentParser(description="Reuters Article Updater")
    parser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = parser.parse_args()

    try:
        updater = ReutersArticleUpdater(env=args.env)
        updater.run()
        logger.info("Article content update completed successfully.")
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()
