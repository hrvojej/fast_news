#!/usr/bin/env python3
"""
BBC Article Content Updater for pt_bbc Schema
----------------------------------------------
This script compares the URLs and publication dates in the pt_bbc.articles table
with the corresponding records in pt_bbc.article_status. For each article where:
  - There is no record in article_status (i.e. initially the table is empty), or
  - The URL exists in both tables but the pub_date is different, or
  - The URL exists and pub_date is the same but one or both of fetched_at/parsed_at are missing,
  
the script will:
  1. Check if the URL should be skipped (see below).
  2. If not skipped, fetch the article’s HTML (waiting a random 3–5 seconds after every fetch attempt).
  3. Extract the plain text according to these rules:
       - For URLs starting with "https://www.bbc.com/news/videos/":
             extract text from the <div data-testid="video-page-video-section">.
       - For URLs starting with "https://www.bbc.com/sport" or "https://www.bbc.com/news/"
         (or similar categories):
             extract text from the element selected by "#main-content > article".
  4. Clear any existing content in the article’s "content" field and update it with the new pure text.
  5. Update (or create) the status record:
       - On success, status = 1 and status_type = "OK".
       - On extraction errors (no target element found or empty text), status = 0 and status_type = "NO_DIV" or "EMPTY_CONTENT".
       - On HTTP or network errors, appropriate error codes are used (e.g. "HTTP403", "NET", etc.).
       - For skipped URLs (per the rules below), status = 0 and status_type = "SKIP".

Skip rules – before attempting any HTTP fetch:
  - If the URL starts with:
      • "https://www.bbc.co.uk/bitesize/"
      • "https://www.bbc.co.uk/iplayer/"
      • "https://www.bbc.com/audio/"
  - If the URL contains "/live/" anywhere.
  - If the URL is of the form "https://www.bbc.co.uk/news/<number>" (i.e. missing a category/article slug).
  
In all cases the script logs detailed progress and a summary at the end.
"""

import sys
import os
import time
import random
import argparse
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from sqlalchemy import text

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)
    
# Import the logging configuration function.
from logging_config import setup_script_logging

# Set up logging for this script.
logger = setup_script_logging(__file__)
logger.info("pt_bbc Article Content Updater script started.")

from db_scripts.models.models import (
    create_portal_category_model,
    create_portal_article_model,
    create_portal_article_status_model
)

from db_scripts.db_context import DatabaseContext

# Create the dynamic models for the pt_bbc schema.
BBCCategory = create_portal_category_model("pt_bbc")
BBCArticle = create_portal_article_model("pt_bbc")
BBCArticleStatus = create_portal_article_status_model("pt_bbc")


class ArticleContentUpdater:
    def __init__(self, env: str = 'dev'):
        self.env = env
        self.db_context = DatabaseContext.get_instance(env)
        self.BBCArticle = BBCArticle
        self.BBCArticleStatus = BBCArticleStatus
        self.consecutive_403_count = 0
        self.error_counts = {}  # To record counts for each error type.
        self.counters = {
            "total": 0,               # Total articles processed from the articles table
            "up_to_date": 0,          # Articles skipped because they are already up-to-date
            "to_update": 0,           # Articles marked for update (or needing a new status record)
            "fetched": 0,             # Articles for which HTML was fetched and parsed
            "updated": 0,             # Articles successfully updated in the DB
            "failed": 0               # Articles that failed during update
        }

    def random_sleep(self):
        sleep_time = random.uniform(3, 5)
        logger.info(f"Sleeping for {sleep_time:.2f} seconds...")
        time.sleep(sleep_time)

    def fetch_html(self, url: str):
        """
        Attempts to fetch the HTML content for the given URL.
        Uses up to 3 attempts for connection errors.
        If the HTTP response status code is 403, 404 or >=500, no retries are attempted.
        After each attempt (successful or error), a random sleep is performed.
        If more than 3 consecutive 403 responses occur, the script aborts.
        
        Returns:
            A tuple: (html_content or None, error_type or None)
        """
        max_attempts = 3
        attempt = 0
        last_error_type = None
        while attempt < max_attempts:
            try:
                logger.info(f"Fetching URL: {url} (Attempt {attempt + 1})")
                response = requests.get(url, timeout=10)
                self.random_sleep()  # Sleep after every attempt

                if response.status_code == 200:
                    self.consecutive_403_count = 0  # Reset on success
                    return response.content, None
                elif response.status_code == 403:
                    self.consecutive_403_count += 1
                    logger.error(f"Received 403 for {url}. Consecutive 403 count: {self.consecutive_403_count}")
                    last_error_type = "HTTP403"
                    if self.consecutive_403_count >= 3:
                        raise Exception("Aborting: 3 consecutive 403 errors encountered.")
                    return None, "HTTP403"
                elif response.status_code == 404:
                    logger.error(f"Received 404 for {url}. Skipping this URL.")
                    return None, "HTTP404"
                elif response.status_code >= 500:
                    logger.error(f"Server error {response.status_code} for {url}. Skipping this URL.")
                    return None, "HTTP5xx"
                else:
                    logger.error(f"Unexpected status code {response.status_code} for {url}. Skipping.")
                    return None, "HTTP_ERR"

            except Exception as e:
                attempt += 1
                last_error_type = "NET"
                logger.error(f"Error fetching {url}: {e}. Attempt {attempt} of {max_attempts}.")
                self.random_sleep()

        # All attempts failed: return network error.
        return None, last_error_type if last_error_type else "NET"

    def should_skip_url(self, url: str) -> bool:
        """
        Determines whether a given URL should be skipped based on the rules.
        """
        # Rule 1: Skip specific domains or paths.
        if (url.startswith("https://www.bbc.co.uk/bitesize/") or
            url.startswith("https://www.bbc.co.uk/iplayer/") or
            url.startswith("https://www.bbc.com/audio/")):
            return True

        # Rule 2: Skip any URL that contains '/live/'.
        if "/live/" in url:
            return True

        # Rule 3: For URLs like "https://www.bbc.co.uk/news/10628994" (i.e. no category/article slug).
        parsed = urlparse(url)
        if parsed.netloc == "www.bbc.co.uk" and parsed.path.startswith("/news/"):
            parts = parsed.path.split('/')
            # Expecting parts like ['', 'news', '10628994'] – if the third part is numeric, skip.
            if len(parts) >= 3 and parts[2].isdigit():
                return True

        return False

    def update_status_record(self, session, url: str, pub_date, fetched_time, parsed_time, status_flag: bool, status_type: str, status_id=None):
        """
        Updates an existing status record (if status_id is provided) or inserts a new one.
        """
        if status_id:
            status_obj = session.query(self.BBCArticleStatus).filter(
                self.BBCArticleStatus.status_id == status_id
            ).first()
            if status_obj:
                status_obj.fetched_at = fetched_time
                status_obj.parsed_at = parsed_time
                status_obj.pub_date = pub_date
                status_obj.status = status_flag
                status_obj.status_type = status_type
                logger.info(f"Status record {status_id} updated with status_type {status_type}.")
        else:
            new_status = self.BBCArticleStatus(
                url=url,
                fetched_at=fetched_time,
                parsed_at=parsed_time,
                pub_date=pub_date,
                status=status_flag,
                status_type=status_type
            )
            session.add(new_status)
            logger.info(f"New status record created for article {url} with status_type {status_type}.")

    def update_article_content(self, article_info: dict) -> bool:
        """
        For a given article (specified by article_id, url, pub_date, and possibly a status_id),
        update the article’s content field (by first clearing any existing content) and update or create
        the corresponding status record.
        
        Implements additional rules for pt_bbc:
          - Skips URLs that match the skip criteria (status_type "SKIP").
          - For URLs starting with "https://www.bbc.com/news/videos/", extracts text from the
            <div data-testid="video-page-video-section"> element.
          - For other (non-skipped) URLs (e.g. bbc.com/sport or bbc.com/news), extracts text from the element
            selected by "#main-content > article".
          
        Returns True if the update was successful (or skipped) and False otherwise.
        """
        url = article_info["url"]
        article_id = article_info["article_id"]
        pub_date = article_info["pub_date"]
        status_id = article_info.get("status_id")  # May be None if no status record exists

        logger.info(f"Processing article with URL: {url}")

        # Check if the URL should be skipped.
        if self.should_skip_url(url):
            logger.info(f"URL {url} meets skip criteria. Skipping content fetch and updating status as SKIP.")
            fetched_time = datetime.now(timezone.utc)
            parsed_time = datetime.now(timezone.utc)
            try:
                with self.db_context.session() as session:
                    # Clear the article content.
                    article_obj = session.query(self.BBCArticle).filter(
                        self.BBCArticle.article_id == article_id
                    ).first()
                    if article_obj:
                        article_obj.content = ""  # Clear existing content.
                        logger.info(f"Article {url} content cleared due to skip rule.")
                    else:
                        logger.error(f"Article {url} not found in the articles table during skip update.")
                        self.counters["failed"] += 1
                        return False

                    self.update_status_record(
                        session,
                        url=url,
                        pub_date=pub_date,
                        fetched_time=fetched_time,
                        parsed_time=parsed_time,
                        status_flag=False,
                        status_type="SKIP",
                        status_id=status_id
                    )
            except Exception as e:
                logger.error(f"Error updating status record for SKIP article {url}: {e}")
                self.counters["failed"] += 1
                return False
            return True

        # Attempt to fetch the HTML.
        html_content, fetch_error = self.fetch_html(url)
        fetched_time = datetime.now(timezone.utc)

        # If no HTML content was fetched, update status record with the error.
        if html_content is None:
            error_type = fetch_error if fetch_error else "UNKNOWN_FETCH"
            parsed_time = None if error_type == "NET" else datetime.now(timezone.utc)
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            logger.error(f"Failed to fetch content for article {url} with error {error_type}.")
            try:
                with self.db_context.session() as session:
                    self.update_status_record(
                        session,
                        url=url,
                        pub_date=pub_date,
                        fetched_time=fetched_time,
                        parsed_time=parsed_time,
                        status_flag=False,
                        status_type=error_type,
                        status_id=status_id
                    )
            except Exception as e:
                logger.error(f"Error updating status record for article {url} with error {error_type}: {e}")
            self.counters["failed"] += 1
            return False

        # Parse the HTML and extract content using the appropriate rule.
        soup = BeautifulSoup(html_content, 'html.parser')
        if url.startswith("https://www.bbc.com/news/videos/"):
            logger.info(f"Using video extraction rule for URL: {url}")
            content_element = soup.find('div', {'data-testid': 'video-page-video-section'})
        else:
            logger.info(f"Using default extraction rule (#main-content > article) for URL: {url}")
            content_element = soup.select_one("#main-content > article")

        if not content_element:
            error_type = "NO_DIV"
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            logger.error(f"Could not find the target element for article {url}.")
            parsed_time = datetime.now(timezone.utc)
            try:
                with self.db_context.session() as session:
                    self.update_status_record(
                        session,
                        url=url,
                        pub_date=pub_date,
                        fetched_time=fetched_time,
                        parsed_time=parsed_time,
                        status_flag=False,
                        status_type=error_type,
                        status_id=status_id
                    )
            except Exception as e:
                logger.error(f"Error updating status record for article {url} with error {error_type}: {e}")
            self.counters["failed"] += 1
            return False

        new_content = content_element.get_text(separator="\n").strip()
        if not new_content:
            error_type = "EMPTY_CONTENT"
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            logger.error(f"Extracted content is empty for article {url}.")
            parsed_time = datetime.now(timezone.utc)
            try:
                with self.db_context.session() as session:
                    self.update_status_record(
                        session,
                        url=url,
                        pub_date=pub_date,
                        fetched_time=fetched_time,
                        parsed_time=parsed_time,
                        status_flag=False,
                        status_type=error_type,
                        status_id=status_id
                    )
            except Exception as e:
                logger.error(f"Error updating status record for article {url} with error {error_type}: {e}")
            self.counters["failed"] += 1
            return False

        # If extraction is successful, update the article’s content (clear any previous content first).
        try:
            with self.db_context.session() as session:
                article_obj = session.query(self.BBCArticle).filter(
                    self.BBCArticle.article_id == article_id
                ).first()
                if article_obj:
                    # Clear the content field and update with new content.
                    article_obj.content = ""  
                    article_obj.content = new_content
                    logger.info(f"Article {url} content updated.")
                else:
                    logger.error(f"Article {url} not found in the articles table during update.")
                    self.counters["failed"] += 1
                    return False

                parsed_time = datetime.now(timezone.utc)
                self.update_status_record(
                    session,
                    url=url,
                    pub_date=pub_date,
                    fetched_time=fetched_time,
                    parsed_time=parsed_time,
                    status_flag=True,
                    status_type="OK",
                    status_id=status_id
                )
            self.counters["updated"] += 1
            return True

        except Exception as e:
            logger.error(f"Error updating article {url}: {e}")
            self.counters["failed"] += 1
            return False

    def run(self):
        logger.info("Starting Article Content Updater for pt_bbc.")

        articles_to_update = []
        with self.db_context.session() as session:
            # Get all articles from pt_bbc.articles.
            articles = session.execute(
                text("SELECT article_id, url, pub_date FROM pt_bbc.articles")
            ).fetchall()
            logger.info(f"Total articles in articles table: {len(articles)}")

            # Get all status records from pt_bbc.article_status.
            status_records = session.execute(
                text("SELECT status_id, url, pub_date, fetched_at, parsed_at, status_type FROM pt_bbc.article_status")
            ).fetchall()
            logger.info(f"Total records in article_status table: {len(status_records)}")

            # Build a dictionary keyed by URL.
            status_dict = {record.url: record for record in status_records}

            for article in articles:
                self.counters["total"] += 1

                if not article.url:
                    logger.info(f"Article {article.article_id} has no URL. Skipping.")
                    continue

                status_record = status_dict.get(article.url)  # May be None

                # Mark article for update if:
                #   1. No status record exists.
                #   2. The pub_date is different.
                #   3. fetched_at or parsed_at is missing.
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
                        logger.info(f"Article {article.article_id} requires update (pub_date or fetch status differs).")
                        articles_to_update.append({
                            "article_id": article.article_id,
                            "url": article.url,
                            "pub_date": article.pub_date,
                            "status_id": status_record.status_id
                        })
                    else:
                        self.counters["up_to_date"] += 1

        self.counters["to_update"] = len(articles_to_update)
        logger.info(f"Total articles marked for update: {len(articles_to_update)}")

        # Process each article that needs to be updated.
        for idx, art in enumerate(articles_to_update, start=1):
            logger.info(f"\nArticle {idx}/{len(articles_to_update)}")
            success = self.update_article_content(art)
            if success:
                self.counters["fetched"] += 1
            self.random_sleep()

        # Log summary statistics.
        logger.info("\nUpdate Summary:")
        logger.info(f"  Total articles processed:         {self.counters['total']}")
        logger.info(f"  Articles up-to-date (skipped):      {self.counters['up_to_date']}")
        logger.info(f"  Articles marked for update:         {self.counters['to_update']}")
        logger.info(f"  Articles where content was fetched: {self.counters['fetched']}")
        logger.info(f"  Articles successfully updated:      {self.counters['updated']}")
        logger.info(f"  Articles failed to update:          {self.counters['failed']}")

        # Log error counts by type.
        logger.info("Error Summary:")
        for err_type, count in self.error_counts.items():
            logger.info(f"  {err_type}: {count}")

def main():
    argparser = argparse.ArgumentParser(description="BBC Article Content Updater for pt_bbc")
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
