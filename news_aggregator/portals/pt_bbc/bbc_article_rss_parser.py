#!/usr/bin/env python
"""
BBC RSS Articles Parser
Fetches and stores BBC RSS feed articles using SQLAlchemy ORM.
Timestamps are normalized to UTC for consistent storage and comparison,
and updates occur only when there's an actual change in publication time.
Keyword extraction is performed using a shared instance from rss_parser_utils.
Now, the parser uses URL as the unique key (guid is set equal to URL).
"""

import sys
import os
import argparse
from uuid import UUID
from datetime import datetime, timezone



# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Import dynamic model factory functions for categories and articles
from db_scripts.models.models import create_portal_category_model, create_portal_article_model
BBCCategory = create_portal_category_model("pt_bbc")
BBCArticle = create_portal_article_model("pt_bbc")

# Import portal database utilities
from portals.modules.portal_db import fetch_portal_id_by_prefix, get_active_categories

# Import base RSS parser and shared logging configuration
from portals.modules.base_parser import BaseRSSParser
from portals.modules.logging_config import setup_script_logging
logger = setup_script_logging(__file__)

# Import the shared KeywordExtractor instance from rss_parser_utils
from portals.modules.rss_parser_utils import keyword_extractor


class BBCRSSArticlesParser(BaseRSSParser):
    def __init__(self, portal_id: UUID, env: str = 'dev'):
        super().__init__(portal_id, env)
        self.model = BBCArticle

    def parse_item(self, item, category_id):
        """
        Parse a single BBC RSS feed item.
        Uses URL as the primary unique key.
        """
        # Extract required fields.
        title = item.find('title').text.strip() if item.find('title') else 'Untitled'
        url = item.find('link').text.strip() if item.find('link') else 'https://www.bbc.com'
        # Set guid equal to url since we rely only on the URL as unique identifier.
        guid = url

        # Extract optional fields.
        description = item.find('description').text.strip() if item.find('description') else None
        content = description  # For BBC, content is set equal to description.

        # Process pubDate with UTC normalization.
        pub_date = None
        pub_date_str = item.find('pubDate').text.strip() if item.find('pubDate') else None
        if pub_date_str:
            try:
                # Try parsing with timezone offset.
                pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
            except Exception as e:
                try:
                    # Replace 'GMT' with '+0000' if necessary.
                    pub_date_str_mod = pub_date_str.replace('GMT', '+0000')
                    pub_date = datetime.strptime(pub_date_str_mod, '%a, %d %b %Y %H:%M:%S %z')
                except Exception as e:
                    logger.error(f"Error parsing pubDate '{pub_date_str}': {e}")
                    pub_date = datetime.utcnow().replace(tzinfo=timezone.utc)
        else:
            pub_date = datetime.utcnow().replace(tzinfo=timezone.utc)

        # Extract keywords using the shared keyword_extractor.
        keywords = keyword_extractor.extract_keywords(title) if title else []

        # BBC-specific extraction for image URL.
        image_url = None
        thumbnail = item.find('media:thumbnail')
        if thumbnail:
            image_url = thumbnail.get('url')

        # Calculate reading time (estimate: 200 words per minute).
        text_content = f"{title} {description or ''}"
        word_count = len(text_content.split())
        reading_time = max(1, round(word_count / 200)) if word_count > 0 else 1

        return {
            'title': title,
            'url': url,
            'guid': guid,  # Retained for completeness, but not used for uniqueness.
            'category_id': category_id,
            'description': description,
            'content': content,
            'author': [],
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


    def run(self):
        """
        Main method to process all active BBC RSS feeds.
        """
        feeds = get_active_categories("pt_bbc", self.env)
        self.run_feeds(feeds)


def main():
    argparser = argparse.ArgumentParser(description="BBC RSS Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    portal_id = fetch_portal_id_by_prefix("pt_bbc", env=args.env)
    parser = BBCRSSArticlesParser(portal_id=portal_id, env=args.env)
    parser.run()


if __name__ == "__main__":
    main()
