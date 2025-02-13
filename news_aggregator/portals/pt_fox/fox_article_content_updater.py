#!/usr/bin/env python3
"""
FOX Article Updater

This script refactors the original article update functionality into a class-based updater for pt_fox.
It leverages common utility functions from the modules/article_updater_utils.py module for:
    - Fetching HTML content with retries and error handling.
    - Updating status records for success or error scenarios.
    - Extracting articles that require update.
    - Processing the update loop with random sleep between updates.
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

# Dynamically create models for the pt_fox schema.
FoxCategory = create_portal_category_model("pt_fox")
FoxArticle = create_portal_article_model("pt_fox")
FoxArticleStatus = create_portal_article_status_model("pt_fox")

class FOXArticleUpdater:
    def __init__(self, env='dev'):
        self.env = env
        self.logger = logger
        self.db_context = DatabaseContext.get_instance(env)
        self.FoxArticle = FoxArticle
        self.FoxArticleStatus = FoxArticleStatus
        self.counters = {
            "total": 0,
            "up_to_date": 0,
            "to_update": 0,
            "fetched": 0,
            "updated": 0,
            "failed": 0
        }
        self.error_counts = {}
        # Context for fetch_html to track state (e.g., consecutive 403 errors)
        self.context = {"consecutive_403_count": 0}

    def update_article(self, article_info):
        """
        Process an individual article update:
            - Fetch HTML content.
            - Parse and extract article content from <div class="article-body">.
            - Clear the current content field.
            - Update the article record.
            - Update or create the status record.
        """
        self.logger.info(f"Processing article with URL: {article_info['url']}")
        fetched_at = datetime.now(timezone.utc)
        html_content, fetch_error = fetch_html(article_info['url'], self.logger, context=self.context)

        if html_content is None:
            error_type = fetch_error if fetch_error else "UNKNOWN_FETCH"
            with self.db_context.session() as session:
                update_status_error(
                    session,
                    self.FoxArticleStatus,
                    article_info['url'],
                    fetched_at,
                    article_info['pub_date'],
                    error_type,
                    status_id=article_info.get('status_id'),
                    logger=self.logger
                )
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            self.counters["failed"] += 1
            return False

        soup = BeautifulSoup(html_content, 'html.parser')
        # Locate the target element based on the extraction rules.
        article_div = soup.find('div', class_='article-body')
        if not article_div:
            error_type = "NO_DIV"
            with self.db_context.session() as session:
                update_status_error(
                    session,
                    self.FoxArticleStatus,
                    article_info['url'],
                    fetched_at,
                    article_info['pub_date'],
                    error_type,
                    status_id=article_info.get('status_id'),
                    logger=self.logger
                )
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            self.counters["failed"] += 1
            return False

        new_content = article_div.get_text(separator="\n").strip()
        if not new_content:
            error_type = "EMPTY_CONTENT"
            with self.db_context.session() as session:
                update_status_error(
                    session,
                    self.FoxArticleStatus,
                    article_info['url'],
                    fetched_at,
                    article_info['pub_date'],
                    error_type,
                    status_id=article_info.get('status_id'),
                    logger=self.logger
                )
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            self.counters["failed"] += 1
            return False

        # Update the article record: first clear existing content, then update.
        with self.db_context.session() as session:
            article_obj = session.query(self.FoxArticle).filter(
                self.FoxArticle.article_id == article_info["article_id"]
            ).first()
            if article_obj:
                # Explicitly clear the existing content before updating.
                article_obj.content = ""
                article_obj.content = new_content
                self.logger.info(f"Article {article_info['url']} content updated.")
            else:
                self.logger.info(f"Article {article_info['article_id']} not found in articles table.")
                self.counters["failed"] += 1
                return False

            parsed_at = datetime.now(timezone.utc)
            update_status_success(
                session,
                self.FoxArticleStatus,
                article_info['url'],
                fetched_at,
                parsed_at,
                article_info['pub_date'],
                status_id=article_info.get('status_id'),
                logger=self.logger
            )

        self.counters["fetched"] += 1
        self.counters["updated"] += 1
        return True

    def run(self):
        self.logger.info("Starting Article Content Updater for pt_fox.")
        # Retrieve articles that require an update.
        with self.db_context.session() as session:
            articles_to_update, summary = get_articles_to_update(
                session,
                "pt_fox.articles",
                "pt_fox.article_status",
                self.logger
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
    parser = argparse.ArgumentParser(description="FOX Article Updater")
    parser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = parser.parse_args()

    try:
        updater = FOXArticleUpdater(env=args.env)
        updater.run()
        logger.info("Article content update completed successfully.")
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()
