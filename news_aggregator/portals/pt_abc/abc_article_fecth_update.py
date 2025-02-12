#!/usr/bin/env python3
"""
ABC Article Content Updater
---------------------------
This script compares the URLs and publication dates in the pt_abc.articles table
with the corresponding records in pt_abc.article_status. For each article where:
  - There is no record in article_status (i.e. initially the table is empty), or
  - The URL exists in both tables but the pub_date is different, or
  - The URL exists and pub_date is the same but one or both of fetched_at/parsed_at are missing,
  
the script will:
  1. Fetch the article’s HTML (waiting a random 4–7 seconds after every fetch attempt).
  2. Extract the plain text from the <div> identified by data-testid="prism-article-body".
  3. Update the article’s "content" field in pt_abc.articles.
  4. Update the status record:
       - If a status record already exists, update its fetched_at, parsed_at, and pub_date.
       - If no status record exists, insert a new one with these details.
       
Error handling includes a retry mechanism (up to 3 attempts) for connection errors (except for 403, 404, or 5xx responses) and aborts if more than 3 consecutive 403 responses are encountered.

The script logger.infos detailed progress and summary statistics at the end.
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

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)
    
# Import the logging configuration function.
from logging_config import setup_script_logging

# Set up logging for this script.
logger = setup_script_logging(__file__)
logger.info("Script started.")

from db_scripts.models.models import (
    create_portal_category_model,
    create_portal_article_model,
    create_portal_article_status_model
)

from db_scripts.db_context import DatabaseContext


# Create the dynamic models for the pt_abc schema.
ABCCategory = create_portal_category_model("pt_abc")
ABCArticle = create_portal_article_model("pt_abc")
ABCArticleStatus = create_portal_article_status_model("pt_abc")


class ArticleContentUpdater:
    def __init__(self, env: str = 'dev'):
        self.env = env
        self.db_context = DatabaseContext.get_instance(env)
        self.ABCArticle = ABCArticle
        self.ABCArticleStatus = ABCArticleStatus
        self.consecutive_403_count = 0
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
        """
        max_attempts = 3
        attempt = 0
        while attempt < max_attempts:
            try:
                logger.info(f"Fetching URL: {url} (Attempt {attempt + 1})")
                response = requests.get(url, timeout=10)
                self.random_sleep()  # Sleep after every attempt

                if response.status_code == 200:
                    self.consecutive_403_count = 0  # Reset on success
                    return response.content
                elif response.status_code == 403:
                    self.consecutive_403_count += 1
                    logger.error(f"Received 403 for {url}. Consecutive 403 count: {self.consecutive_403_count}")
                    if self.consecutive_403_count >= 3:
                        raise Exception("Aborting: 3 consecutive 403 errors encountered.")
                    return None
                elif response.status_code == 404:
                    logger.error(f"Received 404 for {url}. Skipping this URL.")
                    return None
                elif response.status_code >= 500:
                    logger.error(f"Server error {response.status_code} for {url}. Skipping this URL.")
                    return None
                else:
                    logger.error(f"Unexpected status code {response.status_code} for {url}. Skipping.")
                    return None

            except Exception as e:
                attempt += 1
                logger.error(f"Error fetching {url}: {e}. Attempt {attempt} of {max_attempts}.")
                self.random_sleep()

        return None  # All attempts failed

    def update_article_content(self, article_info: dict) -> bool:
        """
        For a given article (specified by article_id, url, pub_date, and possibly a status_id),
        fetch the HTML, extract the article text, update the article content, and update or create
        the status record.
        
        Returns True if the update was successful, False otherwise.
        """
        url = article_info["url"]
        article_id = article_info["article_id"]
        pub_date = article_info["pub_date"]
        status_id = article_info.get("status_id")  # May be None if no status record exists

        logger.info(f"Processing article with URL: {url}")

        html_content = self.fetch_html(url)
        if html_content is None:
            logger.info(f"Failed to fetch content for article {url}. Skipping update.")
            self.counters["failed"] += 1
            return False

        # Mark the time when HTML was fetched.
        fetched_time = datetime.now(timezone.utc)

        # Parse the HTML and extract text from the target div.
        soup = BeautifulSoup(html_content, 'html.parser')
        article_div = soup.find('div', {'data-testid': 'prism-article-body'})
        if not article_div:
            logger.info(f"Could not find the target content div for article {url}. Skipping update.")
            self.counters["failed"] += 1
            return False

        new_content = article_div.get_text(separator="\n").strip()
        if not new_content:
            logger.info(f"Extracted content is empty for article {url}. Skipping update.")
            self.counters["failed"] += 1
            return False

        try:
            # Use a new session for updating the article and status.
            with self.db_context.session() as session:
                # Update the article’s content.
                article_obj = session.query(self.ABCArticle).filter(
                    self.ABCArticle.article_id == article_id
                ).first()
                if article_obj:
                    article_obj.content = new_content
                    logger.info(f"Article {url} content updated.")
                else:
                    logger.info(f"Article {url} not found in the articles table during update.")
                    self.counters["failed"] += 1
                    return False

                # Update or insert the corresponding status record.
                if status_id:
                    # Status record exists; update it.
                    status_obj = session.query(self.ABCArticleStatus).filter(
                        self.ABCArticleStatus.status_id == status_id
                    ).first()
                    if status_obj:
                        status_obj.fetched_at = fetched_time
                        status_obj.parsed_at = datetime.now(timezone.utc)
                        status_obj.pub_date = pub_date
                        logger.info(f"Status record {status_id} updated with fetched_at and parsed_at.")
                    else:
                        logger.info(f"Status record {status_id} not found during update. This should not happen.")
                        self.counters["failed"] += 1
                        return False
                else:
                    # No status record exists; insert a new one.
                    new_status = self.ABCArticleStatus(
                        url=url,
                        fetched_at=fetched_time,
                        parsed_at=datetime.now(timezone.utc),
                        pub_date=pub_date
                    )
                    session.add(new_status)
                    logger.info(f"New status record created for article {url}.")

            self.counters["updated"] += 1
            return True

        except Exception as e:
            logger.info(f"Error updating article {url}: {e}")
            self.counters["failed"] += 1
            return False

    def run(self):
        logger.info("Starting Article Content Updater for pt_abc.")

        articles_to_update = []
        with self.db_context.session() as session:
            # Get all articles from pt_abc.articles.
            articles = session.execute(
                text("SELECT article_id, url, pub_date FROM pt_abc.articles")
            ).fetchall()
            logger.info(f"Total articles in articles table: {len(articles)}")

            # Get all status records from pt_abc.article_status.
            status_records = session.execute(
                text("SELECT status_id, url, pub_date, fetched_at, parsed_at FROM pt_abc.article_status")
            ).fetchall()
            logger.info(f"Total records in article_status table: {len(status_records)}")

            # Build a dictionary keyed by URL.
            status_dict = {record.url: record for record in status_records}

            for article in articles:
                self.counters["total"] += 1

                # If the article has no URL, skip it.
                if not article.url:
                    logger.info(f"Article {article.article_id} has no URL. Skipping.")
                    continue

                status_record = status_dict.get(article.url)  # May be None

                # Determine whether the article needs to be fetched:
                # 1. No status record exists (new article – needs fetching).
                # 2. The pub_date is different.
                # 3. Fetched_at or parsed_at is missing.
                if status_record is None:
                    logger.info(f"Article {article.article_id} with URL {article.url} has no status record. Marking for update (new status record will be created).")
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
                        logger.info(f"Article {article.url} is up-to-date. Skipping.")
                        self.counters["up_to_date"] += 1

        self.counters["to_update"] = len(articles_to_update)
        logger.info(f"Total articles marked for update: {len(articles_to_update)}")

        # Process each article that needs to be updated.
        for idx, art in enumerate(articles_to_update, start=1):
            # logger.info progress for each article.
            logger.info(f"\nArticle {idx}/{len(articles_to_update)}")
            success = self.update_article_content(art)
            if success:
                self.counters["fetched"] += 1
            self.random_sleep()

        # logger.info summary statistics.
        logger.info("\nUpdate Summary:")
        logger.info(f"  Total articles processed:         {self.counters['total']}")
        logger.info(f"  Articles up-to-date (skipped):      {self.counters['up_to_date']}")
        logger.info(f"  Articles marked for update:         {self.counters['to_update']}")
        logger.info(f"  Articles where content was fetched: {self.counters['fetched']}")
        logger.info(f"  Articles successfully updated:      {self.counters['updated']}")
        logger.info(f"  Articles failed to update:          {self.counters['failed']}")


def main():
    argparser = argparse.ArgumentParser(description="ABC Article Content Updater")
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
        logger.info(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
