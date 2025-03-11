# Full module name: fast_news.news_aggregator.portals.modules.article_updater_utils
"""
Utility functions for the Article Updater.

This module provides helper functions to:
  - Sleep for a random duration.
  - Fetch HTML content from a URL with retries and error handling.
  - Update or create status records in the database for both error and success cases.
  - Extract articles that require an update from the database.
  - Process a loop of article updates.
  - Log summary statistics after processing updates.
"""

import time
import random
import requests
from datetime import datetime, timezone
from sqlalchemy import text

def random_sleep(logger, min_seconds=3, max_seconds=5):
    """
    Sleep for a random duration between min_seconds and max_seconds.

    Args:
        logger: Logger instance for logging the sleep time.
        min_seconds (float): Minimum seconds to sleep.
        max_seconds (float): Maximum seconds to sleep.
    """
    sleep_time = random.uniform(min_seconds, max_seconds)
    logger.info(f"Sleeping for {sleep_time:.2f} seconds...")
    time.sleep(sleep_time)

def fetch_html(url, logger, sleep_func=random_sleep, context=None, max_attempts=3, timeout=10):
    """
    Attempts to fetch the HTML content for the given URL with retries.

    Uses up to max_attempts for connection errors. For HTTP errors (e.g., 403, 404, 5xx),
    no retries are performed (except for network errors). After each attempt (successful or error),
    a random sleep is performed.

    A context dictionary is used to keep track of stateful counters such as consecutive 403 errors.

    Args:
        url (str): The URL to fetch.
        logger: Logger instance for logging.
        sleep_func (callable): Function to perform sleeping. Defaults to random_sleep.
        context (dict): Dictionary to maintain state (e.g., {"consecutive_403_count": 0}).
        max_attempts (int): Maximum number of attempts for network errors.
        timeout (int): Request timeout in seconds.

    Returns:
        tuple: (html_content or None, error_type or None)
            - On success: (content, None)
            - On error: (None, error_type)
    """
    if context is None:
        context = {"consecutive_403_count": 0}
    attempt = 0
    last_error_type = None

    while attempt < max_attempts:
        try:
            logger.info(f"Fetching URL: {url} (Attempt {attempt + 1})")
            response = requests.get(url, timeout=timeout)
            sleep_func(logger)
            
            if response.status_code == 200:
                context["consecutive_403_count"] = 0
                return response.content, None
            elif response.status_code == 403:
                context["consecutive_403_count"] += 1
                logger.error(f"Received 403 for {url}. Consecutive 403 count: {context['consecutive_403_count']}")
                last_error_type = "HTTP403"
                if context["consecutive_403_count"] >= 3:
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
            sleep_func(logger)
    
    return None, last_error_type if last_error_type else "NET"

def update_status_error(session, status_model, url, fetched_at, pub_date, error_type, status_id=None, logger=None):
    parsed_at = None if error_type == "NET" else datetime.now(timezone.utc)
    if logger:
        logger.info(f"Updating status for {url} with error {error_type}.")

    # Truncate or map error_type to ensure it's no longer than 10 characters.
    # Option 1: Simple truncation:
    if len(error_type) > 10:
        error_type = error_type[:10]
    
    # Option 2: Use a mapping (uncomment and adjust as needed):
    # error_mapping = {
    #     "User abort, call stop() when calling Runtime.evaluate": "USR_ABORT",
    #     "HTTP403": "HTTP403",
    #     "HTTP404": "HTTP404",
    #     "NO_CONTENT": "NO_CONTENT",
    #     # add additional mappings as necessary
    # }
    # error_type = error_mapping.get(error_type, error_type[:10])
    
    if status_id:
        status_obj = session.query(status_model).filter(status_model.status_id == status_id).first()
        if status_obj:
            status_obj.fetched_at = fetched_at
            status_obj.parsed_at = parsed_at
            status_obj.pub_date = pub_date
            status_obj.status = False
            status_obj.status_type = error_type
        else:
            if logger:
                logger.info(f"Status record {status_id} not found. Creating new error status for {url}.")
            new_status = status_model(
                url=url,
                fetched_at=fetched_at,
                parsed_at=parsed_at,
                pub_date=pub_date,
                status=False,
                status_type=error_type
            )
            session.add(new_status)
    else:
        new_status = status_model(
            url=url,
            fetched_at=fetched_at,
            parsed_at=parsed_at,
            pub_date=pub_date,
            status=False,
            status_type=error_type
        )
        session.add(new_status)



def update_status_success(session, status_model, url, fetched_at, parsed_at, pub_date, status_id=None, logger=None):
    """
    Update or create a status record in the database for a successful update.

    Args:
        session: Database session.
        status_model: The SQLAlchemy model for article status.
        url (str): The URL of the article.
        fetched_at (datetime): The time when the HTML was fetched.
        parsed_at (datetime): The time when the HTML was parsed.
        pub_date (datetime): The publication date of the article.
        status_id: Optional status record identifier.
        logger: Optional logger for logging.
    """
    if logger:
        logger.info(f"Updating status for {url} with success.")

    if status_id:
        status_obj = session.query(status_model).filter(status_model.status_id == status_id).first()
        if status_obj:
            status_obj.fetched_at = fetched_at
            status_obj.parsed_at = parsed_at
            status_obj.pub_date = pub_date
            status_obj.status = True
            status_obj.status_type = "OK"
        else:
            if logger:
                logger.info(f"Status record {status_id} not found. Creating new success status for {url}.")
            new_status = status_model(
                url=url,
                fetched_at=fetched_at,
                parsed_at=parsed_at,
                pub_date=pub_date,
                status=True,
                status_type="OK"
            )
            session.add(new_status)
    else:
        new_status = status_model(
            url=url,
            fetched_at=fetched_at,
            parsed_at=parsed_at,
            pub_date=pub_date,
            status=True,
            status_type="OK"
        )
        session.add(new_status)

def get_articles_to_update(session, articles_table, status_table, logger):
    """
    Retrieves articles that require an update from the database.

    This function queries the articles and status tables, and determines which articles need
    to be fetched and updated based on the following criteria:
      - No status record exists for the article.
      - The publication date differs between the article and its status record.
      - The status record has missing fetched_at or parsed_at timestamps.

    Args:
        session: Database session.
        articles_table (str): The fully qualified table name for articles (e.g., "pt_abc.articles").
        status_table (str): The fully qualified table name for article status (e.g., "pt_abc.article_status").
        logger: Logger instance for logging.

    Returns:
        tuple: A tuple containing:
            - A list of dictionaries for articles that require an update.
              Each dictionary includes: article_id, url, pub_date, status_id (or None).
            - A summary dictionary with counts:
                {
                    "total": total number of articles processed,
                    "up_to_date": number of articles that did not require an update,
                    "to_update": number of articles marked for update
                }
    """
    articles = session.execute(text(f"SELECT article_id, url, pub_date FROM {articles_table}")).fetchall()
    logger.info(f"Total articles in articles table: {len(articles)}")

    status_records = session.execute(text(f"SELECT status_id, url, pub_date, fetched_at, parsed_at, status_type FROM {status_table}")).fetchall()
    logger.info(f"Total records in article status table: {len(status_records)}")

    status_dict = {record.url: record for record in status_records}

    articles_to_update = []
    summary = {
        "total": 0,
        "up_to_date": 0,
        "to_update": 0
    }

    for article in articles:
        summary["total"] += 1
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
                logger.info(f"Article {article.article_id} requires update (pub_date or fetch status differs).")
                articles_to_update.append({
                    "article_id": article.article_id,
                    "url": article.url,
                    "pub_date": article.pub_date,
                    "status_id": status_record.status_id
                })
            else:
                summary["up_to_date"] += 1

    summary["to_update"] = len(articles_to_update)
    return articles_to_update, summary

def process_update_loop(articles_to_update, update_func, logger, sleep_func=random_sleep):
    """
    Processes the update loop for articles that require an update.

    Iterates over the list of articles, calls the provided update function for each article,
    logs the progress, and sleeps for a random duration between updates.

    Args:
        articles_to_update (list): List of articles requiring update.
        update_func (callable): Function that processes an individual article update.
                                It should accept a dictionary representing the article.
        logger: Logger instance for logging.
        sleep_func (callable): Function to perform sleeping. Defaults to random_sleep.
    """
    for idx, article in enumerate(articles_to_update, start=1):
        logger.info(f"\033[1mProcessing article {idx}/{len(articles_to_update)} with URL: {article['url']}\033[0m")
        update_func(article)
        sleep_func(logger)

def log_update_summary(logger, counters, error_counts):
    """
    Logs a summary of update statistics.

    Args:
        logger: Logger instance for logging.
        counters (dict): Dictionary containing counters for:
            - total: Total articles processed.
            - up_to_date: Articles skipped because they were already up-to-date.
            - to_update: Articles marked for update.
            - fetched: Articles where content was fetched.
            - updated: Articles successfully updated.
            - failed: Articles that failed to update.
        error_counts (dict): Dictionary containing counts of errors by type.
    """
    logger.info("\nUpdate Summary:")
    logger.info(f"  Total articles processed:         {counters.get('total', 0)}")
    logger.info(f"  Articles up-to-date (skipped):      {counters.get('up_to_date', 0)}")
    logger.info(f"  Articles marked for update:         {counters.get('to_update', 0)}")
    logger.info(f"  Articles where content was fetched: {counters.get('fetched', 0)}")
    logger.info(f"  Articles successfully updated:      {counters.get('updated', 0)}")
    logger.info(f"  Articles failed to update:          {counters.get('failed', 0)}")

    logger.info("Error Summary:")
    for err_type, count in error_counts.items():
        logger.info(f"  {err_type}: {count}")
