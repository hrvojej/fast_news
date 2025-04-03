# path: fast_news/news_aggregator/nlp/summarizer/summarizer_html.py
"""
Module for HTML processing and file operations for the article summarization system.
"""

import os
import re
import html
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup, Tag, NavigableString
from datetime import datetime

from summarizer_logging import get_logger
from summarizer_config import OUTPUT_HTML_DIR, ensure_output_directory
from summarizer_image import IMAGES_DIR, process_images_in_html, search_and_download_images
from summarizer_db import update_article_summary_details, get_related_articles

from db_scripts.db_context import DatabaseContext



from jinja2 import Environment, FileSystemLoader, select_autoescape

# Compute the base directory of your project (assumes summarizer_html.py is two levels deep in nlp/summarizer)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# Define the template directory path relative to your project structure (note: no extra "web" folder)
TEMPLATE_DIR = os.path.join(BASE_DIR, 'frontend', 'templates')
IMAGES_DIR = os.path.join(BASE_DIR, 'frontend', 'web', 'static', 'images')


jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)
# Register custom filter "split" so the template can split strings
jinja_env.filters['split'] = lambda s, delimiter: s.split(delimiter) if s else []


# Define and register a static_url function for resolving static assets in templates
def static_url(path):
    return "../../static/" + path

jinja_env.globals['static_url'] = static_url

# Initialize logger
logger = get_logger(__name__)

def is_valid_html(text):
    """
    Check if the provided text is valid HTML.
    
    Args:
        text (str): The HTML text to validate
        
    Returns:
        bool: True if valid HTML, False otherwise
    """
    if not text or not isinstance(text, str):
        return False
    
    try:
        soup = BeautifulSoup(text, 'html.parser')
        return bool(soup.find())
    except Exception as e:
        logger.error(f"HTML validation error: {e}")
        return False
    
def get_subfolder_from_url(url):
    """
    Extracts subfolder(s) from the URL.
    Returns a relative path like "us/politics" or "briefing" based on URL segments.
    """
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        # Get non-empty path segments
        segments = [seg for seg in parsed.path.split('/') if seg]
        base_index = 0
        # Look for the date segments.
        # Standard pattern: [year, month, day, ...] or [lang, year, month, day, ...]
        if len(segments) >= 3 and segments[0].isdigit() and len(segments[0]) == 4 \
           and segments[1].isdigit() and len(segments[1]) == 2 \
           and segments[2].isdigit() and len(segments[2]) == 2:
            base_index = 3
        elif len(segments) >= 4 and segments[0].isalpha() \
             and segments[1].isdigit() and len(segments[1]) == 4 \
             and segments[2].isdigit() and len(segments[2]) == 2 \
             and segments[3].isdigit() and len(segments[3]) == 2:
            base_index = 4
        else:
            # If pattern doesn't match, return empty string
            return ""
        # Folder parts are those between the date and the final article slug
        folder_parts = segments[base_index:-1]
        if len(folder_parts) >= 2:
            # Only use the first two segments
            return os.path.join(folder_parts[0], folder_parts[1])
        elif len(folder_parts) == 1:
            return folder_parts[0]
        else:
            return ""
    except Exception as e:
        logger.error(f"Error extracting subfolder from URL: {e}")
        return ""

    

def ensure_proper_classes(soup):
    """
    Ensure that only approved classes are used and elements have appropriate classes.
    This is a validation step to catch any inconsistencies from the Gemini response.
    """
    allowed_classes = [
    # Article structure
    'article-title', 'emphasis-keyword', 'source-attribution', 'label',
    
    # Keywords section
    'keywords-container', 'keywords-heading', 'keywords-tags', 'keyword-pill',
    
    # Entity types
    'named-individual', 'roles-categories', 'orgs-products', 'location', 
    'time-event', 'artistic', 'industry', 'financial', 'key-actions',
    
    # Entity structure
    'entity-overview-heading', 'entity-grid', 'entity-category', 
    'entity-category-title', 'entity-list', 'no-entity',
    
    # Summary elements
    'summary-heading', 'summary-intro', 'key-sentence', 'supporting-point', 
    'transition-text', 'secondary-detail', 'crucial-fact',
    
    # Interesting facts
    'facts-heading', 'facts-container', 'facts-list', 'fact-primary', 
    'fact-secondary', 'fact-conclusion', 'fact-bullet', 'fact-bullet-secondary',
    
    # Legend
    'legend-container', 'legend-heading', 'legend-grid', 'legend-item',
    
    # Separators and misc elements
    'separator', 'divider', 'gradient-divider', 'facts-divider',
    'entity-spacing', 'transition-text', 'date-numeric', 'number-numeric',
    
    # Sentiment analysis classes
    'entity-sentiment', 'entity-name', 'entity-sentiment-details', 'sentiment-positive', 'sentiment-negative', 'entity-summary', 'entity-keywords',
    
    # Topic popularity score elements
    'popularity-container', 'popularity-title', 'popularity-score', 'popularity-number', 'popularity-description',

    # More on topic and related terminology section
    'more-on-topic-heading', 'more-on-topic-container', 'related-terminology-list', 'terminology-item', 'resource-link', 'resource-description', 'more-topic-divider'
    ]

    
    # Check for elements with classes not in the allowed list
    for element in soup.find_all(class_=True):
        element_classes = element.get('class', [])
        if isinstance(element_classes, str):
            element_classes = [element_classes]
        
        # Remove any classes not in the allowed list
        filtered_classes = [cls for cls in element_classes if cls in allowed_classes]
        if filtered_classes:
            element['class'] = filtered_classes
        else:
            # If all classes were invalid, remove the class attribute
            del element['class']
    
    # Element-specific class validation
    
    # Title validation
    for h1 in soup.find_all('h1'):
        if not h1.has_attr('class') or 'article-title' not in h1['class']:
            h1['class'] = ['article-title']
    
    # Source attribution validation
    for p in soup.find_all('p', class_='source-attribution'):
        for span in p.find_all('span'):
            if span.string and ('Source:' in span.string or 'Published:' in span.string):
                if not span.has_attr('class') or 'label' not in span['class']:
                    span['class'] = ['label']
    
    # Keywords container validation
    for div in soup.find_all('div', class_='keywords-container'):
        if not div.find('p', class_='keywords-heading'):
            heading = div.find('p')
            if heading:
                heading['class'] = ['keywords-heading']
                
        tags_container = div.find('div')
        if tags_container and (not tags_container.has_attr('class') or 'keywords-tags' not in tags_container['class']):
            tags_container['class'] = ['keywords-tags']
            
        for span in div.find_all('span'):
            if not span.has_attr('class') and span.parent.name == 'div' and span.parent.get('class') == ['keywords-tags']:
                span['class'] = ['keyword-pill']
    
    # Entity formatting validation
    entity_types = {
        'named-individual': ['strong'],
        'roles-categories': ['strong'],
        'orgs-products': ['strong'],
        'location': ['strong'],
        'time-event': ['strong'],
        'artistic': ['strong'],
        'industry': ['strong'],
        'financial': ['strong'],
        'key-actions': ['strong']
    }
    
    # Check entities have proper formatting
    for entity_class, tag_names in entity_types.items():
        for tag_name in tag_names:
            for tag in soup.find_all(tag_name):
                if tag.string and len(tag.string.strip()) > 0:
                    parent_classes = tag.get('class', [])
                    if not any(cls in parent_classes for cls in entity_types.keys()):
                        # Try to determine what entity type this might be
                        # This is a simplistic approach - you might need more sophisticated entity recognition
                        tag['class'] = [entity_class]
    
    # Ensure summary sections have proper classes
    summary_heading = soup.find('strong', string='Summary:')
    if summary_heading and not summary_heading.has_attr('class'):
        summary_heading['class'] = ['summary-heading']
    
    # Add validation for facts section if needed
    
    return soup

def clean_and_normalize_html(text):
    """
    Clean and normalize HTML content to ensure it's valid.

    Args:
        text (str): The HTML text to clean

    Returns:
        str: Cleaned and normalized HTML
    """
    logger.debug(f"Starting HTML normalization. Original length: {len(text) if text else 0}")

    if not text or not isinstance(text, str):
        logger.warning("Invalid input provided to clean_and_normalize_html.")
        return "<div>No content available</div>"

    try:
        # Extract HTML content from markdown-style code blocks if present
        if "```html" in text:
            try:
                text = text.split('```html')[1].split('```')[0].strip()
                logger.debug("HTML content successfully extracted from markdown code block.")
            except Exception as e:
                logger.warning(f"Failed extracting HTML from markdown block: {e}")

        # Remove markdown-style heading indicators
        text = re.sub(r'^#\s+', '', text, flags=re.MULTILINE)

        # Parse and clean the HTML content
        soup = BeautifulSoup(text, 'html.parser')

        # Remove inline styles
        for tag in soup.find_all(style=True):
            del tag['style']
            logger.debug(f"Removed inline styles from tag: {tag.name}")

        # Ensure correct class usage throughout HTML
        soup = ensure_proper_classes(soup)

        # Check if resulting HTML content is valid and non-empty
        if not soup.find() or not soup.text.strip():
            logger.warning("Resulting HTML is empty or invalid after cleaning.")
            return f"<div>{html.escape(text)}</div>"

        # Ensure HTML is wrapped in a single top-level div
        top_level_elements = [tag for tag in soup.children if isinstance(tag, (Tag, NavigableString))]

        if len(top_level_elements) != 1 or (top_level_elements[0].name != 'div'):
            wrapper_div = soup.new_tag("div")
            for element in top_level_elements:
                wrapper_div.append(element.extract())
            soup = BeautifulSoup(str(wrapper_div), 'html.parser')
            logger.debug("Wrapped HTML content within a single top-level div.")

        cleaned_html = str(soup)
        logger.debug(f"Cleaned HTML (preview 100 chars): {cleaned_html[:100]}...")

        return cleaned_html

    except Exception as e:
        logger.error(f"Exception occurred during HTML cleaning: {e}", exc_info=True)
        return f"<div>{html.escape(text)}</div>"

def extract_summary_fields(clean_html):
    """
    Extract structured fields from the cleaned summary HTML.
    
    Returns a dictionary with:
      - article_title: text from <h1 class="article-title">
      - source_attribution: HTML from <p class="source-attribution">
      - keywords: a list of strings from <span class="keyword-pill">
      - entity_overview: a list of dicts, each with 'category' and 'content' (from entity sections)
      - summary_paragraphs: a list of dicts for summary paragraphs (classes: summary-intro, supporting-point, transition-text, secondary-detail)
      - interesting_facts: a list of dicts for each fact (with its classes and content)
    """
    soup = BeautifulSoup(clean_html, 'html.parser')
    result = {}

    # Article Title
    title_tag = soup.find('h1', class_='article-title')
    result['article_title'] = title_tag.get_text(strip=True) if title_tag else ''

    # Source Attribution
    source_tag = soup.find('p', class_='source-attribution')
    result['source_attribution'] = str(source_tag) if source_tag else ''

    # Keywords
    keywords = []
    keywords_container = soup.find('div', class_='keywords-container')
    if keywords_container:
        for span in keywords_container.find_all('span', class_='keyword-pill'):
            keywords.append(span.get_text(strip=True))
    result['keywords'] = keywords

    # Entity Overview
    entity_overview = []
    entity_grid = soup.find('div', class_='entity-grid')
    if entity_grid:
        for category in entity_grid.find_all('div', class_='entity-category'):
            category_title_tag = category.find(class_='entity-category-title')
            category_title = category_title_tag.get_text(strip=True) if category_title_tag else ''
            entity_list_tag = category.find('p', class_='entity-list')
            entity_list = str(entity_list_tag) if entity_list_tag else ''
            entity_overview.append({'category': category_title, 'content': entity_list})
    result['entity_overview'] = entity_overview

    # Summary Paragraphs
    summary_paragraphs = []
    for class_name in ['summary-intro', 'supporting-point', 'transition-text', 'secondary-detail']:
        for p in soup.find_all('p', class_=class_name):
            summary_paragraphs.append({'class': class_name, 'content': str(p)})
    result['summary_paragraphs'] = summary_paragraphs

    # Interesting Facts
    facts = []
    facts_container = soup.find('div', class_='facts-container')
    if facts_container:
        for li in facts_container.find_all('li'):
            fact_class = li.get('class', [])
            # Using decode_contents to get inner HTML without the outer <li> tag
            facts.append({'class': fact_class, 'content': li.decode_contents()})
    result['interesting_facts'] = facts
    
    # More on topic and related terminology extraction
    related_resources = []
    more_topic_container = soup.find('div', class_='more-on-topic-container')
    if more_topic_container:
        ul = more_topic_container.find('ul', class_='related-terminology-list')
        if ul:
            for li in ul.find_all('li', class_='terminology-item'):
                resource = {}
                a_tag = li.find('a', class_='resource-link')
                if a_tag:
                    resource['title'] = a_tag.get_text(strip=True)
                    resource['url'] = a_tag.get('href', '')
                span_desc = li.find('span', class_='resource-description')
                if span_desc:
                    resource['description'] = span_desc.get_text(strip=True)
                if resource:
                    related_resources.append(resource)
    result['related_resources'] = related_resources
    
    # Topic Popularity Score Extraction
    topic_popularity = {}
    popularity_container = soup.find('div', class_='popularity-container')
    if popularity_container:
        popularity_number = popularity_container.find(class_='popularity-number')
        popularity_description = popularity_container.find(class_='popularity-description')
        topic_popularity['number'] = popularity_number.get_text(strip=True) if popularity_number else ''
        topic_popularity['description'] = popularity_description.get_text(strip=True) if popularity_description else ''
    result['topic_popularity'] = topic_popularity
    
    # Sentiment Analysis Extraction (updated)
    sentiment_data = []
    for div in soup.find_all('div', class_='entity-sentiment'):
        # Get entity name
        entity_name_tag = div.find('h4', class_='entity-name')
        entity_name = entity_name_tag.get_text(strip=True) if entity_name_tag else ''
        
        # Get positive/negative counts
        sentiment_details_tag = div.find('p', class_='entity-sentiment-details')
        positive = ''
        negative = ''
        if sentiment_details_tag:
            positive_tag = sentiment_details_tag.find('span', class_='sentiment-positive')
            negative_tag = sentiment_details_tag.find('span', class_='sentiment-negative')
            positive = positive_tag.get_text(strip=True) if positive_tag else ''
            negative = negative_tag.get_text(strip=True) if negative_tag else ''
        
        # Extract additional sentiment info
        entity_summary_tag = div.find('p', class_='entity-summary')
        entity_summary = entity_summary_tag.get_text(strip=True) if entity_summary_tag else ''
        
        # Extract keywords properly as a list
        entity_keywords = []
        entity_keywords_tag = div.find('p', class_='entity-keywords')
        if entity_keywords_tag:
            keywords_text = entity_keywords_tag.get_text(separator=' ', strip=True)
            # Remove common prefixes if they exist
            for prefix in ["Keywords:", "Key words/phrases:"]:
                if keywords_text.lower().startswith(prefix.lower()):
                    keywords_text = keywords_text[len(prefix):].strip()
            # Split the string into a list by comma and trim each keyword
            entity_keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]

        
        sentiment_data.append({
            'entity': entity_name,
            'positive': positive,
            'negative': negative,
            'summary': entity_summary,
            'keywords': entity_keywords
        })
        result['sentiment_analysis'] = sentiment_data

    return result

def create_filename_from_title(title, url, article_id):
    """
    Create a valid filename from the article title.
    
    Args:
        title (str): The article title
        url (str): The article URL (fallback if title is empty)
        article_id (str): The article ID (fallback if title and URL are empty)
        
    Returns:
        str: A valid filename
    """
    # Handle empty title
    if not title or title.strip() == '':
        if url:
            # Extract last part of URL
            url_parts = url.strip('/').split('/')
            return f"{url_parts[-1][:50]}.html"
        else:
            # Use article ID
            return f"article_{article_id}.html"
    
    # Clean title and create filename
    filename = re.sub(r'[^\w\s-]', '', title)  # Remove non-alphanumeric chars
    filename = re.sub(r'\s+', '_', filename)    # Replace spaces with underscores
    filename = filename[:50]                    # Limit length
    return f"{filename}.html"

def save_as_html(article_id, title, url, content, summary, response_text, schema, keywords=None, existing_gemini_title=None): # Note: keywords arg here is likely unused now
    """
    Save the article and its summary as an HTML file, with images from Wikimedia based on keywords.

    Args:
        article_id (str): The article ID
        title (str): The article title
        url (str): The article URL
        content (str): The original article content
        summary (str): The generated summary
        response_text (str): The raw API response
        schema (str): The database schema
        keywords (list, optional): [DEPRECATED/UNUSED in this context - keywords are extracted from summary]
        existing_gemini_title (str, optional): Title from DB if already summarized.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure output directory exists
        ensure_output_directory()

        logger.debug(f"Raw summary type: {type(summary)}")
        logger.debug(f"Raw summary preview: {summary[:300] if summary else 'None'}")

        # --- Start Processing Summary and Extracting Fields FIRST ---
        processed_summary = summary
        clean_summary = ""
        if processed_summary and isinstance(processed_summary, str):
            if "```html" in processed_summary:
                try:
                    processed_summary = processed_summary.split("```html")[1].split("```")[0].strip()
                    processed_summary = html.unescape(processed_summary)
                    logger.debug("Extracted and unescaped HTML from code block")
                except Exception as e:
                    logger.warning(f"Error extracting HTML from code block: {e}")

            processed_summary = re.sub(r'<li style="[^>]*">', '<li>', processed_summary)
            clean_summary = clean_and_normalize_html(processed_summary)
        else:
            logger.warning(f"Invalid summary content: {type(processed_summary)}")
            clean_summary = "<div>No valid summary content available</div>"

        # If clean_summary is empty or just a placeholder, try with the API response
        if not clean_summary or clean_summary in ("<div>No content available</div>", "<div>No valid summary content available</div>"):
            logger.warning("Processed summary is empty, attempting to extract from raw API response")
            try:
                # ... (logic to extract HTML from response_text - keep as is) ...
                 if response_text and "```html" in response_text:
                    html_content = response_text.split("```html")[1].split("```")[0].strip()
                    html_content = html.unescape(html_content)
                    if html_content:
                        clean_summary = clean_and_normalize_html(html_content)
                        logger.info("Successfully extracted HTML content from API response")
                 elif response_text and ("<html" in response_text or "<div" in response_text):
                    html_match = re.search(r'(<div.*?>.*?</div>|<html.*?>.*?</html>)', response_text, re.DOTALL)
                    if html_match:
                        html_content = html_match.group(0)
                        clean_summary = clean_and_normalize_html(html_content)
                        logger.info("Successfully extracted HTML content from API response using regex")
            except Exception as e:
                logger.error(f"Error extracting HTML from API response: {e}")


        # Extract Gemini-generated title (use existing if available)
        soup_summary = BeautifulSoup(clean_summary, 'html.parser')
        gemini_title_tag = soup_summary.find('h1', class_='article-title')
        generated_title = gemini_title_tag.get_text(separator=' ', strip=True) if gemini_title_tag else title
        gemini_title = existing_gemini_title if existing_gemini_title is not None else generated_title

        if existing_gemini_title is not None:
             logger.info(f"Existing Gemini title found in DB for article {article_id}: '{existing_gemini_title}'. Title unchanged.")
        else:
             logger.info(f"New Gemini title generated for article {article_id}: '{generated_title}'.")

        # **MODIFICATION 1: Extract summary fields (including keywords) HERE**
        summary_fields = extract_summary_fields(clean_summary)
        # Get the keywords extracted from the summary content
        extracted_keywords = summary_fields.get("keywords", []) # Use a different variable name to avoid confusion with the function argument

        # --- Now Perform Image Search Using Extracted Keywords ---
        images = [] # Initialize images list
        featured_image_html = ""

        # Use extracted keywords for image search if available, otherwise fall back to title
        if extracted_keywords:
            logger.info(f"Attempting Wikimedia image search using extracted keywords: {extracted_keywords}")
            base_name = re.sub(r'[^\w\s-]', '', gemini_title if gemini_title else "Article")
            base_name = re.sub(r'\s+', '_', base_name)[:30]

            from summarizer_config import CONFIG, get_config_value
            short_threshold = get_config_value(CONFIG, 'image_search', 'short_threshold', 3000)
            medium_threshold = get_config_value(CONFIG, 'image_search', 'medium_threshold', 7000)
            max_images = get_config_value(CONFIG, 'image_search', 'max_images', 3)

            content_length = len(content) if content else 0
            if content_length < short_threshold:
                num_images = 3 # put to 2 for lowering num of images in short articles
            elif content_length < medium_threshold:
                num_images = 3
            else:
                num_images = max_images

            # **MODIFICATION 2: Pass extracted_keywords to search_keywords parameter**
            images = search_and_download_images(
                query="", # Query is not needed when search_keywords is provided
                article_id=article_id,
                base_name=base_name,
                num_images=num_images,
                title=gemini_title, # Still pass title for potential fallback or context
                search_keywords=extracted_keywords # <-- PASS THE KEYWORDS HERE
            )
            logger.info(f"Found {len(images)} images for article {article_id} using extracted keywords.")

        elif title: # Fallback if no keywords were extracted, but title exists
             logger.info("No keywords extracted from summary, falling back to title-based image search.")
             base_name = re.sub(r'[^\w\s-]', '', title)
             base_name = re.sub(r'\s+', '_', base_name)[:30]
             # Determine num_images based on content length (same logic as above)
             from summarizer_config import CONFIG, get_config_value
             short_threshold = get_config_value(CONFIG, 'image_search', 'short_threshold', 3000)
             medium_threshold = get_config_value(CONFIG, 'image_search', 'medium_threshold', 7000)
             max_images = get_config_value(CONFIG, 'image_search', 'max_images', 3)
             content_length = len(content) if content else 0
             if content_length < short_threshold: num_images = 2
             elif content_length < medium_threshold: num_images = 3
             else: num_images = max_images

             images = search_and_download_images(
                 query="", # Let the image module use extract_search_terms with title
                 article_id=article_id,
                 base_name=base_name,
                 num_images=num_images,
                 title=title,
                 search_keywords=None # Explicitly pass None
             )
             logger.info(f"Found {len(images)} images for article {article_id} using title fallback.")
        else:
            logger.warning("No keywords extracted and no title provided. Cannot search for images.")


        # Prepare featured image and fetched images context (using the 'images' list populated above)
        featured_image_data = None
        fetched_images_data = []
        if images and len(images) > 0:
            # Use the first image as featured
            featured_image_data = {
                "url": os.path.basename(images[0]["url"]), # Use basename for template path
                "alt": images[0].get("caption", "Article image"),
                "caption": images[0].get("caption", "")
            }
            # Use the rest as fetched images
            fetched_images_data = [{
                "url": os.path.basename(img["url"]), # Use basename for template path
                "alt": img.get("caption", "Article image"),
                "caption": img.get("caption", "")
            } for img in images[1:]]

            # Also generate the featured_image_html string if needed elsewhere (though context is preferred for Jinja)
            featured_image_url = images[0]["url"].replace("\\", "/") # Use the relative path from download_image
            featured_image_html = (
                 f'<div class="featured-image">'
                 f'<img src="{featured_image_url}" alt="{images[0]["caption"]}">'
                 f'<figcaption>{images[0]["caption"]}</figcaption>'
                 f'</div>'
            )
            logger.info(f"Featured image prepared: {featured_image_url}")
        else:
             logger.warning("No images found or downloaded. No featured image will be added.")


        # Process any *inline* images already present in the summary HTML
        if clean_summary and "<img" in clean_summary:
            clean_summary = process_images_in_html(clean_summary, article_id)


        # --- Continue with saving HTML, using already extracted summary_fields ---
        filename = create_filename_from_title(gemini_title, url, article_id)

        # Determine subfolder(s) based on URL
        subfolder = get_subfolder_from_url(url)
        target_dir = os.path.join(OUTPUT_HTML_DIR, subfolder) if subfolder else OUTPUT_HTML_DIR
        os.makedirs(target_dir, exist_ok=True)
        filepath = os.path.join(target_dir, filename)
        logger.debug(f"Preparing to save HTML to: {filepath}")

        # Compute relative path for static assets
        depth = subfolder.count(os.sep) + 1 if subfolder else 0
        relative_static_path = "../" * (1 + depth) + "static"

        # Create processed date and current year
        processed_date = datetime.now().strftime("%B %d, %Y %H:%M")
        current_year = datetime.now().year

        # Compute relative file location for the saved HTML file
        relative_file_location = os.path.join(subfolder, filename).replace(os.sep, '/') if subfolder else filename.replace(os.sep, '/')

        # Get Related Articles (using the already extracted keywords)
        from db_scripts.db_context import DatabaseContext
        db_context = DatabaseContext()
        related_articles_list = get_related_articles(db_context, schema, article_id, extracted_keywords, limit=5) if extracted_keywords else []

        # Prepare context for Jinja template
        context = {
            "title": gemini_title or f"Article {article_id}",
            "article_id": article_id,
            "url": url,
            "processed_date": processed_date,
            "featured_image": featured_image_data, # Use the data dict
            "summary": clean_summary if clean_summary else "<div>No summary available</div>",
            "fetched_images": fetched_images_data, # Use the data list
            "show_api_response": True, # Or False based on your config/preference
            "response_text": response_text,
            "content": content, # Optional: include original content if template uses it
            "relative_static_path": relative_static_path,
            "current_year": current_year,
            # Use fields extracted earlier
            "source_attribution": summary_fields.get("source_attribution", ""),
            "keywords": extracted_keywords, # Use the extracted list
            "entity_overview": summary_fields.get("entity_overview", []),
            "summary_paragraphs": summary_fields.get("summary_paragraphs", []),
            "interesting_facts": summary_fields.get("interesting_facts", []),
            "related_resources": summary_fields.get("related_resources", []),
            "sentiment_analysis": summary_fields.get("sentiment_analysis", []),
            "topic_popularity": summary_fields.get("topic_popularity", {}),
            "popularity_score": int(summary_fields.get("topic_popularity", {}).get("number", "0") or 0),
            "related_articles_list": related_articles_list,
            "schema": schema,
            "article_html_file_location": relative_file_location
        }

        # Load and render the template
        template = jinja_env.get_template('article.html')
        html_content = template.render(context)

        # Write the rendered HTML to the output file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
            f.flush() # Ensure data is written to disk

        # Final checks and DB update
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            logger.info(f"Successfully saved HTML output to {filepath} (size: {file_size} bytes)")
            # Update additional summary details in the database.
            update_success = update_article_summary_details(db_context, schema, article_id, context) # Pass the full context
            if update_success:
                logger.info("Database summary details updated successfully.")
            else:
                logger.error("Failed to update database summary details.")
            return True
        else:
            logger.error(f"File wasn't created despite no errors: {filepath}")
            return False

    except Exception as e:
        # Ensure filepath is defined for logging, even if error occurred early
        filepath_str = filepath if 'filepath' in locals() else 'unknown path'
        logger.error(f"Error saving HTML file {filepath_str}: {e}", exc_info=True)
        return False
