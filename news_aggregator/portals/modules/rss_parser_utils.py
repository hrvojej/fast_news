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
