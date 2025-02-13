#!/usr/bin/env python3
"""
BBC Article Content Updater for pt_bbc

This script refactors the original pt_bbc article content updater into a class-based updater.
It leverages common utility functions from the modules/article_updater_utils.py module for:
    - Fetching HTML content with retries and error handling.
    - Updating status records for success or error scenarios.
    - Extracting articles that require update.
    - Processing the update loop with random sleep between updates.

Skip rules and extraction logic specific to BBC are maintained.
"""

import sys
import os
import argparse
from datetime import datetime, timezone
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Add package root to path.
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from portals.modules.logging_config import setup_script_logging

logger = setup_script_logging(__file__)

from db_scripts.models.models import (
    create_portal_category_model,
    create_portal_article_model,
    create_portal_article_status_model
)
from db_scripts.db_context import DatabaseContext

# Import updater utilities.
from portals.modules.article_updater_utils import (
    random_sleep,
    fetch_html,
    update_status_error,
    update_status_success,
    get_articles_to_update,
    log_update_summary
)

# Dynamically create models for the pt_bbc schema.
BBCCategory = create_portal_category_model("pt_bbc")
BBCArticle = create_portal_article_model("pt_bbc")
BBCArticleStatus = create_portal_article_status_model("pt_bbc")


class BBCArticleUpdater:
    def __init__(self, env='dev'):
        self.env = env
        self.logger = logger
        self.db_context = DatabaseContext.get_instance(env)
        self.BBCArticle = BBCArticle
        self.BBCArticleStatus = BBCArticleStatus
        self.counters = {
            "total": 0,
            "up_to_date": 0,
            "to_update": 0,
            "fetched": 0,
            "updated": 0,
            "failed": 0
        }
        self.error_counts = {}
        # Context for fetch_html (e.g., tracking consecutive 403 errors)
        self.context = {"consecutive_403_count": 0}

    def should_skip_url(self, url: str) -> bool:
        """
        Returns True if the URL meets any of the skip criteria.
        """
        if (url.startswith("https://www.bbc.co.uk/bitesize/") or
            url.startswith("https://www.bbc.co.uk/iplayer/") or
            url.startswith("https://www.bbc.com/audio/")):
            return True

        if "/live/" in url:
            return True

        parsed = urlparse(url)
        if parsed.netloc == "www.bbc.co.uk" and parsed.path.startswith("/news/"):
            parts = parsed.path.split('/')
            if len(parts) >= 3 and parts[2].isdigit():
                return True

        return False

    def update_article(self, article_info: dict) -> bool:
        """
        Process an individual article update:
          - If the URL should be skipped, clear its content and update status as SKIP.
          - Otherwise, fetch the HTML, extract the article content (using BBC-specific rules),
            update the article record, and record success or error in the status table.
        """
        url = article_info["url"]
        self.logger.info(f"Processing article with URL: {url}")
        pub_date = article_info["pub_date"]

        # Check for skip conditions.
        if self.should_skip_url(url):
            self.logger.info(f"URL {url} meets skip criteria. Clearing content and marking as SKIP.")
            fetched_at = datetime.now(timezone.utc)
            # Update the article record by clearing content.
            try:
                with self.db_context.session() as session:
                    article_obj = session.query(self.BBCArticle).filter(
                        self.BBCArticle.article_id == article_info["article_id"]
                    ).first()
                    if article_obj:
                        article_obj.content = ""
                    else:
                        self.logger.error(f"Article {url} not found in DB during skip update.")
                        self.counters["failed"] += 1
                        return False
                    update_status_error(
                        session,
                        self.BBCArticleStatus,
                        url,
                        fetched_at,
                        pub_date,
                        "SKIP",
                        status_id=article_info.get("status_id"),
                        logger=self.logger
                    )
            except Exception as e:
                self.logger.error(f"Error updating skip status for {url}: {e}")
                self.counters["failed"] += 1
                return False
            return True

        # Not skipped – attempt to fetch HTML.
        fetched_at = datetime.now(timezone.utc)
        html_content, fetch_err = fetch_html(url, self.logger, context=self.context)
        if html_content is None:
            error_type = fetch_err if fetch_err else "UNKNOWN_FETCH"
            try:
                with self.db_context.session() as session:
                    update_status_error(
                        session,
                        self.BBCArticleStatus,
                        url,
                        fetched_at,
                        pub_date,
                        error_type,
                        status_id=article_info.get("status_id"),
                        logger=self.logger
                    )
            except Exception as e:
                self.logger.error(f"Error updating status for {url} with error {error_type}: {e}")
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            self.counters["failed"] += 1
            return False

        # Parse HTML and extract content using BBC-specific extraction rules.
        soup = BeautifulSoup(html_content, 'html.parser')
        if url.startswith("https://www.bbc.com/news/videos/"):
            self.logger.info(f"Using video extraction rule for URL: {url}")
            target_element = soup.find('div', {'data-testid': 'video-page-video-section'})
        else:
            self.logger.info(f"Using default extraction rule (#main-content > article) for URL: {url}")
            target_element = soup.select_one("#main-content > article")

        if not target_element:
            error_type = "NO_DIV"
            try:
                with self.db_context.session() as session:
                    update_status_error(
                        session,
                        self.BBCArticleStatus,
                        url,
                        fetched_at,
                        pub_date,
                        error_type,
                        status_id=article_info.get("status_id"),
                        logger=self.logger
                    )
            except Exception as e:
                self.logger.error(f"Error updating status for {url} with error {error_type}: {e}")
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            self.counters["failed"] += 1
            return False

        new_content = target_element.get_text(separator="\n").strip()
        if not new_content:
            error_type = "EMPTY_CONTENT"
            try:
                with self.db_context.session() as session:
                    update_status_error(
                        session,
                        self.BBCArticleStatus,
                        url,
                        fetched_at,
                        pub_date,
                        error_type,
                        status_id=article_info.get("status_id"),
                        logger=self.logger
                    )
            except Exception as e:
                self.logger.error(f"Error updating status for {url} with error {error_type}: {e}")
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            self.counters["failed"] += 1
            return False

        # Update the article record and mark success.
        try:
            with self.db_context.session() as session:
                article_obj = session.query(self.BBCArticle).filter(
                    self.BBCArticle.article_id == article_info["article_id"]
                ).first()
                if article_obj:
                    article_obj.content = new_content
                    self.logger.info(f"Article {url} content updated.")
                else:
                    self.logger.error(f"Article {url} not found in DB during update.")
                    self.counters["failed"] += 1
                    return False
                parsed_at = datetime.now(timezone.utc)
                update_status_success(
                    session,
                    self.BBCArticleStatus,
                    url,
                    fetched_at,
                    parsed_at,
                    pub_date,
                    status_id=article_info.get("status_id"),
                    logger=self.logger
                )
        except Exception as e:
            self.logger.error(f"Error updating article {url}: {e}")
            self.counters["failed"] += 1
            return False

        self.counters["fetched"] += 1
        self.counters["updated"] += 1
        return True

    def run(self):
        self.logger.info("Starting Article Content Updater for pt_bbc.")
        # Retrieve articles that require update.
        try:
            with self.db_context.session() as session:
                articles_to_update, summary = get_articles_to_update(
                    session,
                    "pt_bbc.articles",
                    "pt_bbc.article_status",
                    self.logger
                )
        except Exception as e:
            self.logger.error(f"Error retrieving articles to update: {e}")
            return

        self.counters["total"] = summary.get("total", 0)
        self.counters["up_to_date"] = summary.get("up_to_date", 0)
        self.counters["to_update"] = summary.get("to_update", 0)
        self.logger.info(f"Total articles marked for update: {len(articles_to_update)}")

        # Process each article.
        for idx, article in enumerate(articles_to_update, start=1):
            self.logger.info(f"Processing article {idx}/{len(articles_to_update)} with URL: {article['url']}")
            self.update_article(article)
            random_sleep(self.logger)

        # Log summary statistics.
        log_update_summary(self.logger, self.counters, self.error_counts)


def main():
    parser = argparse.ArgumentParser(description="BBC Article Content Updater for pt_bbc")
    parser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = parser.parse_args()

    try:
        updater = BBCArticleUpdater(env=args.env)
        updater.run()
        logger.info("Article content update completed successfully.")
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
