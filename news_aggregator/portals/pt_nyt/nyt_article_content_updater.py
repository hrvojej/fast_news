#!/usr/bin/env python3
"""
NYT Article Updater

This script refactors the original functionality into a class-based updater for the pt_nyt schema.
It uses a headless Chrome instance via pychrome to fetch the HTML content.
The article content is extracted according to these rules:

    1. Extract text from a <div> with attribute data-testid="live-blog-post"
    2. Else, extract text from a <section> with attribute name="articleBody"
    3. Else, extract text from all <p> elements with class "g-text"
    
If no content is found, the article is marked with a "NO_CONTENT" flag.
Additionally, if the article URL contains any of the substrings:
    /podcasts/, /video/, or /audio/,
the article is skipped (and a "SKIPPED" flag is recorded).
Before updating, any existing content is cleared.
A final summary is logged showing counts for total, updated, skipped, and errored articles.
"""

import sys
import os
import argparse
import time
import threading
import random
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import pychrome

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

# Import common updater utilities (except random_sleep, which we override below)
from portals.modules.article_updater_utils import (
    update_status_error,
    update_status_success,
    get_articles_to_update,
    log_update_summary
)

# Set up shared logging
logger = setup_script_logging(__file__)

# -------------------------------
# NEW: Setup global thread error tracking
# -------------------------------
global_thread_error_counts = {}

def threading_exception_handler(args):
    err_type = args.exc_type.__name__
    err_msg = f"Unhandled exception in thread {args.thread.name}: {err_type}: {args.exc_value}"
    logger.error(err_msg)
    global global_thread_error_counts
    global_thread_error_counts[err_type] = global_thread_error_counts.get(err_type, 0) + 1

# Assign the custom exception handler to all threads.
threading.excepthook = threading_exception_handler
# -------------------------------

# Dynamically create models for the pt_nyt portal.
NYTCategory = create_portal_category_model("pt_nyt")
NYTArticle = create_portal_article_model("pt_nyt")
NYTArticleStatus = create_portal_article_status_model("pt_nyt")

# New random_sleep function: pause for a random time between 1 and 3 seconds.
def random_sleep(logger):
    sleep_time = random.uniform(3, 4)
    logger.info(f"Sleeping for {sleep_time:.2f} seconds.")
    time.sleep(sleep_time)

def fetch_html_pychrome(url, logger):
    """
    Fetch HTML content from the given URL using pychrome.
    A headless Chrome instance (with remote debugging enabled) is used to navigate to the URL.
    After a fixed wait of 2 seconds, a JavaScript snippet is run to remove script, style, iframe, link, and meta tags.
    Returns a tuple of (html_content, error) where error is None if successful.
    """
    try:
        browser = pychrome.Browser(url="http://127.0.0.1:9222")
        tab = browser.new_tab()

        def handle_exception(msg):
            logger.debug(f"Debug: {msg}")

        tab.set_listener("exception", handle_exception)
        tab.start()
        tab.Page.enable()
        tab.Runtime.enable()

        tab.Page.navigate(url=url)
        # Wait for the page to load (now 2 seconds)
        time.sleep(2)

        clean_html_js = """
        function cleanHTML() {
            const elements = document.querySelectorAll('script, style, iframe, link, meta');
            elements.forEach(el => el.remove());
            return document.documentElement.outerHTML;
        }
        cleanHTML();
        """
        result = tab.Runtime.evaluate(expression=clean_html_js)
        html_content = result["result"]["value"]
        return html_content, None

    except Exception as e:
        logger.error(f"Error fetching url {url} with pychrome: {e}")
        return None, str(e)

    finally:
        try:
            tab.stop()
            browser.close_tab(tab)
        except Exception as e:
            logger.debug(f"Error closing tab: {e}")

class NYTArticleUpdater:
    def __init__(self, env='dev'):
        self.env = env
        self.logger = logger
        self.db_context = DatabaseContext.get_instance(env)
        self.NYTArticle = NYTArticle
        self.NYTArticleStatus = NYTArticleStatus
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

    def update_article(self, article_info):
        """
        Process an individual article update:
            - Skip URLs with unsupported content types.
            - Fetch HTML content using pychrome.
            - Parse the HTML and extract article content based on extraction rules.
            - Update the article record (clearing any existing content).
            - Record the update or error status in the status table.
        """
        url = article_info['url']
        self.logger.info(f"Processing article with URL: {url}")

        # Check for URLs that should be ignored.
        if any(segment in url for segment in ['/podcasts/', '/video/', '/audio/']):
            self.logger.info(f"Skipping article due to unsupported content type in URL: {url}")
            fetched_at = datetime.now(timezone.utc)
            with self.db_context.session() as session:
                update_status_error(
                    session,
                    self.NYTArticleStatus,
                    url,
                    fetched_at,
                    article_info['pub_date'],
                    "SKIPPED",
                    status_id=article_info.get('status_id'),
                    logger=self.logger
                )
            self.counters["skipped"] += 1
            return False

        fetched_at = datetime.now(timezone.utc)
        html_content, fetch_error = fetch_html_pychrome(url, self.logger)
        if html_content is None:
            error_type = fetch_error if fetch_error else "UNKNOWN_FETCH"
            with self.db_context.session() as session:
                update_status_error(
                    session,
                    self.NYTArticleStatus,
                    url,
                    fetched_at,
                    article_info['pub_date'],
                    error_type,
                    status_id=article_info.get('status_id'),
                    logger=self.logger
                )
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            self.counters["failed"] += 1
            return False

        # Parse HTML and attempt content extraction.
        soup = BeautifulSoup(html_content, 'html.parser')
        content_extracted = None

        # Rule 1: Try <div data-testid="live-blog-post">
        element = soup.find('div', {'data-testid': 'live-blog-post'})
        if element:
            content_extracted = element.get_text(separator="\n").strip()
        else:
            # Rule 2: Try <section name="articleBody">
            element = soup.find('section', {'name': 'articleBody'})
            if element:
                content_extracted = element.get_text(separator="\n").strip()
            else:
                # Rule 3: Try all <p class="g-text">
                elements = soup.find_all('p', class_='g-text')
                if elements:
                    content_extracted = "\n".join(el.get_text(separator="\n").strip() for el in elements)

        if not content_extracted:
            error_type = "NO_CONTENT"
            with self.db_context.session() as session:
                update_status_error(
                    session,
                    self.NYTArticleStatus,
                    url,
                    fetched_at,
                    article_info['pub_date'],
                    error_type,
                    status_id=article_info.get('status_id'),
                    logger=self.logger
                )
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            self.counters["failed"] += 1
            return False

        # Update the article record.
        with self.db_context.session() as session:
            article_obj = session.query(self.NYTArticle).filter(
                self.NYTArticle.article_id == article_info["article_id"]
            ).first()
            if article_obj:
                # Clear existing content then update.
                article_obj.content = ""
                article_obj.content = content_extracted
                self.logger.info(f"Article {url} content updated.")
            else:
                self.logger.info(f"Article {article_info['article_id']} not found in articles table.")
                self.counters["failed"] += 1
                return False

            parsed_at = datetime.now(timezone.utc)
            update_status_success(
                session,
                self.NYTArticleStatus,
                url,
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
        self.logger.info("Starting Article Content Updater for pt_nyt.")
        # Retrieve articles to update from pt_nyt.articles.
        with self.db_context.session() as session:
            articles_to_update, summary = get_articles_to_update(
                session,
                "pt_nyt.articles",
                "pt_nyt.article_status",
                self.logger
            )

        self.counters["total"] = summary.get("total", 0)
        self.counters["up_to_date"] = summary.get("up_to_date", 0)
        self.counters["to_update"] = summary.get("to_update", 0)
        self.logger.info(f"Total articles marked for update: {len(articles_to_update)}")

        for idx, article in enumerate(articles_to_update, start=1):
            self.logger.info(f"\033[1mProcessing article {idx}/{len(articles_to_update)} with URL: {article['url']}\033[0m")
            self.update_article(article)
            random_sleep(self.logger)

        # Log the final summary including any thread exceptions.
        log_update_summary(self.logger, self.counters, self.error_counts)
        if global_thread_error_counts:
            self.logger.info("Thread Exception Summary:")
            for err_type, count in global_thread_error_counts.items():
                self.logger.info(f"  {err_type}: {count}")

def main():
    parser = argparse.ArgumentParser(description="NYT Article Updater")
    parser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = parser.parse_args()

    try:
        updater = NYTArticleUpdater(env=args.env)
        updater.run()
        logger.info("Article content update completed successfully.")
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()
