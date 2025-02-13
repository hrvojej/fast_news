#!/usr/bin/env python
import argparse
from uuid import UUID
import sys
import os
from datetime import datetime

# Add the package root (e.g., news_aggregator) to sys.path if needed.
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from portals.modules.base_parser import BaseRSSParser
from portals.modules.portal_db import fetch_portal_id_by_prefix, get_active_categories
from portals.modules.rss_parser_utils import parse_rss_item  # You can modify or extend this if needed.
from db_scripts.models.models import create_portal_article_model, create_portal_category_model
from portals.modules.logging_config import setup_script_logging
from portals.modules.keyword_extractor import KeywordExtractor  # New import

logger = setup_script_logging(__file__)
keyword_extractor = KeywordExtractor()  # Instantiate the keyword extractor once

# Dynamically create models for the Fox News portal.
FoxNewsCategory = create_portal_category_model("pt_fox")
FoxNewsArticle = create_portal_article_model("pt_fox")


class FoxNewsRSSArticlesParser(BaseRSSParser):
    def __init__(self, portal_id: UUID, env: str = 'dev'):
        super().__init__(portal_id, env)
        self.model = FoxNewsArticle


    def parse_item(self, item, category_id):
        """
        Parse a single Fox News RSS item.
        """
        title = item.find('title').text.strip() if item.find('title') else 'Untitled'
        link = item.find('link').text.strip() if item.find('link') else 'https://www.foxnews.com'

        # Skip video URLs.
        if link.startswith("https://www.foxnews.com/video/"):
            logger.info("Skipping video URL: %s", link)
            return None

        guid = item.find('guid').text.strip() if item.find('guid') else link  # Fallback to link if no GUID

        description = item.find('description').text.strip() if item.find('description') else None
        content_tag = item.find('content:encoded')
        content = content_tag.text.strip() if content_tag else description

        pub_date_str = item.find('pubDate').text.strip() if item.find('pubDate') else None
        pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z') if pub_date_str else datetime.utcnow()

        authors = [creator.text.strip() for creator in item.find_all('dc:creator')] or []
        # Use the KeywordExtractor to derive keywords from the title.
        keywords = keyword_extractor.extract_keywords(title) if title else []

        # Get image from media:content elements (choosing the one with the highest width)
        image_url = None
        media_contents = item.find_all('media:content')
        if media_contents:
            valid_media = [(m.get('url'), int(m.get('width')))
                        for m in media_contents
                        if m.get('width') and m.get('width').isdigit()]
            if valid_media:
                image_url = max(valid_media, key=lambda x: x[1])[0]

        # Calculate a rough reading time (assume 200 words per minute)
        text_content = f"{title} {description or ''} {content or ''}"
        word_count = len(text_content.split())
        reading_time = max(1, round(word_count / 200))

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
            'sentiment_score': 0.0,  # Default neutral sentiment
            'share_count': 0,
            'view_count': 0,
            'comment_count': 0
        }


    def run(self):
        """
        Retrieve all active categories (feeds) for Fox News and process each.
        """
        feeds = get_active_categories("pt_fox", self.env)
        self.run_feeds(feeds)


def main():
    argparser = argparse.ArgumentParser(description="Fox News RSS Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    portal_id = fetch_portal_id_by_prefix("pt_fox", env=args.env)
    parser = FoxNewsRSSArticlesParser(portal_id=portal_id, env=args.env)
    parser.run()


if __name__ == "__main__":
    main()
