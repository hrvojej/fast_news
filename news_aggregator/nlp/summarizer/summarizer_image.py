"""
Module for image handling operations in the article summarization system.
This module retrieves and downloads images from Wikimedia Commons.
"""

import os
import re
import requests
import uuid
import shutil
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from summarizer_logging import get_logger
from summarizer_config import OUTPUT_HTML_DIR, get_config_value, CONFIG

logger = get_logger(__name__)

# Directory for storing images
IMAGES_DIR = os.path.join(OUTPUT_HTML_DIR, "images")

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
        if not os.path.exists(IMAGES_DIR):
            os.makedirs(IMAGES_DIR)
            logger.info(f"Created images directory: {IMAGES_DIR}")
        
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
        str: Relative path to the downloaded image (relative to the HTML output directory), or None if download failed.
    """
    logger.debug(f"download_image called with url: {url}, article_id: {article_id}, base_name: {base_name}, counter: {counter}")
    if not is_valid_image_url(url):
        logger.warning(f"Invalid image URL: {url}")
        return None
    
    try:
        if not ensure_images_directory():
            logger.error("Images directory could not be ensured.")
            return None
        
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        extension = os.path.splitext(path)[1]
        if not extension or extension == '.':
            extension = '.jpg'
        
        if base_name and counter is not None:
            sanitized_base = re.sub(r'[^\w\s-]', '', base_name).strip().replace(' ', '_')
            filename = f"{sanitized_base}_{counter}{extension}"
        else:
            unique_id = str(uuid.uuid4())[:8]
            filename = f"img_{article_id}_{unique_id}{extension}"
        
        filepath = os.path.join(IMAGES_DIR, filename)
        logger.debug(f"Attempting to download image from {url} to {filepath}")
        
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
            relative_path = os.path.join("images", filename)
            logger.info(f"Downloaded image from {url} to {filepath}")
            return relative_path
        else:
            logger.warning(f"Failed to download image (status code {response.status_code}): {url}")
            return None
    except Exception as e:
        logger.error(f"Error downloading image from {url}: {e}", exc_info=True)
        return None

def search_and_download_images(query, article_id, base_name, num_images):
    """
    Search for images on Wikimedia Commons using the provided query and download up to num_images.
    
    Args:
        query (str): Search query (derived from article keywords or title).
        article_id (str): ID of the article (used for naming images).
        base_name (str): Base name for image filenames (typically a sanitized article title).
        num_images (int): Number of images to download.
        
    Returns:
        list: A list of dictionaries, each containing 'url' (the local relative image path) and 'caption' (if available).
    """
    api_url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,  # File namespace
        "gsrlimit": num_images,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata"
    }
    logger.debug(f"Searching Wikimedia Commons with query: '{query}' and params: {params}")
    
    try:
        response = requests.get(api_url, params=params, timeout=10)
        logger.debug(f"Wikimedia Commons API response status: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"Wikimedia Commons API returned status code {response.status_code}")
            return []
        
        data = response.json()
        logger.debug(f"Wikimedia Commons API response keys: {list(data.keys())}")
        if "query" not in data or "pages" not in data["query"]:
            logger.info("No images found for the query.")
            return []
        
        images = []
        pages = data["query"]["pages"]
        sorted_pages = sorted(pages.values(), key=lambda p: int(p.get("pageid", 0)))
        for idx, page in enumerate(sorted_pages, start=1):
            imageinfo = page.get("imageinfo", [])
            if not imageinfo:
                logger.debug(f"No imageinfo found for page: {page.get('title', 'Unknown')}")
                continue
            info = imageinfo[0]
            image_url = info.get("url")
            extmeta = info.get("extmetadata", {})
            caption = None
            if extmeta:
                caption = extmeta.get("ObjectName", {}).get("value")
                if not caption:
                    caption = extmeta.get("ImageDescription", {}).get("value")
            local_image_path = download_image(image_url, article_id, base_name=base_name, counter=idx)
            if local_image_path:
                images.append({
                    "url": local_image_path,
                    "caption": caption if caption else page.get("title", "Image")
                })
            if len(images) >= num_images:
                break
        
        logger.info(f"Downloaded {len(images)} images for query: '{query}'")
        return images
    except Exception as e:
        logger.error(f"Error searching for images on Wikimedia Commons: {e}", exc_info=True)
        return []

def process_images_in_html(html_content, article_id):
    """
    Process all images in HTML content by downloading external images and replacing their source URLs with local paths.
    
    Args:
        html_content (str): HTML content containing <img> tags.
        article_id (str): ID of the article.
    
    Returns:
        str: Updated HTML content with local image paths.
    """
    if not html_content:
        return html_content
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        img_tags = soup.find_all('img')
        
        for img in img_tags:
            src = img.get('src')
            if src and (src.startswith('http://') or src.startswith('https://')):
                local_path = download_image(src, article_id)
                if local_path:
                    img['src'] = local_path
                    img['data-original-src'] = src
                else:
                    img['alt'] = f"{img.get('alt', 'Image')} (failed to download)"
                    img['title'] = f"Failed to download: {src}"
        
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
    """Test the image download functionality using a known Wikimedia Commons image."""
    test_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/800px-Python-logo-notext.svg.png"
    test_article_id = "test_article_123"
    local_path = download_image(test_url, test_article_id)
    
    if local_path:
        print(f"Successfully downloaded test image to {local_path}")
        return True
    else:
        print("Failed to download test image")
        return False

if __name__ == "__main__":
    ensure_images_directory()
    test_image_download()
