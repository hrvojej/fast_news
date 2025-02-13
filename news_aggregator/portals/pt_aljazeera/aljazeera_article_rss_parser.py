#!/usr/bin/env python
import argparse
import sys
import os
from uuid import UUID
from urllib.parse import urlparse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

# Add package root to path (adjust if needed)
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from portals.modules.base_parser import BaseRSSParser
from portals.modules.portal_db import fetch_portal_id_by_prefix
from portals.modules.rss_parser_utils import parse_rss_item
from portals.modules.logging_config import setup_script_logging
from db_scripts.models.models import create_portal_article_model, create_portal_category_model

logger = setup_script_logging(__file__)

# Dynamically create models for the portal.
AlJazeeraCategory = create_portal_category_model("pt_aljazeera")
AlJazeeraArticle = create_portal_article_model("pt_aljazeera")


class AlJazeeraRSSArticlesParser(BaseRSSParser):
    FEED_URL = "https://www.aljazeera.com/xml/rss/all.xml"

    def __init__(self, portal_id: UUID, env: str = 'dev'):
        super().__init__(portal_id, env)
        self.model = AlJazeeraArticle
        # In-memory cache for category lookups/creation.
        self.category_cache = {}
        # List to hold URLs of articles for which category matching failed.
        self.unmatched_urls = []

    def get_or_create_category(self, session, category_text, derived_slug, derived_name, derived_link, category_cache):
        """
        Returns the category_id by first checking the provided category (if any),
        then the derived slug. It consults the in‑memory cache, then the DB,
        and finally inserts a new category if needed.
        """
        if category_text:
            result = session.execute(
                text("SELECT category_id, slug FROM pt_aljazeera.categories WHERE name = :name"),
                {'name': category_text}
            ).fetchone()
            if result:
                cat_id, cat_slug = result
                category_cache[cat_slug] = cat_id
                return cat_id

        if derived_slug in category_cache:
            return category_cache[derived_slug]

        result = session.execute(
            text("SELECT category_id FROM pt_aljazeera.categories WHERE slug = :slug"),
            {'slug': derived_slug}
        ).fetchone()
        if result:
            cat_id = result[0]
            category_cache[derived_slug] = cat_id
            return cat_id

        new_category = AlJazeeraCategory(
            name=derived_name,
            slug=derived_slug,
            portal_id=self.portal_id,
            path=derived_link,
            level=1,
            description=None,
            link=derived_link,
            atom_link=derived_link,
            is_active=True
        )
        session.add(new_category)
        try:
            session.commit()
        except IntegrityError as e:
            session.rollback()
            result = session.execute(
                text("SELECT category_id FROM pt_aljazeera.categories WHERE slug = :slug"),
                {'slug': derived_slug}
            ).fetchone()
            if result:
                cat_id = result[0]
                category_cache[derived_slug] = cat_id
                return cat_id
            else:
                raise e
        cat_id = new_category.category_id
        category_cache[derived_slug] = cat_id
        return cat_id

    def parse_item(self, item, session):
        """
        Implements the abstract method required by BaseRSSParser.
        This method follows the same logic as before (without altering the expected
        output): it uses the generic parse_rss_item utility and applies Al Jazeera–specific
        category handling while setting 'content' and 'reading_time_minutes' to None.
        """
        parsed_data = parse_rss_item(item, None)
        url = parsed_data.get('url')
        if not url:
            logger.error("Parsed item is missing URL; skipping.")
            return None

        # Derive category info from URL.
        parsed_url = urlparse(url)
        path_segments = [seg for seg in parsed_url.path.split('/') if seg]
        if len(path_segments) < 2:
            logger.warning(f"URL does not contain enough segments for category derivation: {url}")
            self.unmatched_urls.append(url)
            return None
        phrase1, phrase2 = path_segments[0], path_segments[1]
        derived_category_name = f"{phrase1.capitalize()}_{phrase2.capitalize()}"
        derived_category_slug = derived_category_name.lower()
        derived_category_link = f"{parsed_url.scheme}://{parsed_url.netloc}/{phrase1}/{phrase2}/"

        # Use provided <category> element if available.
        category_elem = item.find('category')
        category_text = category_elem.text.strip() if category_elem and category_elem.text.strip() else None

        # Get or create the category.
        category_id = self.get_or_create_category(
            session,
            category_text,
            derived_category_slug,
            derived_category_name,
            derived_category_link,
            self.category_cache
        )
        if not category_id:
            logger.warning(f"Article '{parsed_data.get('title')}' has an unmatched category. URL: {url}")
            self.unmatched_urls.append(url)
            return None

        parsed_data['category_id'] = category_id

        # Remove fields that should remain uncalculated for Al Jazeera.
        parsed_data['content'] = None
        parsed_data['reading_time_minutes'] = None

        return parsed_data

    def run(self):
        """
        Fetches the RSS feed and processes each <item> using a single DB session.
        Articles with unmatched categories are skipped (and their URLs logged).
        """
        new_articles_count = 0
        updated_articles_count = 0
        updated_articles_details = []

        soup = self.fetch_feed(self.FEED_URL)
        items = soup.find_all('item')
        logger.info(f"Found {len(items)} items in feed {self.FEED_URL}.")

        with self.db_context.session() as session:
            for item in items:
                data = self.parse_item(item, session)
                if data is None:
                    continue
                try:
                    result, detail = self.upsert_item(data, session)
                    if result == 'new':
                        new_articles_count += 1
                    elif result == 'updated':
                        updated_articles_count += 1
                        updated_articles_details.append(detail)
                except Exception as e:
                    logger.error(f"Error upserting item with URL {data.get('url')}: {e}")
                    continue
            session.commit()

        logger.info("Final Report:")
        logger.info(f"Newly added articles: {new_articles_count}")
        logger.info(f"Updated articles: {updated_articles_count}")
        if updated_articles_details:
            logger.info("Details of updated articles:")
            for title, old_date, new_date in updated_articles_details:
                logger.info(f" - Article '{title}': pub_date in DB: {old_date}, pub_date online: {new_date}")
        if self.unmatched_urls:
            logger.info("Articles with unmatched categories (no corresponding DB entry):")
            for url in self.unmatched_urls:
                logger.info(url)


def main():
    argparser = argparse.ArgumentParser(description="Al Jazeera RSS Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    portal_id = fetch_portal_id_by_prefix("pt_aljazeera", env=args.env)
    parser = AlJazeeraRSSArticlesParser(portal_id=portal_id, env=args.env)
    parser.run()


if __name__ == "__main__":
    main()
