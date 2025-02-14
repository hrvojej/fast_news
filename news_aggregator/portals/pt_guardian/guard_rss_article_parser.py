#!/usr/bin/env python
import argparse
import os
import sys
from uuid import UUID
import email.utils
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
import nltk
from sqlalchemy import text

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Import common modules and helpers
from portals.modules.base_parser import BaseRSSParser
from portals.modules.portal_db import fetch_portal_id_by_prefix, get_active_categories
from portals.modules.logging_config import setup_script_logging
from db_scripts.models.models import create_portal_category_model, create_portal_article_model

logger = setup_script_logging(__file__)

# Dynamically create models for the Guardian portal.
GuardianCategory = create_portal_category_model("pt_guardian")
GuardianArticle = create_portal_article_model("pt_guardian")


class KeywordExtractor:
    """Extracts keywords from text using SentenceTransformer embeddings."""

    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        try:
            self.stop_words = set(stopwords.words('english'))
        except LookupError:
            nltk.download('stopwords')
            self.stop_words = set(stopwords.words('english'))

    def extract_keywords(self, text: str, max_keywords: int = 5):
        if not text:
            return []
        chunks = text.split()
        if not chunks:
            return []
        text_embedding = self.model.encode([text])
        chunk_embeddings = self.model.encode(chunks)
        similarities = cosine_similarity(text_embedding, chunk_embeddings).flatten()
        scored_chunks = sorted(
            [(chunks[i], score) for i, score in enumerate(similarities)],
            key=lambda x: x[1],
            reverse=True
        )
        keywords = []
        seen = set()
        for word, _ in scored_chunks:
            word = word.lower()
            if word not in self.stop_words and word not in seen and len(word) > 2:
                keywords.append(word)
                seen.add(word)
            if len(keywords) >= max_keywords:
                break
        return keywords


class GuardianRSSArticlesParser(BaseRSSParser):
    """
    Guardian RSS Articles Parser

    Fetches articles from Guardian RSS feeds and stores them in the database.
    """

    def __init__(self, portal_id: UUID, env: str = 'dev'):
        super().__init__(portal_id, env)
        self.model = GuardianArticle
        self.keyword_extractor = KeywordExtractor()

    def parse_date(self, date_str: str) -> datetime:
        """Parse a date string in RFC 2822 format."""
        if not date_str:
            return datetime.utcnow()
        try:
            time_tuple = email.utils.parsedate_tz(date_str)
            if time_tuple:
                timestamp = email.utils.mktime_tz(time_tuple)
                return datetime.fromtimestamp(timestamp)
        except Exception as e:
            logger.error(f"Error parsing date '{date_str}': {e}")
        return datetime.utcnow()

    def parse_item(self, item, category_id):
        """
        Parse a single RSS item into a dictionary of article data.
        This method will be used by the base parser's feed loop.
        """
        title = item.find('title').text.strip() if item.find('title') else 'Untitled'
        link = item.find('link').text.strip() if item.find('link') else 'https://www.theguardian.com'
        guid = item.find('guid').text.strip() if item.find('guid') else link

        description = item.find('description').text.strip() if item.find('description') else None
        content = description  # Use description as fallback for content
        pub_date_str = item.find('pubDate').text.strip() if item.find('pubDate') else None
        pub_date = self.parse_date(pub_date_str)

        authors = []
        dc_creator = item.find('dc:creator')
        if dc_creator:
            authors = [author.strip() for author in dc_creator.text.split(',')]

        # Extract keywords from title using the keyword extractor
        keywords = self.keyword_extractor.extract_keywords(title) if title else []

        # Extract image URL from media:content (if available)
        image_url = None
        media_contents = item.find_all('media:content')
        if media_contents:
            valid_media = [
                (m.get('url'), int(m.get('width', 0)))
                for m in media_contents
                if m.get('url') and m.get('width')
            ]
            if valid_media:
                image_url = max(valid_media, key=lambda x: x[1])[0]

        # Estimate reading time (assuming 200 words per minute)
        text_content = f"{title} {description or ''} {content or ''}"
        word_count = len(text_content.split())
        reading_time = max(1, round(word_count / 200))

        article_data = {
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
        return article_data

    def run(self):
        """Fetch and process all active Guardian RSS feeds."""
        feeds = get_active_categories("pt_guardian", self.env)
        self.run_feeds(feeds)


def main():
    """Script entry point."""
    argparser = argparse.ArgumentParser(description="Guardian RSS Articles Parser")
    argparser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = argparser.parse_args()

    try:
        portal_id = fetch_portal_id_by_prefix("pt_guardian", env=args.env)
        parser = GuardianRSSArticlesParser(portal_id=portal_id, env=args.env)
        parser.run()
        logger.info("Article processing completed successfully")
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
