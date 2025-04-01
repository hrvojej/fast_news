"""
Module for image handling operations in the article summarization system.
This module retrieves and downloads images from Wikimedia Commons.
"""

import json
import os
import re
import time
import requests
import uuid
import shutil
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import sys

from summarizer_logging import get_logger
from summarizer_config import OUTPUT_HTML_DIR, get_config_value, CONFIG

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

logger = get_logger(__name__)

# Directory for storing images
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
IMAGES_DIR = os.path.join(BASE_DIR, 'frontend', 'web', 'static', 'images')

# Standard class names for images
IMAGE_CLASSES = {
    "featured": "featured-image",
    "article": "article-image",
    "left_float": "left-image",
    "right_float": "right-image",
    "caption": "image-caption"
}

def is_valid_image_url(url):
    """
    Check if a URL is likely a valid image URL.
    
    Args:
        url (str): URL to check.
        
    Returns:
        bool: True if the URL appears to be a valid image URL, False otherwise.
    """
    if not url or not isinstance(url, str):
        return False
    
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()
    has_image_extension = any(path.endswith(ext) for ext in image_extensions)
    has_scheme = bool(parsed_url.scheme in ['http', 'https'])
    has_netloc = bool(parsed_url.netloc)
    
    return has_scheme and has_netloc and has_image_extension

def ensure_images_directory():
    """
    Ensure the images directory exists and is writable.
    
    Returns:
        bool: True if the directory exists and is writable, False otherwise.
    """
    logger.debug(f"Ensuring images directory exists at: {IMAGES_DIR}")
    try:
        os.makedirs(IMAGES_DIR, exist_ok=True)
        logger.info(f"Ensured images directory: {IMAGES_DIR}")
        
        # Test write access
        test_file = os.path.join(IMAGES_DIR, "test_write.txt")
        with open(test_file, 'w') as f:
            f.write("Test")
        os.remove(test_file)
        
        logger.debug(f"Images directory is writable: {IMAGES_DIR}")
        return True
    except Exception as e:
        logger.error(f"Error with images directory: {e}", exc_info=True)
        return False

def download_image(url, article_id, base_name=None, counter=None):
    """
    Download an image from a URL and save it to the images directory.

    Args:
        url (str): URL of the image to download.
        article_id (str): ID of the article (used for naming fallback).
        base_name (str, optional): Base name for the image file (e.g., sanitized article title).
        counter (int, optional): A counter to append to the filename.

    Returns:
        dict: Image metadata including 'path', 'filename', 'original_url', or None if download failed.
    """
    logger.debug(f"download_image called with url: {url}, article_id: {article_id}, base_name: {base_name}, counter: {counter}")

    if not is_valid_image_url(url):
        logger.warning(f"Invalid image URL: {url}")
        return None

    if not ensure_images_directory():
        logger.error("Images directory could not be ensured.")
        return None

    parsed_url = urlparse(url)
    extension = os.path.splitext(parsed_url.path.lower())[1] or '.jpg'

    if base_name and counter is not None:
        sanitized_base = re.sub(r'[^\w\s-]', '', base_name).strip().replace(' ', '_')
        filename = f"{sanitized_base}_{counter}{extension}"
    else:
        unique_id = str(uuid.uuid4())[:8]
        filename = f"img_{article_id}_{unique_id}{extension}"

    filepath = os.path.join(IMAGES_DIR, filename)
    logger.debug(f"Attempting to download image from {url} to {filepath}")

    try:
        user_agent = get_config_value("USER_AGENT", "MySummarizer/1.0 (your.email@example.com)")
        timeout_value = get_config_value("REQUEST_TIMEOUT", 10)
        headers = {
            'User-Agent': user_agent
        }
        response = requests.get(url, headers=headers, stream=True, timeout=timeout_value)
        logger.debug(f"Image download response status: {response.status_code}")
        response.raise_for_status()

        # Check if the response contains an image
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            logger.error(f"URL did not return image content: {url} (Content-Type: {content_type})")
            return None

        with open(filepath, 'wb') as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)

        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            logger.info(f"Downloaded image successfully:\n"
                        f"    Original URL: {url}\n"
                        f"    Local path: {filename}\n"
                        f"    Absolute path: {filepath}\n"
                        f"    Size: {file_size} bytes, Content-Type: {content_type}")

            return {
                "path": "/static/images/" + filename,
                "filename": filename,
                "original_url": url,
                "content_type": content_type,
                "size": file_size
            }
        else:
            logger.error(f"Image file {filepath} was not created after download attempt.")
            return None

    except requests.RequestException as req_error:
        logger.error(f"Request error while downloading image from {url}: {req_error}", exc_info=True)
        return None
    except Exception as file_error:
        logger.error(f"Failed to save image to {filepath}: {file_error}", exc_info=True)
        return None

def extract_search_terms(query, title, content=None, entity_list=None):
    import logging
    logger = logging.getLogger(__name__)
    
    search_text = title if title else query
    if not search_text:
        logger.info("No title or query provided; cannot extract search terms.")
        return []
    
    from portals.modules.keyword_extractor import KeywordExtractor
    extractor = KeywordExtractor()
    
    candidates = []
    # Try extracting keywords with decreasing max_keywords: 5, then 4, then 3, then 2
    for max_kw in [5, 4, 3, 2]:
        logger.info(f"Attempting to extract keywords with max_keywords = {max_kw}")
        keywords = extractor.extract_keywords(search_text, max_keywords=max_kw)
        logger.info(f"Extracted keywords with max_keywords={max_kw}: {keywords}")
        if keywords:
            nlp_query = " ".join(keywords)
            logger.info(f"Using NLP search term: {nlp_query}")
            candidates.append(nlp_query)
    
    if not candidates:
        logger.info("Failed to extract any keywords using NLP.")
    return candidates

def is_relevant(caption, query):
    """
    Check if the image caption is relevant to the search query.
    
    Args:
        caption (str): The caption or description of the image.
        query (str): The search query.
    
    Returns:
        bool: True if at least one word from the query is found in the caption.
    """
    if not caption:
        return False
    caption_lower = caption.lower()
    query_words = query.lower().split()
    matches = sum(1 for word in query_words if word in caption_lower)
    return matches > 0

def wrap_image_in_figure(soup, img):
    """
    Wrap an img tag in a figure element with the standard article image class
    and add a figcaption if the alt text is available.
    
    Args:
        soup (BeautifulSoup): The BeautifulSoup object.
        img (Tag): The image tag to wrap.
    
    Returns:
        Tag: The new figure element.
    """
    figure = soup.new_tag('figure', **{'class': IMAGE_CLASSES["article"]})
    img_copy = img.extract()
    figure.append(img_copy)
    if img_copy.get('alt') and img_copy.get('alt') != 'Image':
        figcaption = soup.new_tag('figcaption')
        figcaption.string = img_copy.get('alt')
        figure.append(figcaption)
    return figure

def search_and_download_images(query, article_id, base_name, num_images, title=None, entity_list=None, content=None, requested_width=600):
    """
    Search for images using Wikimedia Commons.
    
    Args:
        query (str): Search query (derived from article keywords or title).
        article_id (str): ID of the article (used for naming images).
        base_name (str): Base name for image filenames.
        num_images (int): Number of images to download.
        title (str, optional): Article title for search terms.
        entity_list (list, optional): List of named entities from the article.
        content (str, optional): Article content for context-based search terms.
        requested_width (int, optional): Desired thumbnail width (in pixels). Defaults to 600.
        
    Returns:
        list: A list of dictionaries, each containing 'url', 'caption', and 'alt'.
    """
    # Get a prioritized list of search terms using the original title if provided
    if title:
        search_queries = extract_search_terms("", title, content, entity_list)
    else:
        search_queries = extract_search_terms(query, title, content, entity_list)
    if not search_queries:
        logger.info("No keywords extracted using NLP; falling back to original title.")
        search_queries = [title]
    logger.debug(f"Will try these search queries in order: {search_queries}")

    logger.info("Using Wikimedia Commons search for images.")
    api_url = "https://commons.wikimedia.org/w/api.php"
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg']
    
    for current_query in search_queries:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": current_query,
            "gsrwhat": "text",
            "gsrnamespace": 6,
            "gsrlimit": num_images * 3,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": requested_width
        }
        logger.debug(f"Searching Wikimedia Commons with query: '{current_query}' and params: {params}")
        try:
            user_agent = get_config_value("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (your.email@example.com)")
            timeout_value = get_config_value("REQUEST_TIMEOUT", 10)
            headers = {
                'User-Agent': user_agent
            }
            response = requests.get(api_url, headers=headers, params=params, timeout=timeout_value)
            logger.debug(f"Wikimedia API Request URL: {response.url}")
            logger.debug(f"Wikimedia API Response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Wikimedia API request failed (status: {response.status_code}). Response: {response.text[:500]}")
                continue
            try:
                json_response = response.json()
                logger.debug(f"Wikimedia Commons API JSON response (truncated): {json.dumps(json_response, indent=2)[:500]}")
            except ValueError as e:
                logger.error(f"Failed to parse JSON from Wikimedia response: {e}")
                continue
            if 'query' not in json_response or 'pages' not in json_response['query']:
                logger.info(f"No images found in Wikimedia response for query '{current_query}'")
                continue
            sleep_duration = get_config_value("WIKIMEDIA_SLEEP_DURATION", 1)
            time.sleep(sleep_duration)
            images = []
            pages = json_response["query"]["pages"]
            sorted_pages = sorted(pages.values(), key=lambda p: int(p.get("pageid", 0)))
            for idx, page in enumerate(sorted_pages, start=1):
                imageinfo = page.get("imageinfo", [])
                if not imageinfo:
                    logger.debug(f"No imageinfo found for page: {page.get('title', 'Unknown')}")
                    continue
                info = imageinfo[0]
                image_url = info.get("thumburl") or info.get("url")
                if not image_url:
                    continue
                _, ext = os.path.splitext(image_url.lower())
                if ext not in valid_extensions:
                    logger.warning(f"Invalid image format {ext} for URL: {image_url}")
                    continue
                extmeta = info.get("extmetadata", {})
                caption = None
                if extmeta:
                    caption = extmeta.get("ObjectName", {}).get("value")
                    if not caption:
                        caption = extmeta.get("ImageDescription", {}).get("value")
                    if caption and '<' in caption:
                        caption = BeautifulSoup(caption, 'html.parser').get_text()
                if not caption:
                    caption = page.get("title", "Image").replace("File:", "").replace("_", " ")
                # Check relevance using the new helper function
                if not is_relevant(caption, current_query):
                    logger.debug(f"Skipping image '{page.get('title', 'Unknown')}' due to low relevance with query '{current_query}'.")
                    continue
                image_data = download_image(image_url, article_id, base_name=base_name, counter=idx)
                if image_data:
                    images.append({
                        "url": image_data["path"],
                        "caption": caption,
                        "alt": caption
                    })
                if len(images) >= num_images:
                    break
            if images:
                logger.info(f"Downloaded {len(images)} images from Wikimedia Commons for query: '{current_query}'")
                return images
        except Exception as e:
            logger.error(f"Error searching for images on Wikimedia Commons with query '{current_query}': {e}", exc_info=True)
    
    logger.warning("All queries failed to find images. No images will be included.")
    return []

def create_standardized_image_html(url, caption=None, alt=None, is_featured=False):
    """
    Create standardized HTML for images with proper classes and structure.
    
    Args:
        url (str): URL path to the image.
        caption (str, optional): Caption for the image.
        alt (str, optional): Alt text for the image.
        is_featured (bool): Whether this is a featured image.
        
    Returns:
        str: Standardized HTML for the image.
    """
    alt_text = alt or caption or "Image"
    
    if is_featured:
        html = f'<div class="{IMAGE_CLASSES["featured"]}">'
        html += f'<img src="{url}" alt="{alt_text}">'
        if caption:
            html += f'<figcaption>{caption}</figcaption>'
        html += '</div>'
    else:
        html = f'<figure class="{IMAGE_CLASSES["article"]}">'
        html += f'<img src="{url}" alt="{alt_text}">'
        if caption:
            html += f'<figcaption>{caption}</figcaption>'
        html += '</figure>'
    
    return html

def process_images_in_html(html_content, article_id):
    """
    Process all images in HTML content by downloading external images, replacing their
    source URLs with local paths, and ensuring proper class structure.
    
    Args:
        html_content (str): HTML content containing <img> tags.
        article_id (str): ID of the article.
    
    Returns:
        str: Updated HTML content with local image paths and standardized styling.
    """
    if not html_content:
        return html_content
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Process standalone img tags
        standalone_imgs = [img for img in soup.find_all('img') if img.parent.name not in ['figure', 'div'] or (img.parent.name == 'div' and IMAGE_CLASSES["featured"] not in img.parent.get('class', []))]
        
        for img in standalone_imgs:
            src = img.get('src')
            if src and (src.startswith('http://') or src.startswith('https://')):
                image_data = download_image(src, article_id)
                if image_data:
                    img['src'] = image_data["path"]
                    img['data-original-src'] = src
                    
                    if img.parent.name not in ['div', 'figure'] or not img.parent.get('class'):
                        new_figure = wrap_image_in_figure(soup, img)
                        img.insert_after(new_figure)
                        img.decompose()
                else:
                    img['alt'] = f"{img.get('alt', 'Image')} (failed to download)"
                    img['title'] = f"Failed to download: {src}"
        
        # Process images in figures or featured-image divs
        for container in soup.find_all(['figure', 'div']):
            if container.name == 'div' and (not container.get('class') or IMAGE_CLASSES["featured"] not in container.get('class', [])):
                continue
                
            img = container.find('img')
            if not img:
                continue
                
            src = img.get('src')
            if src and (src.startswith('http://') or src.startswith('https://')):
                image_data = download_image(src, article_id)
                if image_data:
                    img['src'] = image_data["path"]
                    img['data-original-src'] = src
                else:
                    img['alt'] = f"{img.get('alt', 'Image')} (failed to download)"
                    img['title'] = f"Failed to download: {src}"
            
            if container.name == 'figure' and not container.get('class'):
                container['class'] = IMAGE_CLASSES["article"]
            
            if container.name == 'figure' and not container.find('figcaption') and img.get('alt'):
                figcaption = soup.new_tag('figcaption')
                figcaption.string = img.get('alt')
                container.append(figcaption)
        
        # Remove any style attributes
        for element in soup.find_all(lambda tag: tag.has_attr('style')):
            del element['style']
        
        return str(soup)
    except Exception as e:
        logger.error(f"Error processing images in HTML: {e}", exc_info=True)
        return html_content

def extract_image_urls_from_html(html_content):
    """
    Extract all image URLs from HTML content.
    
    Args:
        html_content (str): HTML content containing <img> tags.
        
    Returns:
        list: A list of image URLs.
    """
    if not html_content:
        return []
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        img_tags = soup.find_all('img')
        urls = [img.get('src') for img in img_tags if img.get('src') and (img.get('src').startswith('http://') or img.get('src').startswith('https://'))]
        return urls
    except Exception as e:
        logger.error(f"Error extracting image URLs: {e}", exc_info=True)
        return []

def test_image_download():
    """
    Test image download functionality with detailed logging and User-Agent compliance.
    """
    test_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/800px-Python-logo-notext.svg.png"
    test_article_id = "test_article_123"
    user_agent = get_config_value("USER_AGENT", "MySummarizerTest/1.0 (your.email@example.com) requests/2.25.1")
    headers = {
        'User-Agent': user_agent
    }

    logger.debug(f"Testing image download with URL: {test_url}")
    
    try:
        response = requests.get(test_url, headers=headers, stream=True, timeout=get_config_value("REQUEST_TIMEOUT", 10))
        logger.debug(f"Test image download response status: {response.status_code}")

        if response.status_code == 200:
            filename = f"test_image_{test_article_id}.png"
            filepath = os.path.join(IMAGES_DIR, filename)
            os.makedirs(IMAGES_DIR, exist_ok=True)

            with open(filepath, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)

            file_size = os.path.getsize(filepath)
            logger.info(f"Successfully downloaded test image: {filepath} (Size: {file_size} bytes)")
            print(f"Downloaded test image successfully: {filepath}")

        else:
            logger.error(f"Failed to download test image. Status code: {response.status_code}")
            print(f"Failed to download image. Status code: {response.status_code}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error during test image download: {e}", exc_info=True)
        print(f"Request exception: {e}")

if __name__ == "__main__":
    ensure_images_directory()
    test_image_download()
