#!/usr/bin/env python
import argparse
import sys
import os

# Add package root to path (same pattern as ABC example)
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from portals.modules.portal_db import fetch_portal_id_by_prefix
from db_scripts.db_context import DatabaseContext
from portals.modules.logging_config import setup_script_logging
from portals.modules.keyword_extractor import KeywordExtractor
from db_scripts.models.models import create_portal_article_model, create_portal_category_model

logger = setup_script_logging(__file__)
keyword_extractor = KeywordExtractor()

def update_keywords_for_all_articles(session, FoxNewsArticle, batch_size=100):
    """
    Updates the keywords for every article in the pt_fox.articles table.
    Processes articles in batches.
    """
    query = session.query(FoxNewsArticle)
    total = query.count()
    logger.info(f"Updating keywords for {total} articles.")

    offset = 0
    while offset < total:
        articles = query.offset(offset).limit(batch_size).all()
        if not articles:
            break

        for article in articles:
            if article.title:
                new_keywords = keyword_extractor.extract_keywords(article.title)
            else:
                new_keywords = []
            article.keywords = new_keywords
            logger.info(f"Article ID {article.article_id}: updated keywords to {new_keywords}")

        session.commit()
        offset += batch_size
        logger.info(f"Processed {min(offset, total)}/{total} articles.")

def main():
    argparser = argparse.ArgumentParser(description="Fox News Articles Keywords Updater")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    # Mimic ABC script: fetch the portal_id (even if not directly used here)
    portal_id = fetch_portal_id_by_prefix("pt_fox", env=args.env)

    # Create and register the category model so that SQLAlchemy knows about pt_fox.categories.
    FOXCategory = create_portal_category_model("pt_fox")
    # Create the Fox News article model for the "pt_fox" portal.
    FoxNewsArticle = create_portal_article_model("pt_fox")

    # Obtain the database session using the project's helper function.
    session = DatabaseContext.get_instance(env=args.env).session().__enter__()

    try:
        update_keywords_for_all_articles(session, FoxNewsArticle)
        logger.info("Keyword update migration completed successfully.")
    except Exception as e:
        logger.error(f"An error occurred during migration: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
