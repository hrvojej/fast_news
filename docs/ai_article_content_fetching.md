Based on this script:


#!/usr/bin/env python3
"""
ABC Article Updater

This script refactors the original abc_article_fetch_update functionality into a class-based updater.
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
from db_scripts.models.models import create_portal_category_model, create_portal_article_model, create_portal_article_status_model
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

# Dynamically create models for the portal.
ABCCategory = create_portal_category_model("pt_abc")
ABCArticle = create_portal_article_model("pt_abc")
ABCArticleStatus = create_portal_article_status_model("pt_abc")

class ABCArticleUpdater:
    def __init__(self, env='dev'):
        self.env = env
        self.logger = logger
        self.db_context = DatabaseContext.get_instance(env)
        self.ABCArticle = ABCArticle
        self.ABCArticleStatus = ABCArticleStatus
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
            - Parse and extract article content.
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
                    self.ABCArticleStatus,
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

        # Parse HTML and extract content from the target div.
        soup = BeautifulSoup(html_content, 'html.parser')
        article_div = soup.find('div', {'data-testid': 'prism-article-body'})
        if not article_div:
            error_type = "NO_DIV"
            with self.db_context.session() as session:
                update_status_error(
                    session,
                    self.ABCArticleStatus,
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
                    self.ABCArticleStatus,
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

        # Update the article record and record success.
        with self.db_context.session() as session:
            article_obj = session.query(self.ABCArticle).filter(self.ABCArticle.article_id == article_info["article_id"]).first()
            if article_obj:
                article_obj.content = new_content
                self.logger.info(f"Article {article_info['url']} content updated.")
            else:
                self.logger.info(f"Article {article_info['article_id']} not found in articles table.")
                self.counters["failed"] += 1
                return False

            parsed_at = datetime.now(timezone.utc)
            update_status_success(
                session,
                self.ABCArticleStatus,
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
        self.logger.info("Starting Article Content Updater for pt_abc.")
        # Retrieve articles that require an update.
        with self.db_context.session() as session:
            articles_to_update, summary = get_articles_to_update(session, "pt_abc.articles", "pt_abc.article_status", self.logger)
        
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
    parser = argparse.ArgumentParser(description="ABC Article Updater")
    parser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = parser.parse_args()

    try:
        updater = ABCArticleUpdater(env=args.env)
        updater.run()
        logger.info("Article content update completed successfully.")
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()


I need to create same for schema (portal) pt_nyt. 

HTML article page fetching based on url should be done like this:
import pychrome
import time
import threading

def main():
   try:
       browser = pychrome.Browser(url="http://127.0.0.1:9222")
       tab = browser.new_tab()
       
       def handle_exception(msg):
           print(f"Debug: {msg}")
       
       tab.set_listener("exception", handle_exception)
       tab.start()
       
       tab.Page.enable()
       tab.Runtime.enable()
       
       url = "https://edition.cnn.com/2025/02/04/politics/cia-workforce-buyouts/index.html"
       tab.Page.navigate(url=url)
       
       time.sleep(5)
       
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

       with open("cnn.html", "w", encoding="utf-8") as f:
           f.write(html_content)
           
   except Exception as e:
       print(f"Error: {e}")
   finally:
       tab.stop()
       browser.close_tab(tab)

if __name__ == "__main__":
   main()


Structure of all tables are same in that schema as in pt_abc.
You need to fetch content of the article from:
SELECT url  FROM pt_nyt.articles

When opening them extract text from:
#### Rules of extraction of content START

<div data-testid="live-blog-post" 
<section name="articleBody" 
If page don't have any above elements extract text from all elements like this:
<p class="g-text

Ignore pages that have in url path:
/podcasts/
/video/
/audio/





#### Rules of extraction of content END

remove all other- js, css, and html styling - just store pure text in "content" field in database. Clear that filed before storing from existing content. 
Please ask if something is not clear, do not assume. 
Make sure we have final report on inserted skipped errored etc. articles. 

# ################# 
I want to make sure I fully understand your requirements before proceeding. Here are a few questions:

1. **Script Structure & Logic:**  
   Should the new script for the **pt_nyt** schema follow the exact same structure, logging, error handling (including retries, status updates, and sleep intervals), and database update logic as the existing **pt_abc** script—except that it will target the **pt_nyt** schema and use the updated content extraction?

Yes.

2. **Target Element & Extraction:**  
   For the article pages, you mentioned that we need to extract text from the  various html elements in various pages.

   - Should we simply use BeautifulSoup’s `get_text()` on that element to obtain the “pure text” (thus stripping out any JS, CSS, or HTML styling)?  YES.
   - In cases where that element isn’t found, do you want to handle the error the same way as in the pt_abc script (for example, marking the status with an error code like "NO_DIV" or a similar designation)? YES.

3. **Clearing the Content Field:**  
   When you say “Clear that field before storing from existing content,” do you mean that for each article we should explicitly set the **content** field to an empty string (or null) before writing the newly extracted text? YES. Is this intended to ensure that any old or partial data is removed prior to updating? YES.

4. **Additional Customizations:**  
   Are there any other differences in behavior or processing that you would like for the pt_nyt version compared to the pt_abc version, or is it solely the change in schema and the new target extraction element? No, it solely the change in schema and the new target extraction element

   Please ask if something is not clear, do not assume. 

   If you detect that there is no content on page - use "NO_CONTENT" flag in status table. 

