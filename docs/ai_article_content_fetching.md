Based on this script:

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
       - If a status record already exists, update its fetched_at, parsed_at, pub_date,
         status, and status_type.
       - If no status record exists, insert a new one with these details.
       
Error handling includes:
  - Retries (up to 3 attempts) for connection errors (network errors).
  - Immediate exit for repeated 403 responses (after 3 consecutive 403s).
  - Reporting of distinct errors in a summary at the end.
  
For successful fetch and parsing:
    status = 1, status_type = "OK"
For errors:
    status = 0, and status_type is set to one of:
      - "NO_DIV" for missing content div,
      - "HTTP403", "HTTP404", "HTTP5xx", or "HTTP_ERR" for HTTP errors,
      - "NET" for network errors.
      
In the case of network errors the parsed_at field is left NULL so that the URL is picked
up for a retry.
      
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
            - On success: (content, None)
            - On error: (None, error_type)
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

    def update_article_content(self, article_info: dict) -> bool:
        """
        For a given article (specified by article_id, url, pub_date, and possibly a status_id),
        fetch the HTML, extract the article text, update the article content, and update or create
        the status record.
        
        In every case (success or error) the status record is updated with:
          - status: True (1) if successful, False (0) if an error occurred.
          - status_type: "OK" on success or a specific error type.
          
        For network errors, parsed_at is left as NULL so that the article is retried.
        
        Returns True if the update was successful, False otherwise.
        """
        url = article_info["url"]
        article_id = article_info["article_id"]
        pub_date = article_info["pub_date"]
        status_id = article_info.get("status_id")  # May be None if no status record exists

        logger.info(f"Processing article with URL: {url}")

        # Attempt to fetch the HTML.
        html_content, fetch_error = self.fetch_html(url)
        fetched_time = datetime.now(timezone.utc)

        # If no HTML content was fetched, update status record with the error.
        if html_content is None:
            error_type = fetch_error if fetch_error else "UNKNOWN_FETCH"
            # For network errors leave parsed_at as None so that the URL is retried.
            parsed_time = None if error_type == "NET" else datetime.now(timezone.utc)
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            logger.info(f"Failed to fetch content for article {url} with error {error_type}. Skipping update.")
            try:
                with self.db_context.session() as session:
                    if status_id:
                        status_obj = session.query(self.ABCArticleStatus).filter(
                            self.ABCArticleStatus.status_id == status_id
                        ).first()
                        if status_obj:
                            status_obj.fetched_at = fetched_time
                            status_obj.parsed_at = parsed_time
                            status_obj.pub_date = pub_date
                            status_obj.status = False
                            status_obj.status_type = error_type
                            logger.info(f"Status record {status_id} updated with error {error_type}.")
                    else:
                        new_status = self.ABCArticleStatus(
                            url=url,
                            fetched_at=fetched_time,
                            parsed_at=parsed_time,
                            pub_date=pub_date,
                            status=False,
                            status_type=error_type
                        )
                        session.add(new_status)
                        logger.info(f"New status record created for article {url} with error {error_type}.")
            except Exception as e:
                logger.error(f"Error updating status record for article {url} with error {error_type}: {e}")
            self.counters["failed"] += 1
            return False

        # Parse the HTML and extract text from the target div.
        soup = BeautifulSoup(html_content, 'html.parser')
        article_div = soup.find('div', {'data-testid': 'prism-article-body'})
        if not article_div:
            error_type = "NO_DIV"
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            logger.error(f"Could not find the target content div for article {url}. Skipping update.")
            parsed_time = datetime.now(timezone.utc)
            try:
                with self.db_context.session() as session:
                    if status_id:
                        status_obj = session.query(self.ABCArticleStatus).filter(
                            self.ABCArticleStatus.status_id == status_id
                        ).first()
                        if status_obj:
                            status_obj.fetched_at = fetched_time
                            status_obj.parsed_at = parsed_time
                            status_obj.pub_date = pub_date
                            status_obj.status = False
                            status_obj.status_type = error_type
                            logger.info(f"Status record {status_id} updated with error {error_type}.")
                    else:
                        new_status = self.ABCArticleStatus(
                            url=url,
                            fetched_at=fetched_time,
                            parsed_at=parsed_time,
                            pub_date=pub_date,
                            status=False,
                            status_type=error_type
                        )
                        session.add(new_status)
                        logger.info(f"New status record created for article {url} with error {error_type}.")
            except Exception as e:
                logger.error(f"Error updating status record for article {url} with error {error_type}: {e}")
            self.counters["failed"] += 1
            return False

        new_content = article_div.get_text(separator="\n").strip()
        if not new_content:
            # In case the extracted content is empty, record an error.
            error_type = "EMPTY_CONTENT"
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            logger.info(f"Extracted content is empty for article {url}. Skipping update.")
            parsed_time = datetime.now(timezone.utc)
            try:
                with self.db_context.session() as session:
                    if status_id:
                        status_obj = session.query(self.ABCArticleStatus).filter(
                            self.ABCArticleStatus.status_id == status_id
                        ).first()
                        if status_obj:
                            status_obj.fetched_at = fetched_time
                            status_obj.parsed_at = parsed_time
                            status_obj.pub_date = pub_date
                            status_obj.status = False
                            status_obj.status_type = error_type
                            logger.info(f"Status record {status_id} updated with error {error_type}.")
                    else:
                        new_status = self.ABCArticleStatus(
                            url=url,
                            fetched_at=fetched_time,
                            parsed_at=parsed_time,
                            pub_date=pub_date,
                            status=False,
                            status_type=error_type
                        )
                        session.add(new_status)
                        logger.info(f"New status record created for article {url} with error {error_type}.")
            except Exception as e:
                logger.error(f"Error updating status record for article {url} with error {error_type}: {e}")
            self.counters["failed"] += 1
            return False

        # If we reach here, the article content was fetched and parsed successfully.
        try:
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

                # Update or insert the corresponding status record with success.
                parsed_time = datetime.now(timezone.utc)
                if status_id:
                    status_obj = session.query(self.ABCArticleStatus).filter(
                        self.ABCArticleStatus.status_id == status_id
                    ).first()
                    if status_obj:
                        status_obj.fetched_at = fetched_time
                        status_obj.parsed_at = parsed_time
                        status_obj.pub_date = pub_date
                        status_obj.status = True
                        status_obj.status_type = "OK"
                        logger.info(f"Status record {status_id} updated with success status.")
                    else:
                        logger.info(f"Status record {status_id} not found during update. This should not happen.")
                        self.counters["failed"] += 1
                        return False
                else:
                    new_status = self.ABCArticleStatus(
                        url=url,
                        fetched_at=fetched_time,
                        parsed_at=parsed_time,
                        pub_date=pub_date,
                        status=True,
                        status_type="OK"
                    )
                    session.add(new_status)
                    logger.info(f"New status record created for article {url} with success status.")
            self.counters["updated"] += 1
            return True

        except Exception as e:
            logger.error(f"Error updating article {url}: {e}")
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
                text("SELECT status_id, url, pub_date, fetched_at, parsed_at, status_type FROM pt_abc.article_status")
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
                #    (Note: for network errors, parsed_at is left NULL to force a retry.)
                if status_record is None:
                    logger.info(f"Article {article.article_id} with URL {article.url} has no status record. Marking for update (new status record will be created).")
                    articles_to_update.append({
                        "article_id": article.article_id,
                        "url": article.url,
                        "pub_date": article.pub_date,
                        "status_id": None
                    })
                else:
                    # If the pub_date differs or if either timestamp is missing, then mark for update.
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


I need to create same for schema (portal) pt_bbc. Structure of all tables are same in that schema as in pt_abc.
You need to fetch content of the article from:
urls from database.

When opening them extract text from:
#### Rules of extraction of content START

# Rules for URLS starting with: https://www.bbc.com/sport or https://www.bbc.com/news/ or any other simillar category:
Get all text from:  
#main-content > article
tag.


# Rules for URLS starting with: 
https://www.bbc.co.uk/bitesize/ 
https://www.bbc.co.uk/iplayer/
https://www.bbc.com/audio/
and if category or "article" is missing after domain name like in:
https://www.bbc.co.uk/news/10628994
https://www.bbc.co.uk/news/10725415
also all links that have /live/ in URL:
https://www.bbc.com/live
Or
https://www.bbc.com/sport/football/live/cy9l1yjvnz5t
--> :
Skip all of them - put status_type "SKIP".


# Rules for URLS starting with: https://www.bbc.com/news/videos/
Get text from DIV: 
<div data-testid="video-page-video-section"



#### Rules of extraction of content END

remove all other- js, css, and html styling - just store pure text in "content" field in database. Clear that filed before storing from existing content. 
Please ask if something is not clear, do not assume. 

# ################# 
I want to make sure I fully understand your requirements before proceeding. Here are a few questions:

1. **Script Structure & Logic:**  
   Should the new script for the **pt_bbc** schema follow the exact same structure, logging, error handling (including retries, status updates, and sleep intervals), and database update logic as the existing **pt_abc** script—except that it will target the **pt_bbc** schema and use the updated content extraction?

Yes.

2. **Target Element & Extraction:**  
   For the article pages, you mentioned that we need to extract text from the  
   ```html
   <div class="wysiwyg wysiwyg--all-content" aria-live="polite" aria-atomic="true">
   ```  
   element.  
   - Should we simply use BeautifulSoup’s `get_text()` on that element to obtain the “pure text” (thus stripping out any JS, CSS, or HTML styling)?  YES.
   - In cases where that element isn’t found, do you want to handle the error the same way as in the pt_abc script (for example, marking the status with an error code like "NO_DIV" or a similar designation)? YES.

3. **Clearing the Content Field:**  
   When you say “Clear that field before storing from existing content,” do you mean that for each article we should explicitly set the **content** field to an empty string (or null) before writing the newly extracted text? YES. Is this intended to ensure that any old or partial data is removed prior to updating? YES.

4. **Additional Customizations:**  
   Are there any other differences in behavior or processing that you would like for the pt_bbc version compared to the pt_abc version, or is it solely the change in schema and the new target extraction element? No, it solely the change in schema and the new target extraction element

   Please ask if something is not clear, do not assume. 



# Errors to fix:
After running script I get in database:

SELECT url, guid,pub_date content FROM pt_bbc.articles
where url like '%c8d95v0nr1yo%'
-->

"https://www.bbc.com/news/articles/c8d95v0nr1yo"	"https://www.bbc.com/news/articles/c8d95v0nr1yo#1"	"2025-02-04 15:24:34+01"
"https://www.bbc.com/news/articles/c8d95v0nr1yo"	"https://www.bbc.com/news/articles/c8d95v0nr1yo#0"	"2025-02-04 14:24:34+01"
"https://www.bbc.com/news/articles/c8d95v0nr1yo"	"https://www.bbc.com/news/articles/c8d95v0nr1yo#2"	"2025-02-04 15:24:34+01"



These are dupes - this should not be happening. UPSERT should be applied based on pub_date in case there is same record.

Also before proceeding dupes check should be done and keep only single record that has latest pub_date. 