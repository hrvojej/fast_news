#!/usr/bin/env python3
"""
Google Images Fetcher from DB

This script fetches articles from the database that have no content,
logs their titles, and for each article:
  - Opens a headless Chrome instance via pychrome to perform a Google Images search using the article title as search keywords.
  - Simulates a click at fixed coordinates (since the first image appears in the same spot).
  - Simulates a right-click on the image preview to extract the image URL.
  - Logs the image URL (or any error encountered).

Additional features:
  - A random delay (3-6 seconds) is applied between processing articles.
  - A command-line parameter (--limit) limits the number of articles processed (0 means no limit).

Make sure Chrome is running with remote debugging enabled (e.g.:
    chrome --remote-debugging-port=9222
)
"""

import sys
import os
import argparse
import time
import random
import re
import threading
import urllib.parse
from urllib.parse import urlparse
from datetime import datetime, timezone
import pychrome
import pytesseract
from PIL import Image
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"



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
from portals.modules.article_updater_utils import (
    get_articles_for_google_images,
    log_update_summary
)

logger = setup_script_logging(__file__)

# -------------------------------
# Global thread error tracking
# -------------------------------
global_thread_error_counts = {}

def check_image_for_text(filename, logger, text_threshold=5):
    """
    Uses Tesseract OCR to check if the image contains text.
    Returns True if the detected text (after stripping whitespace) has a length greater than text_threshold, False otherwise.
    """
    try:
        logger.info(f"Checking image {filename} for text using Tesseract OCR.")
        image = Image.open(filename)
        text = pytesseract.image_to_string(image)
        logger.info(f"Detected text: {text.strip()}")
        if len(text.strip()) > text_threshold:
            return True
        return False
    except Exception as e:
        logger.error(f"Error processing image {filename} for text detection: {e}")
        return False


def threading_exception_handler(args):
    err_type = args.exc_type.__name__
    err_msg = f"Unhandled exception in thread {args.thread.name}: {err_type}: {args.exc_value}"
    logger.error(err_msg)
    global global_thread_error_counts
    global_thread_error_counts[err_type] = global_thread_error_counts.get(err_type, 0) + 1

threading.excepthook = threading_exception_handler

# Dynamically create models for the pt_nyt portal
NYTCategory = create_portal_category_model("pt_nyt")
NYTArticle = create_portal_article_model("pt_nyt")
NYTArticleStatus = create_portal_article_status_model("pt_nyt")

def random_sleep(logger):
    sleep_time = random.uniform(3, 6)
    logger.info(f"Sleeping for {sleep_time:.2f} seconds.")
    time.sleep(sleep_time)


def fetch_image_urls(title, logger):
    """
    Uses pychrome to open Google Images with the given title as search keywords.
    It then simulates three clicks at fixed coordinates (for three images) and
    simulates a right-click on the image preview (which always appears at the same place)
    to extract each image URL.
    
    Returns a tuple (image_urls, error) where image_urls is a list of URLs (which may have fewer than three if some fail)
    and error is None if no exception occurred.
    """
    image_urls = []
    tab = None
    browser = None
    try:
        browser = pychrome.Browser(url="http://127.0.0.1:9222")
        tab = browser.new_tab()
        tab.start()
        tab.Page.enable()
        tab.Runtime.enable()

        query = urllib.parse.quote(title)
        url = f"https://www.google.com/search?tbm=isch&q={query}"
        logger.info(f"Navigating to URL: {url}")
        tab.Page.navigate(url=url)

        load_wait_time = random.uniform(4, 6)
        logger.info(f"Waiting {load_wait_time:.2f} seconds for page to load.")
        time.sleep(load_wait_time)

        # Define the left-click coordinates for three images.
        click_positions = [(100, 450), (300, 450), (450, 450)]
        # Fixed right-click coordinates for the preview (since it always appears at the same place).
        right_click_x = 1500
        right_click_y = 450

        for (click_x, click_y) in click_positions:
            logger.info(f"Simulating left-click at coordinates ({click_x}, {click_y}).")
            tab.Input.dispatchMouseEvent(
                type="mousePressed",
                x=click_x,
                y=click_y,
                button="left",
                clickCount=1
            )
            tab.Input.dispatchMouseEvent(
                type="mouseReleased",
                x=click_x,
                y=click_y,
                button="left",
                clickCount=1
            )

            preview_wait_time = random.uniform(2, 3)
            logger.info(f"Waiting {preview_wait_time:.2f} seconds for image preview to load.")
            time.sleep(preview_wait_time)

            logger.info(f"Simulating right-click at coordinates ({right_click_x}, {right_click_y}) on preview.")
            tab.Input.dispatchMouseEvent(
                type="mousePressed",
                x=right_click_x,
                y=right_click_y,
                button="right",
                clickCount=1
            )
            tab.Input.dispatchMouseEvent(
                type="mouseReleased",
                x=right_click_x,
                y=right_click_y,
                button="right",
                clickCount=1
            )

            # Execute JavaScript to extract the preview image URL.
            right_click_js = """
            (function(){
                let imgs = document.querySelectorAll('img');
                let target = null;
                for (let img of imgs) {
                    if (img.src && img.src.startsWith("http")) {
                        let domain = new URL(img.src).hostname;
                        if (!domain.includes("google.com") && !domain.includes("gstatic.com") && !domain.includes("googleusercontent.com")) {
                            target = img;
                            break;
                        }
                    }
                }
                if (target){
                    let evt = new MouseEvent('contextmenu', { bubbles: true, cancelable: true, view: window });
                    target.dispatchEvent(evt);
                    return target.src;
                }
                return null;
            })();
            """
            result = tab.Runtime.evaluate(expression=right_click_js)
            image_url = result["result"]["value"]
            if image_url:
                logger.info(f"Fetched image URL: {image_url}")
                image_urls.append(image_url)
            else:
                logger.error(f"No image URL found for click at ({click_x}, {click_y}).")
        return image_urls, None

    except Exception as e:
        logger.error(f"Error fetching images for title '{title}': {e}")
        return image_urls, str(e)

    finally:
        if tab is not None:
            try:
                tab.stop()
            except Exception as e:
                logger.debug(f"Error stopping tab: {e}")
        if browser is not None and tab is not None:
            try:
                browser.close_tab(tab)
            except Exception as e:
                logger.debug(f"Error closing tab: {e}")


def download_image(url, dest_filename, logger):
    """
    Downloads an image from the given URL and saves it to dest_filename.
    """
    try:
        logger.info(f"Downloading image from URL: {url} to {dest_filename}")
        import urllib.request
        urllib.request.urlretrieve(url, dest_filename)
        logger.info(f"Downloaded image saved as {dest_filename}")
    except Exception as e:
        logger.error(f"Failed to download image from {url}: {e}")



class GoogleImagesFetcher:
    def __init__(self, env='dev', limit=0):
        self.env = env
        self.limit = limit  # Limit on the number of articles to process; 0 means no limit.
        self.logger = logger
        self.db_context = DatabaseContext.get_instance(env)
        self.counters = {
            "total": 0,
            "fetched": 0,
            "failed": 0,
        }
        self.error_counts = {}

    def run(self):
        self.logger.info("Starting Google Images Fetcher for articles with no content.")
        with self.db_context.session() as session:
            articles_to_update = get_articles_for_google_images(
                session,
                "pt_nyt.articles",
                self.logger
            )

        self.logger.info(f"Total articles to process: {len(articles_to_update)}")


        self.counters["total"] = len(articles_to_update)

        self.logger.info(f"Total articles to process: {len(articles_to_update)}")

        if self.limit > 0:
            articles_to_update = articles_to_update[:self.limit]
            self.logger.info(f"Limiting processing to first {self.limit} articles.")

        for idx, article in enumerate(articles_to_update, start=1):
            title = article.get("title", "")
            if not title:
                article_id = article.get("article_id", f"{idx} (no id)")
                url = article.get("url", "No URL")
                self.logger.error(f"Article {article_id} with URL {url} has an empty title. Skipping.")
                self.counters["failed"] += 1
                continue


            self.logger.info(f"Processing article {idx}/{len(articles_to_update)}: {title}")
            image_urls, error = fetch_image_urls(title, self.logger)
            if error:
                self.logger.error(f"Error fetching images for '{title}': {error}")
                self.error_counts[error] = self.error_counts.get(error, 0) + 1
                self.counters["failed"] += 1
            else:
                
                
                self.logger.info(f"Fetched image URLs for '{title}': {image_urls}")
                # Download each image, check for text using Tesseract, and filter out images containing text.
                article_id = article.get("article_id", f"article_{idx}")
                valid_image_urls = []
                for i, url in enumerate(image_urls, start=1):
                    image_caption = re.sub(r'[\\/*?:"<>|]', '', title).replace(' ', '_')      

                    parsed_url = urlparse(url)
                    _, ext = os.path.splitext(parsed_url.path)
                    if not ext:
                        ext = '.jpg'

                    image_caption = re.sub(r'[\\/*?:"<>|]', '', title).replace(' ', '_')
                    filename = f"{article_id}_{image_caption}{ext}"


                    download_image(url, filename, self.logger)
                    if check_image_for_text(filename, self.logger):
                        self.logger.info(f"Image {filename} contains text, filtering it out.")
                        try:
                            os.remove(filename)
                            self.logger.info(f"Deleted image {filename} due to detected text.")
                        except Exception as e:
                            self.logger.error(f"Failed to delete image {filename}: {e}")
                        continue
                    valid_image_urls.append(url)
                self.logger.info(f"Valid image URLs for '{title}': {valid_image_urls}")
                self.counters["fetched"] += 1



            random_sleep(self.logger)

        log_update_summary(self.logger, self.counters, self.error_counts)
        if global_thread_error_counts:
            self.logger.info("Thread Exception Summary:")
            for err_type, count in global_thread_error_counts.items():
                self.logger.info(f"  {err_type}: {count}")

def main():
    parser = argparse.ArgumentParser(
        description="Google Images Fetcher from DB: Retrieve image URL based on article title for articles with no content."
    )
    parser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help="Limit the number of articles to process (0 for no limit)"
    )
    args = parser.parse_args()

    try:
        fetcher = GoogleImagesFetcher(env=args.env, limit=args.limit)
        fetcher.run()
        logger.info("Google Images fetching completed successfully.")
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    main()
