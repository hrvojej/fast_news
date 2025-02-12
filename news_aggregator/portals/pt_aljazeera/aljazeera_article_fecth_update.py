#!/usr/bin/env python3
"""
Al Jazeera Article Content Updater
-----------------------------------
This script compares the URLs and publication dates in the pt_aljazeera.articles table
with the corresponding records in pt_aljazeera.article_status. For each article where:
  - There is no record in article_status, or
  - The pub_date is different, or
  - Fetched/parsed timestamps are missing,
  
the script will:
  1. Fetch the article’s HTML (waiting a random few seconds between fetches).
  2. Attempt to extract the pure text from the target content element:
       - First, it tries the <div> element with class "wysiwyg wysiwyg--all-content"
         (with aria-live="polite" and aria-atomic="true").
       - If that element is not found, it will try to find the <p> element with class
         "article__subhead u-inline".
     In either case, BeautifulSoup’s get_text() is used to obtain the pure text.
  3. Clear the article’s "content" field before updating it with the new text.
  4. Update the status record accordingly.
  
Error handling includes:
  - Retries (up to 3 attempts) for connection errors.
  - Immediate exit for repeated 403 responses.
  - Logging of distinct errors in a summary at the end.
  
For successful fetch and parsing:
    status = 1, status_type = "OK"
For errors:
    status = 0, with a status_type such as "NO_DIV", "HTTP403", etc.
    
For network errors, parsed_at is left NULL to force a retry.
    
The script logs detailed progress and summary statistics at the end.
"""

import sys
import os
import time
import random
import argparse
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from sqlalchemy import text

# Add package root to path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Import the logging configuration function.
from logging_config import setup_script_logging

# Set up logging for this script.
logger = setup_script_logging(__file__)
logger.info("Script started.")

# Import the dynamic models generator and database context.
from db_scripts.models.models import (
    create_portal_category_model,
    create_portal_article_model,
    create_portal_article_status_model
)

from db_scripts.db_context import DatabaseContext

# Create the dynamic models for the pt_aljazeera schema.
ALJCategory = create_portal_category_model("pt_aljazeera")
ALJArticle = create_portal_article_model("pt_aljazeera")
ALJArticleStatus = create_portal_article_status_model("pt_aljazeera")


class ArticleContentUpdater:
    def __init__(self, env: str = 'dev'):
        self.env = env
        self.db_context = DatabaseContext.get_instance(env)
        self.Article = ALJArticle
        self.ArticleStatus = ALJArticleStatus
        self.consecutive_403_count = 0
        self.error_counts = {}
        self.counters = {
            "total": 0,
            "up_to_date": 0,
            "to_update": 0,
            "fetched": 0,
            "updated": 0,
            "failed": 0
        }

    def random_sleep(self):
        sleep_time = random.uniform(3, 5)
        logger.info(f"Sleeping for {sleep_time:.2f} seconds...")
        time.sleep(sleep_time)

    def fetch_html(self, url: str):
        max_attempts = 3
        attempt = 0
        last_error_type = None
        while attempt < max_attempts:
            try:
                logger.info(f"Fetching URL: {url} (Attempt {attempt + 1})")
                response = requests.get(url, timeout=10)
                self.random_sleep()

                if response.status_code == 200:
                    self.consecutive_403_count = 0
                    return response.content, None
                elif response.status_code == 403:
                    self.consecutive_403_count += 1
                    logger.error(f"Received 403 for {url}. Count: {self.consecutive_403_count}")
                    last_error_type = "HTTP403"
                    if self.consecutive_403_count >= 3:
                        raise Exception("Aborting: 3 consecutive 403 errors encountered.")
                    return None, "HTTP403"
                elif response.status_code == 404:
                    logger.error(f"Received 404 for {url}.")
                    return None, "HTTP404"
                elif response.status_code >= 500:
                    logger.error(f"Server error {response.status_code} for {url}.")
                    return None, "HTTP5xx"
                else:
                    logger.error(f"Unexpected status {response.status_code} for {url}.")
                    return None, "HTTP_ERR"
            except Exception as e:
                attempt += 1
                last_error_type = "NET"
                logger.error(f"Error fetching {url}: {e}. Attempt {attempt} of {max_attempts}.")
                self.random_sleep()
        return None, last_error_type if last_error_type else "NET"

    def update_article_content(self, article_info: dict) -> bool:
        url = article_info["url"]
        article_id = article_info["article_id"]
        pub_date = article_info["pub_date"]
        status_id = article_info.get("status_id")

        logger.info(f"Processing article: {url}")

        html_content, fetch_error = self.fetch_html(url)
        fetched_time = datetime.now(timezone.utc)

        if html_content is None:
            error_type = fetch_error or "UNKNOWN_FETCH"
            parsed_time = None if error_type == "NET" else datetime.now(timezone.utc)
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            logger.error(f"Failed to fetch content for {url}: {error_type}")
            try:
                with self.db_context.session() as session:
                    if status_id:
                        status_obj = session.query(self.ArticleStatus).filter(
                            self.ArticleStatus.status_id == status_id
                        ).first()
                        if status_obj:
                            status_obj.fetched_at = fetched_time
                            status_obj.parsed_at = parsed_time
                            status_obj.pub_date = pub_date
                            status_obj.status = False
                            status_obj.status_type = error_type
                    else:
                        new_status = self.ArticleStatus(
                            url=url,
                            fetched_at=fetched_time,
                            parsed_at=parsed_time,
                            pub_date=pub_date,
                            status=False,
                            status_type=error_type
                        )
                        session.add(new_status)
            except Exception as e:
                logger.error(f"Error updating status for {url}: {e}")
            self.counters["failed"] += 1
            return False

        # Parse the HTML and extract content.
        soup = BeautifulSoup(html_content, 'html.parser')
        # First attempt: look for the primary div element.
        content_div = soup.find('div', {
            "class": "wysiwyg wysiwyg--all-content",
            "aria-live": "polite",
            "aria-atomic": "true"
        })
        if not content_div:
            logger.info(f"Primary content div not found for {url}. Attempting fallback extraction from <p class='article__subhead u-inline'>")
            # Fallback: try to find the <p> element with the given class.
            content_div = soup.find('p', {"class": "article__subhead u-inline"})
        if not content_div:
            error_type = "NO_DIV"
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            logger.error(f"Target content element not found for {url} even after fallback.")
            parsed_time = datetime.now(timezone.utc)
            try:
                with self.db_context.session() as session:
                    if status_id:
                        status_obj = session.query(self.ArticleStatus).filter(
                            self.ArticleStatus.status_id == status_id
                        ).first()
                        if status_obj:
                            status_obj.fetched_at = fetched_time
                            status_obj.parsed_at = parsed_time
                            status_obj.pub_date = pub_date
                            status_obj.status = False
                            status_obj.status_type = error_type
                    else:
                        new_status = self.ArticleStatus(
                            url=url,
                            fetched_at=fetched_time,
                            parsed_at=parsed_time,
                            pub_date=pub_date,
                            status=False,
                            status_type=error_type
                        )
                        session.add(new_status)
            except Exception as e:
                logger.error(f"Error updating status for {url}: {e}")
            self.counters["failed"] += 1
            return False

        new_content = content_div.get_text(separator="\n").strip()
        if not new_content:
            error_type = "EMPTY_CONTENT"
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            logger.error(f"Extracted content is empty for {url}.")
            parsed_time = datetime.now(timezone.utc)
            try:
                with self.db_context.session() as session:
                    if status_id:
                        status_obj = session.query(self.ArticleStatus).filter(
                            self.ArticleStatus.status_id == status_id
                        ).first()
                        if status_obj:
                            status_obj.fetched_at = fetched_time
                            status_obj.parsed_at = parsed_time
                            status_obj.pub_date = pub_date
                            status_obj.status = False
                            status_obj.status_type = error_type
                    else:
                        new_status = self.ArticleStatus(
                            url=url,
                            fetched_at=fetched_time,
                            parsed_at=parsed_time,
                            pub_date=pub_date,
                            status=False,
                            status_type=error_type
                        )
                        session.add(new_status)
            except Exception as e:
                logger.error(f"Error updating status for {url}: {e}")
            self.counters["failed"] += 1
            return False

        # Update the article: first clear the content field, then store the new content.
        try:
            with self.db_context.session() as session:
                article_obj = session.query(self.Article).filter(
                    self.Article.article_id == article_id
                ).first()
                if article_obj:
                    article_obj.content = ""  # Clear the field
                    article_obj.content = new_content
                    logger.info(f"Article content updated for {url}.")
                else:
                    logger.error(f"Article {url} not found in the articles table.")
                    self.counters["failed"] += 1
                    return False

                # Update or create the status record with a success status.
                parsed_time = datetime.now(timezone.utc)
                if status_id:
                    status_obj = session.query(self.ArticleStatus).filter(
                        self.ArticleStatus.status_id == status_id
                    ).first()
                    if status_obj:
                        status_obj.fetched_at = fetched_time
                        status_obj.parsed_at = parsed_time
                        status_obj.pub_date = pub_date
                        status_obj.status = True
                        status_obj.status_type = "OK"
                        logger.info(f"Status record {status_id} updated as OK.")
                    else:
                        logger.error(f"Status record {status_id} not found for {url}.")
                        self.counters["failed"] += 1
                        return False
                else:
                    new_status = self.ArticleStatus(
                        url=url,
                        fetched_at=fetched_time,
                        parsed_at=parsed_time,
                        pub_date=pub_date,
                        status=True,
                        status_type="OK"
                    )
                    session.add(new_status)
                    logger.info(f"New status record created for {url} with OK status.")
            self.counters["updated"] += 1
            return True
        except Exception as e:
            logger.error(f"Error updating article {url}: {e}")
            self.counters["failed"] += 1
            return False

    def run(self):
        logger.info("Starting Article Content Updater for pt_aljazeera.")

        articles_to_update = []
        with self.db_context.session() as session:
            # Retrieve all articles from pt_aljazeera.articles.
            articles = session.execute(
                text("SELECT article_id, url, pub_date FROM pt_aljazeera.articles")
            ).fetchall()
            logger.info(f"Total articles: {len(articles)}")
            
            # Retrieve status records from pt_aljazeera.article_status.
            status_records = session.execute(
                text("SELECT status_id, url, pub_date, fetched_at, parsed_at, status_type FROM pt_aljazeera.article_status")
            ).fetchall()
            logger.info(f"Total status records: {len(status_records)}")

            # Build a lookup dictionary for status records keyed by URL.
            status_dict = {record.url: record for record in status_records}

            for article in articles:
                self.counters["total"] += 1
                if not article.url:
                    logger.info(f"Article {article.article_id} has no URL. Skipping.")
                    continue

                status_record = status_dict.get(article.url)
                if status_record is None:
                    logger.info(f"Article {article.article_id} with URL {article.url} has no status record. Marking for update.")
                    articles_to_update.append({
                        "article_id": article.article_id,
                        "url": article.url,
                        "pub_date": article.pub_date,
                        "status_id": None
                    })
                else:
                    if (article.pub_date != status_record.pub_date or
                        status_record.fetched_at is None or
                        status_record.parsed_at is None):
                        logger.info(f"Article {article.article_id} requires update.")
                        articles_to_update.append({
                            "article_id": article.article_id,
                            "url": article.url,
                            "pub_date": article.pub_date,
                            "status_id": status_record.status_id
                        })
                    else:
                        self.counters["up_to_date"] += 1

        self.counters["to_update"] = len(articles_to_update)
        logger.info(f"Articles marked for update: {len(articles_to_update)}")

        for idx, art in enumerate(articles_to_update, start=1):
            logger.info(f"Updating article {idx} of {len(articles_to_update)}")
            success = self.update_article_content(art)
            if success:
                self.counters["fetched"] += 1
            self.random_sleep()

        logger.info("\nUpdate Summary:")
        logger.info(f"  Total articles processed: {self.counters['total']}")
        logger.info(f"  Articles up-to-date (skipped): {self.counters['up_to_date']}")
        logger.info(f"  Articles marked for update: {self.counters['to_update']}")
        logger.info(f"  Articles where content was fetched: {self.counters['fetched']}")
        logger.info(f"  Articles successfully updated: {self.counters['updated']}")
        logger.info(f"  Articles failed to update: {self.counters['failed']}")

        logger.info("Error Summary:")
        for err_type, count in self.error_counts.items():
            logger.info(f"  {err_type}: {count}")

def main():
    argparser = argparse.ArgumentParser(description="Al Jazeera Article Content Updater")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    try:
        updater = ArticleContentUpdater(env=args.env)
        updater.run()
        logger.info("Article content update completed successfully.")
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()
