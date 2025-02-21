import os
import sys
import argparse
from datetime import datetime, timezone
from bs4 import BeautifulSoup

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Import necessary modules
from portals.modules.logging_config import setup_script_logging
from db_scripts.models.models import create_portal_category_model, create_portal_article_model, create_portal_article_status_model
from db_scripts.db_context import DatabaseContext
from portals.modules.article_updater_utils import (
    random_sleep,
    fetch_html,
    update_status_error,
    update_status_success,
    get_articles_to_update,
    log_update_summary
)

# Set up logging
logger = setup_script_logging(__file__)

# Define dynamic models
ALJCategory = create_portal_category_model("pt_aljazeera")
ALJArticle = create_portal_article_model("pt_aljazeera")
ALJArticleStatus = create_portal_article_status_model("pt_aljazeera")

class AlJazeeraArticleUpdater:
    def __init__(self, env='dev'):
        self.env = env
        self.logger = logger
        self.db_context = DatabaseContext.get_instance(env)
        self.ALJArticle = ALJArticle
        self.ALJArticleStatus = ALJArticleStatus
        self.counters = {
            "total": 0,
            "up_to_date": 0,
            "to_update": 0,
            "fetched": 0,
            "updated": 0,
            "failed": 0
        }
        self.error_counts = {}
        self.context = {"consecutive_403_count": 0}

    def update_article(self, article_info):
        self.logger.info(f"Processing article: {article_info['url']}")
        fetched_at = datetime.now(timezone.utc)
        html_content, fetch_error = fetch_html(article_info['url'], self.logger, context=self.context)

        if html_content is None:
            error_type = fetch_error if fetch_error else "UNKNOWN_FETCH"
            with self.db_context.session() as session:
                update_status_error(session, self.ALJArticleStatus, article_info['url'], fetched_at, article_info['pub_date'], error_type, status_id=article_info.get('status_id'), logger=self.logger)
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            self.counters["failed"] += 1
            return False

        soup = BeautifulSoup(html_content, 'html.parser')
        article_div = soup.find('div', class_='wysiwyg wysiwyg--all-content')
        
        if not article_div:
            article_div = soup.find('p', class_='article__subhead u-inline')

        if not article_div:
            error_type = "NO_CONTENT"
            with self.db_context.session() as session:
                update_status_error(session, self.ALJArticleStatus, article_info['url'], fetched_at, article_info['pub_date'], error_type, status_id=article_info.get('status_id'), logger=self.logger)
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            self.counters["failed"] += 1
            return False

        new_content = article_div.get_text(separator="\n").strip()
        if not new_content:
            error_type = "EMPTY_CONTENT"
            with self.db_context.session() as session:
                update_status_error(session, self.ALJArticleStatus, article_info['url'], fetched_at, article_info['pub_date'], error_type, status_id=article_info.get('status_id'), logger=self.logger)
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            self.counters["failed"] += 1
            return False

        with self.db_context.session() as session:
            article_obj = session.query(self.ALJArticle).filter(self.ALJArticle.article_id == article_info["article_id"]).first()
            if article_obj:
                article_obj.content = new_content
                self.logger.info(f"Article {article_info['url']} content updated.")
            else:
                self.logger.info(f"Article {article_info['article_id']} not found.")
                self.counters["failed"] += 1
                return False

            parsed_at = datetime.now(timezone.utc)
            update_status_success(session, self.ALJArticleStatus, article_info['url'], fetched_at, parsed_at, article_info['pub_date'], status_id=article_info.get('status_id'), logger=self.logger)
        
        self.counters["fetched"] += 1
        self.counters["updated"] += 1
        return True

    def run(self):
        self.logger.info("Starting Al Jazeera Article Updater.")
        with self.db_context.session() as session:
            articles_to_update, summary = get_articles_to_update(session, "pt_aljazeera.articles", "pt_aljazeera.article_status", self.logger)
        
        self.counters.update(summary)
        self.logger.info(f"Total articles marked for update: {len(articles_to_update)}")

        for idx, article in enumerate(articles_to_update, start=1):
            self.logger.info(f"\033[1mProcessing article {idx}/{len(articles_to_update)} with URL: {article['url']}\033[0m")
            self.update_article(article)
            random_sleep(self.logger)

        log_update_summary(self.logger, self.counters, self.error_counts)


def main():
    parser = argparse.ArgumentParser(description="Al Jazeera Article Updater")
    parser.add_argument('--env', choices=['dev', 'prod'], default='dev', help="Specify the environment (default: dev)")
    args = parser.parse_args()

    try:
        updater = AlJazeeraArticleUpdater(env=args.env)
        updater.run()
        logger.info("Article content update completed successfully.")
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
