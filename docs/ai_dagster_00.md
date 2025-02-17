Past days Ive been building category parsers, article parsers and article content update (3 scripts that have to be run one after another ):
- category parser - updates list of categoris in which article belongs (run once in hour)
- article parser scripts - getting metadata about new articles that needs to be parsed and getting metadata from those articles (run once in hour after category parser)
- article content updater - scripts that update content based on new url on articles fetched from article parser script (run once in hour after article content updater if there is new article metadata fetched)

Im covering currently 8 portals:
(venv) C:\Users\Korisnik\Desktop\TLDR\news_dagster-etl\news_aggregator\portals>tree /f
Folder PATH listing
Volume serial number is ACEF-BB81
C:.
│   cache_models.py
│   
├───archive
│   └───pt_bloomberg
│           bloomberg_html_category_parser.py
│           bloomberg_rss_article_parser.py
│
├───modules
│   │   article_updater_utils.py
│   │   base_parser.py
│   │   keyword_extractor.py
│   │   logging_config.py
│   │   portal_db.py
│   │   rss_parser_utils.py
│   │   __init__.py
│   │   
│   └───__pycache__
│           article_updater_utils.cpython-313.pyc
│           base_parser.cpython-313.pyc
│           keyword_extractor.cpython-313.pyc
│           logging_config.cpython-313.pyc
│           portal_db.cpython-313.pyc
│           rss_parser_utils.cpython-313.pyc
│           __init__.cpython-313.pyc
│
├───pt_abc
│       abc_article_content_updater.py
│       abc_article_rss_parser.py
│       abc_category_rss_parser.py
│
├───pt_aljazeera
│       aljazeera_article_content_updater.py
│       aljazeera_article_rss_parser.py
│       aljazeera_category_html_parser.py
│       test_rss_feed.py
│
├───pt_bbc
│       bbc_article_content_updater.py
│       bbc_article_rss_parser.py
│       bbc_category_html_parser.py
│
├───pt_fox
│       fox_article_content_updater.py
│       fox_article_rss_parser.py
│       fox_category_rss_parser.py
│       fox_keyword_updater.py
│
├───pt_guardian
│       guardian_article_content_updater.py
│       guard_html_category_parser.py
│       guard_rss_article_parser.py
│       test_articles.py
│
├───pt_nyt
│       nyt_article_content_updater.py
│       nyt_rss_article_parser.py
│       nyt_rss_categories_parser.py
│       __init__.py
│
├───pt_reuters
│       reuters_article_content_updater.py
│       reuters_keyword_updater.py
│       reuters_rss_articles_parser.py
│       reuters_rss_categories_parser.py
│
└───py_cnn
        cnn_article_content_updater.py
        cnn_html_articles_parser.py
        cnn_html_categories_parser.py


(venv) C:\Users\Korisnik\Desktop\TLDR\news_dagster-etl\news_aggregator\portals>

Now, I would like to set up orchestration of those scripts with dagster without overcomplicating with some aditional features. Just implementing what I explained. 
Pleae lead me in this, I have all scripts functioning and ready. They are in Python. 
if you need more details - please ask, do not assume. 
Im setting it all up on my windows 11 machine in python virtual env, using: Python 3.13.2 with PostgreSQL16.  

Now I need to clarify how to schedule and orchestrate them. I should ask the user a few questions:

All 3 scripts should be run as part of single pipeline. 
Each portal should have its own pipeline - so one job per portal. 


Do they want to use Dagster's schedule or sensor functionalities for scheduling?
I think schedule would be fine for now. 

Also, should the tasks for each portal be part of a single pipeline or should I separate them? 
Separate them. 

, how dependencies should be handled - they are already installed, scripts are fully functional
, and if the content updater should check for new metadata before running - content updater currently checks just for new urls in status_table , that script is fetching content of articles for urls that don't have fetched_at and parsed_at dates set. 

# ## Questions answered:
Are these scripts already functioning as expected individually?
Yes.
 Also, will these scripts use PostgreSQL for some sort of state tracking?
 Yes.

It looks like the user wants to run all three scripts in a single pipeline but also considers having a separate pipeline per portal, meaning one job for each portal.
Yes.
 They also prefer to use Dagster's scheduler for now. Yes.
  I'll need to clarify: Should we treat each portal as an independent job and ensure no overlap?
  Yes.
   How should their task dependencies be structured? Is the content updater script checking only the status table, or is there more to the logic? Once we have these details, we can provide a solid orchestration recommendation.

  I'll also want to know the basic structure or flow of the scripts — are they interdependent in any way? Let's clarify a bit further.

# Here goes example of functioning script for parseing data from ABC news portal
## news_dagster-etl\news_aggregator\portals\pt_abc\abc_category_rss_parser.py:
#!/usr/bin/env python
"""
ABC News RSS Categories Parser
Fetches and stores ABC News RSS feed categories using SQLAlchemy ORM.
Refactored in a similar style as abc_article_rss_parser.
"""

import argparse
import sys
import os
import requests
import re
from bs4 import BeautifulSoup
from uuid import UUID

# Add the package root (e.g., news_aggregator) to sys.path if needed.
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from portals.modules.portal_db import fetch_portal_id_by_prefix
from db_scripts.models.models import create_portal_category_model
from portals.modules.logging_config import setup_script_logging

logger = setup_script_logging(__file__)

# Dynamically create the category model for the ABC News portal.
ABCCategory = create_portal_category_model("pt_abc")


class ABCRSSCategoriesParser:
    """
    Parser for ABC News RSS feed categories.
    Fetches a page listing RSS feeds, parses each feed to extract category metadata,
    and stores unique categories in the database.
    """

    def __init__(self, portal_id: UUID, env: str = 'dev', category_model=ABCCategory):
        """
        Initialize the parser.

        Args:
            portal_id: UUID of the ABC News portal in the news_portals table.
            env: Environment to use ('dev' or 'prod').
            category_model: SQLAlchemy ORM model for categories.
        """
        self.portal_id = portal_id
        self.env = env
        self.category_model = category_model
        self.base_url = "https://abcnews.go.com/Site/page/rss-feeds-3520115"

    @staticmethod
    def clean_ltree(value: str) -> str:
        """
        Convert a category title into a valid ltree path.
        """
        if not value:
            return "unknown"
        # Replace "U.S." with "U_S", slashes/backslashes with dots, arrow indicators with dots,
        # then convert to lowercase.
        value = value.replace('U.S.', 'U_S')
        value = value.replace('/', '.').replace('\\', '.')
        value = value.replace('>', '.').strip()
        value = value.lower()
        # Replace any non-alphanumeric characters (except dots) with underscores.
        value = re.sub(r'[^a-z0-9.]+', '_', value)
        # Replace multiple dots or underscores with a single dot.
        value = re.sub(r'[._]{2,}', '.', value)
        return value.strip('._')

    def fetch_rss_feeds(self):
        """
        Fetch the ABC News RSS feeds page, extract unique RSS feed URLs,
        and parse each feed to extract category metadata.
        """
        try:
            logger.info(f"Fetching RSS feeds page from {self.base_url}")
            response = requests.get(self.base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            rss_links = []
            # Look for <a> elements whose href starts with the expected ABC News RSS feed URL.
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                if href.startswith("https://feeds.abcnews.com/"):
                    rss_links.append(href)
            unique_rss_links = list(set(rss_links))
            logger.info(f"Found {len(unique_rss_links)} unique RSS feeds")
            return self.parse_rss_feeds(unique_rss_links)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch RSS feeds page: {e}")
            raise Exception(f"Failed to fetch RSS feeds page: {e}")

    def parse_rss_feeds(self, rss_links):
        """
        Parse each RSS feed URL and extract category metadata.

        Args:
            rss_links: List of RSS feed URLs.

        Returns:
            A list of dictionaries containing category metadata.
        """
        categories = []
        for rss_url in rss_links:
            try:
                logger.info(f"Processing RSS feed: {rss_url}")
                response = requests.get(rss_url)
                response.raise_for_status()
                rss_soup = BeautifulSoup(response.content, 'xml')
                channel = rss_soup.find('channel')
                if channel:
                    title_tag = channel.find('title')
                    link_tag = channel.find('link')
                    description_tag = channel.find('description')
                    
                    # Use the RSS feed title if available, otherwise fallback to the URL.
                    title = title_tag.text.strip() if title_tag and title_tag.text else rss_url
                    link = link_tag.text.strip() if link_tag and link_tag.text else ""
                    description = description_tag.text.strip() if description_tag and description_tag.text else ""
                    
                    # Always use the RSS feed URL for atom_link.
                    atom_link = rss_url
                    
                    # Create a path and level based on the title.
                    path = self.clean_ltree(title)
                    level = len(path.split('.'))
                    
                    category = {
                        'title': title,
                        'link': link,
                        'description': description,
                        'atom_link': atom_link,
                        'path': path,
                        'level': level
                    }
                    categories.append(category)
                else:
                    # If no <channel> element is present, store minimal information.
                    title = rss_url
                    path = self.clean_ltree(title)
                    level = len(path.split('.'))
                    category = {
                        'title': title,
                        'link': "",
                        'description': "",
                        'atom_link': rss_url,
                        'path': path,
                        'level': level
                    }
                    categories.append(category)
            except Exception as e:
                logger.error(f"Error processing RSS feed {rss_url}: {e}")
                continue
        return categories

    def store_categories(self, categories):
        """
        Store categories in the database using SQLAlchemy ORM.
        Avoids inserting duplicate categories.

        Args:
            categories: List of category dictionaries.
        """
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext.get_instance(self.env)
        session = db_context.session().__enter__()
        try:
            logger.info("Storing categories in the database...")
            count_added = 0
            for category_data in categories:
                slug = self.clean_ltree(category_data['title'])
                # Check if this category already exists for the portal.
                existing = session.query(self.category_model).filter(
                    self.category_model.slug == slug,
                    self.category_model.portal_id == self.portal_id
                ).first()
                if existing:
                    logger.info(f"Category with slug '{slug}' already exists. Skipping insertion.")
                    continue

                category = self.category_model(
                    name=category_data['title'],
                    slug=slug,
                    portal_id=self.portal_id,
                    path=category_data['path'],
                    level=category_data['level'],
                    description=category_data['description'],
                    link=category_data['link'],
                    atom_link=category_data['atom_link'],
                    is_active=True
                )
                session.add(category)
                count_added += 1

            session.commit()
            logger.info(f"Successfully stored {count_added} new categories.")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store categories: {e}")
            raise Exception(f"Failed to store categories: {e}")
        finally:
            session.close()

    def run(self):
        """
        Main method to fetch, parse, and store ABC News categories.
        """
        try:
            categories = self.fetch_rss_feeds()
            self.store_categories(categories)
            logger.info("Category processing completed successfully.")
        except Exception as e:
            logger.error(f"Error processing categories: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description="ABC News RSS Categories Parser")
    parser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = parser.parse_args()

    portal_id = fetch_portal_id_by_prefix("pt_abc", env=args.env)
    logger.info(f"Using portal_id: {portal_id} for portal_prefix: pt_abc")
    parser_instance = ABCRSSCategoriesParser(portal_id=portal_id, env=args.env)
    parser_instance.run()


if __name__ == "__main__":
    main()


## news_dagster-etl\news_aggregator\portals\pt_abc\abc_article_rss_parser.py:
#!/usr/bin/env python
import argparse
from uuid import UUID
import sys
import os

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)


from portals.modules.base_parser import BaseRSSParser
from portals.modules.portal_db import fetch_portal_id_by_prefix, get_active_categories
from portals.modules.rss_parser_utils import parse_rss_item
from db_scripts.models.models import create_portal_article_model, create_portal_category_model

from portals.modules.logging_config import setup_script_logging
logger = setup_script_logging(__file__)


# Dynamically create models for the portal.
ABCCategory = create_portal_category_model("pt_abc")
ABCArticle = create_portal_article_model("pt_abc")


class ABCRSSArticlesParser(BaseRSSParser):
    def __init__(self, portal_id: UUID, env: str = 'dev'):
        super().__init__(portal_id, env)
        self.model = ABCArticle

    def parse_item(self, item, category_id):
        """
        Uses the generic RSS parser utility to parse an item.
        """
        return parse_rss_item(item, category_id)

    def run(self):
        feeds = get_active_categories("pt_abc", self.env)
        self.run_feeds(feeds)



def main():
    argparser = argparse.ArgumentParser(description="ABC RSS Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    portal_id = fetch_portal_id_by_prefix("pt_abc", env=args.env)
    parser = ABCRSSArticlesParser(portal_id=portal_id, env=args.env)
    parser.run()

if __name__ == "__main__":
    main()


## news_dagster-etl\news_aggregator\portals\pt_abc\abc_article_content_updater.py:
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


# Other relevant scripts:
## [text](../news_aggregator/portals/modules/base_parser.py)
from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
from db_scripts.db_context import DatabaseContext
from portals.modules.logging_config import setup_script_logging
from sqlalchemy.dialects.postgresql import insert


# Configure logger using the shared logging configuration.
logger = setup_script_logging(__file__)

class BaseRSSParser(ABC):
    """
    Base class for RSS parsers.
    Encapsulates shared functionality:
      - Fetching feeds
      - Parsing XML with BeautifulSoup
      - Managing database sessions
      - Handling errors and logging
      - Upserting items into the database
    """
    def __init__(self, portal_id, env='dev'):
        """
        :param portal_id: Unique identifier for the portal.
        :param env: Environment ('dev' or 'prod').
        """
        self.portal_id = portal_id
        self.env = env
        self.db_context = DatabaseContext.get_instance(env)
        # Subclasses must set this to their specific SQLAlchemy model.
        self.model = None

    def fetch_feed(self, url):
        """
        Fetches the RSS feed from a given URL and returns a BeautifulSoup object.
        :param url: The URL of the RSS feed.
        :return: BeautifulSoup object of the parsed XML.
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'xml')
            logger.info(f"Successfully fetched feed from {url}.")
            return soup
        except Exception as e:
            logger.error(f"Error fetching feed from {url}: {e}")
            raise

    def get_session(self):
        """
        Returns a database session from the DatabaseContext.
        Note: Subclasses can also use context managers (e.g. "with self.db_context.session() as session:")
        """
        return self.db_context.session().__enter__()

    def process_feed(self, feed_url, category_id):
        new_articles_count = 0
        updated_articles_count = 0
        updated_articles_details = []
        try:
            soup = self.fetch_feed(feed_url)
            items = soup.find_all('item')
            logger.info(f"Found {len(items)} items in feed {feed_url}.")
            with self.db_context.session() as session:
                for item in items:
                    item_data = self.parse_item(item, category_id)
                    result, detail = self.upsert_item(item_data, session)
                    if result == 'new':
                        new_articles_count += 1
                    elif result == 'updated':
                        updated_articles_count += 1
                        updated_articles_details.append(detail)  # detail: (title, old_date, new_date)
                session.commit()
                logger.info(f"Successfully processed feed: {feed_url}")
        except Exception as e:
            logger.error(f"Error in process_feed for {feed_url}: {e}")
            raise
        return new_articles_count, updated_articles_count, updated_articles_details


    def process_multiple_feeds(self, feeds):
        """
        Processes multiple feeds.
        :param feeds: List of tuples (feed_url, category_id)
        """
        for feed_url, category_id in feeds:
            try:
                self.process_feed(feed_url, category_id)
            except Exception as e:
                logger.error(f"Error processing feed {feed_url}: {e}")

    @abstractmethod
    def parse_item(self, item, category_id):
        """
        Abstract method to parse a single RSS feed item.
        Subclasses must implement this to extract the necessary fields.
        :param item: A BeautifulSoup element corresponding to an <item>.
        :param category_id: Category identifier associated with the item.
        :return: Dictionary of parsed item data.
        """
        pass



    def upsert_item(self, item_data, session):
        try:
            if self.model is None:
                raise Exception("Model not set in parser. Ensure self.model is defined in the subclass.")
            
            stmt = insert(self.model).values(**item_data)
            # Use the unique index on url
            stmt = stmt.on_conflict_do_update(
                index_elements=[self.model.url],
                set_=item_data,
                where=(self.model.pub_date != stmt.excluded.pub_date)
            ).returning(self.model.pub_date)
            
            result = session.execute(stmt)
            session.commit()
            
            # Optionally, inspect result.fetchone() if needed for logging
            returned_pub_date = result.scalar()  # This is the new pub_date if update happened, or None if no update
            if returned_pub_date is None:
                # No update took place because the pub_date was the same.
                # logger.info(f"No update needed for item: {item_data.get('title')}")
                return 'unchanged', None
            else:
                logger.info(f"Upserted item: {item_data.get('title')}")
                # You can decide here how to report "new" vs "updated"
                # For example, if an existing row was found, treat it as "updated"
                return 'updated', (item_data.get('title'), None, item_data.get('pub_date'))
        except Exception as e:
            logger.error(f"Error upserting item with url {item_data.get('url')}: {e}")
            raise



    def is_update_needed(self, existing, new_data):
        """
        Compares an existing record with new data to decide if an update is required.
        For example, by checking if the publication date has changed.
        :param existing: Existing database record.
        :param new_data: Dictionary with new data.
        :return: Boolean indicating whether an update is necessary.
        """
        if existing.pub_date and new_data.get('pub_date'):
            return existing.pub_date != new_data.get('pub_date')
        return existing.pub_date != new_data.get('pub_date')
    
    
    def run_feeds(self, feeds):
        total_new = 0
        total_updated = 0
        total_updated_details = []
        for category_id, feed_url in feeds:
            try:
                new_count, updated_count, updated_details = self.process_feed(feed_url, category_id)
                total_new += new_count
                total_updated += updated_count
                total_updated_details.extend(updated_details)
            except Exception as e:
                logger.error(f"Error processing feed for category {category_id} at {feed_url}: {e}")
        print("\nFinal Report:")
        print(f"Newly added articles: {total_new}")
        print(f"Updated articles: {total_updated}")
        if total_updated_details:
            print("\nDetails of updated articles:")
            for title, old_date, new_date in total_updated_details:
                print(f" - Article '{title}': pub_date in DB: {old_date}, pub_date online: {new_date}")
        print("All articles processed and committed successfully.")


    @abstractmethod
    def run(self):
        """
        Abstract main method that should be implemented by child classes.
        Typically, this method will call process_feed() (or process_multiple_feeds()) for each feed.
        """
        raise NotImplementedError("Subclasses must implement the run() method.")


## [text](../news_aggregator/portals/modules/portal_db.py)
from db_scripts.db_context import DatabaseContext
from sqlalchemy import text

def fetch_portal_id_by_prefix(portal_prefix, env='dev'):
    """
    Fetches the portal_id from the news_portals table for a given portal prefix.
    """
    db_context = DatabaseContext.get_instance(env)
    with db_context.session() as session:
        result = session.execute(
            text("SELECT portal_id FROM public.news_portals WHERE portal_prefix = :prefix"),
            {'prefix': portal_prefix}
        ).fetchone()
        if result:
            return result[0]
        raise Exception(f"Portal with prefix '{portal_prefix}' not found.")

def get_active_categories(portal_prefix, env='dev'):
    """
    Returns active categories for the given portal.
    The query is encapsulated in this module so portal-specific parsers do not contain SQL.
    """
    db_context = DatabaseContext.get_instance(env)
    with db_context.session() as session:
        sql = f"""
            SELECT category_id, atom_link 
            FROM {portal_prefix}.categories 
            WHERE is_active = true AND atom_link IS NOT NULL
        """
        result = session.execute(text(sql)).fetchall()
    return result


## [text](../news_aggregator/portals/modules/rss_parser_utils.py)
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from portals.modules.keyword_extractor import KeywordExtractor
from portals.modules.logging_config import setup_script_logging

# Configure logger using the shared logging configuration.
logger = setup_script_logging(__file__)

# Instantiate a shared keyword extractor so it's not recreated for each item
keyword_extractor = KeywordExtractor()

def parse_rss_item(item, category_id):
    """
    Parses a generic RSS <item> element and extracts common fields.

    :param item: BeautifulSoup element representing an RSS <item>
    :param category_id: The category ID associated with this item
    :return: Dictionary with extracted data
    """
    title_tag = item.find('title')
    title = title_tag.text.strip() if title_tag else 'Untitled'

    link_tag = item.find('link')
    link = link_tag.text.strip() if link_tag else ""  # Leave empty if not found

    guid_tag = item.find('guid')
    guid = guid_tag.text.strip() if guid_tag else ""  # Leave empty if not found

    description_tag = item.find('description')
    description = description_tag.text.strip() if description_tag else None
    content = None  # Content remains empty

    pub_date_tag = item.find('pubDate')
    pub_date = None
    if pub_date_tag:
        pub_date_str = pub_date_tag.text.strip()
        try:
            pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z').astimezone(timezone.utc)
        except Exception as e:
            logger.warning(f"Failed to parse pub_date '{pub_date_str}': {e}")
            pub_date = None

    authors = []
    keywords = keyword_extractor.extract_keywords(title) if title else []

    # Extract image URL from <media:thumbnail> elements
    image_url = None
    media_thumbnails = item.find_all('media:thumbnail')
    if media_thumbnails:
        valid_thumbnails = []
        for thumb in media_thumbnails:
            url = thumb.get('url')
            width = thumb.get('width')
            if url and width and width.isdigit():
                valid_thumbnails.append((url, int(width)))
        if valid_thumbnails:
            image_url = max(valid_thumbnails, key=lambda x: x[1])[0]

    reading_time = None  # Keep reading_time as None since content is not used.

    return {
        'title': title,
        'url': link,
        'guid': guid,
        'category_id': category_id,
        'description': description,
        'content': content,
        'author': authors,
        'pub_date': pub_date,
        'keywords': keywords,
        'reading_time_minutes': reading_time,
        'language_code': 'en',
        'image_url': image_url,
        'sentiment_score': 0.0,
        'share_count': 0,
        'view_count': 0,
        'comment_count': 0
    }


Great, thanks for sharing all the details! To make sure I set up the Dagster orchestration exactly as you need, I have a few clarifying questions:

Pipeline Structure:

You want each portal to have its own Dagster job (pipeline) that consists of three sequential operations:
Category Parser
Article Parser
Article Content Updater
Is that correct?
Yes.

Scheduling:

You mentioned you prefer to use Dagster’s scheduler for now. Should each portal’s job be scheduled to run every hour (with no overlapping runs for the same portal)?
Yes. Each portals' job could be scheduled lets say 7minutes one from another. 
For example:
abc job - 01:00
nyt job - 01:07
reuters job - 01:014
..and so on. 

Script Integration:

Currently, your scripts are fully functional. Would you like to wrap these scripts as Python functions (ops) within Dagster, or do you prefer invoking them as subprocess commands?
Which is beter?

Do you have any preference on handling environment configurations (like dev/prod) through Dagster’s configuration?
Yes. Current scripts are dev environmnet, but prod should be same only with different configuration (database location)

Dependencies and Execution Flow:

The article content updater already checks the status table for new URLs, so no extra dependency logic is needed there, correct?
Yes.
If one of the steps fails (for example, if the category parser fails), should the subsequent steps be skipped for that run, or do you have another fallback mechanism in mind?
If category parser fails it should warn about that and proceed with articles parser, if article parser fails it should fail and report on that. 
Article content updater cannot run if article parser didnt run first. 

Error Handling and Notifications:

Do you want any additional error handling or notification (e.g., email alerts) integrated into the Dagster pipelines, or is the internal logging within your scripts sufficient?
At this point internal logging within script is ok. 

I need very detailed and small steps in regards with setting everything up in Dagster. Giving me Dagster script is not enough. 
I never used Dagster before I just installed it via pip install dagster dagit
and It seems that installation went ok.
