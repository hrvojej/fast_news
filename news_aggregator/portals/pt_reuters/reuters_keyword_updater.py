#!/usr/bin/env python
"""
Script to update missing keywords in pt_reuters.articles based on the article title.
It queries the database for articles and, if an article's keywords are missing,
it extracts keywords using the shared KeywordExtractor instance and updates the record.
"""

import os
import sys

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

import argparse
from portals.modules.logging_config import setup_script_logging
from portals.modules.rss_parser_utils import keyword_extractor
from db_scripts.db_context import DatabaseContext
from db_scripts.models.models import create_portal_article_model, create_portal_category_model

logger = setup_script_logging(__file__)

def main():
    argparser = argparse.ArgumentParser(
        description="Update missing keywords for pt_reuters articles."
    )
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    # Initialize the database context.
    db_context = DatabaseContext.get_instance(args.env)
    
    # Dynamically create the models for Reuters.
    ReutersArticle = create_portal_article_model("pt_reuters")
    ReutersCategory = create_portal_category_model("pt_reuters")
    
    # Ensure that the metadata for ReutersArticle includes the categories table.
    # This is needed because ReutersArticle has a foreign key pointing to pt_reuters.categories.
    if ReutersCategory.__table__.name not in ReutersArticle.__table__.metadata.tables:
        ReutersArticle.__table__.metadata._add_table(
            ReutersCategory.__table__.name,
            ReutersCategory.__table__.schema,
            ReutersCategory.__table__
        )

    with db_context.session() as session:
        # Optionally, you could filter only articles where keywords are missing.
        articles = session.query(ReutersArticle).all()
        logger.info(f"Found {len(articles)} article(s) to process.")
        update_count = 0

        for article in articles:
            # Adjust this check based on how keywords are stored (list, string, etc.)
            if not article.keywords or (isinstance(article.keywords, str) and article.keywords.strip() == ""):
                if article.title:
                    new_keywords = keyword_extractor.extract_keywords(article.title)
                    article.keywords = new_keywords
                    logger.info(f"Article '{article.title}' updated with keywords: {new_keywords}")
                    update_count += 1
                else:
                    logger.warning(f"Article with GUID {article.guid} has no title; skipping keyword extraction.")
        session.commit()
        logger.info(f"Keyword update completed. {update_count} article(s) updated.")

if __name__ == "__main__":
    main()
