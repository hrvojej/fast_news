# summarizer_image.py
"""
Module for image handling operations in the article summarization system.
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

# Initialize logger
logger = get_logger(__name__)

# Directory for storing images
IMAGES_DIR = os.path.join(OUTPUT_HTML_DIR, "images")

def ensure_images_directory():
    """
    Ensure the images directory exists and is writable.
    
    Returns:
        bool: True if the directory exists and is writable, False otherwise
    """
    try:
        if not os.path.exists(IMAGES_DIR):
            os.makedirs(IMAGES_DIR)
            logger.info(f"Created images directory: {IMAGES_DIR}")
        
        # Test write access
        test_file = os.path.join(IMAGES_DIR, "test_write.txt")
        with open(test_file, 'w') as f:
            f.write("Test")
        os.remove(test_file)
        
        logger.info(f"Images directory is writable: {IMAGES_DIR}")
        return True
        
    except Exception as e:
        logger.error(f"Error with images directory: {e}", exc_info=True)
        return False

def is_valid_image_url(url):
    """
    Check if a URL is likely a valid image URL.
    
    Args:
        url (str): URL to check
        
    Returns:
        bool: True if URL seems to be a valid image URL, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    # Check if URL has a common image extension
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()
    
    # Check if URL has an image extension
    has_image_extension = any(path.endswith(ext) for ext in image_extensions)
    
    # Basic validation of URL format
    has_scheme = bool(parsed_url.scheme in ['http', 'https'])
    has_netloc = bool(parsed_url.netloc)
    
    return has_scheme and has_netloc and has_image_extension

def download_image(url, article_id):
    """
    Download an image from a URL and save it to the images directory.
    
    Args:
        url (str): URL of the image to download
        article_id (str): ID of the article (used for naming)
        
    Returns:
        str: Path to the downloaded image relative to the HTML output directory,
             or None if download failed
    """
    if not is_valid_image_url(url):
        logger.warning(f"Invalid image URL: {url}")
        return None
    
    try:
        # Ensure images directory exists
        if not ensure_images_directory():
            return None
        
        # Extract file extension from URL
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        # Find the file extension
        extension = os.path.splitext(path)[1]
        if not extension or extension == '.':
            # Default to .jpg if no extension found
            extension = '.jpg'
        
        # Generate a unique filename
        unique_id = str(uuid.uuid4())[:8]
        filename = f"img_{article_id}_{unique_id}{extension}"
        filepath = os.path.join(IMAGES_DIR, filename)
        
        # Download the image with timeout
        response = requests.get(url, stream=True, timeout=10)
        
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
            
            # Return the path relative to the output directory
            relative_path = os.path.join("images", filename)
            logger.info(f"Downloaded image from {url} to {filepath}")
            return relative_path
        else:
            logger.warning(f"Failed to download image (status code {response.status_code}): {url}")
            return None
            
    except Exception as e:
        logger.error(f"Error downloading image from {url}: {e}", exc_info=True)
        return None

def process_images_in_html(html_content, article_id):
    """
    Process all images in HTML content, downloading them and updating src attributes.
    
    Args:
        html_content (str): HTML content containing image tags
        article_id (str): ID of the article
        
    Returns:
        str: Updated HTML content with local image paths
    """
    if not html_content:
        return html_content
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        img_tags = soup.find_all('img')
        
        for img in img_tags:
            src = img.get('src')
            if src and (src.startswith('http://') or src.startswith('https://')):
                # Download the image
                local_path = download_image(src, article_id)
                
                if local_path:
                    # Update the src attribute
                    img['src'] = local_path
                    img['data-original-src'] = src
                else:
                    # If download failed, add a note
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
        html_content (str): HTML content containing image tags
        
    Returns:
        list: List of image URLs
    """
    if not html_content:
        return []
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        img_tags = soup.find_all('img')
        
        urls = []
        for img in img_tags:
            src = img.get('src')
            if src and (src.startswith('http://') or src.startswith('https://')):
                urls.append(src)
        
        return urls
        
    except Exception as e:
        logger.error(f"Error extracting image URLs: {e}", exc_info=True)
        return []

# Test function
def test_image_download():
    """Test the image download functionality."""
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