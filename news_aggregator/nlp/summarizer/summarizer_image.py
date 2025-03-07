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

from summarizer_logging import get_logger
from summarizer_config import OUTPUT_HTML_DIR, get_config_value, CONFIG

logger = get_logger(__name__)

# Directory for storing images
IMAGES_DIR = os.path.join(OUTPUT_HTML_DIR, "images")

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
        headers = {
            'User-Agent': 'MySummarizer/1.0 (your.email@example.com)'
        }
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        logger.debug(f"Image download response status: {response.status_code}")

        # Check if the response contains an image
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            logger.error(f"URL did not return image content: {url} (Content-Type: {content_type})")
            return None

        if response.status_code == 200:
            # Write the image to file once
            with open(filepath, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
        else:
            logger.error(f"Response status code {response.status_code} for URL: {url}")
            return None

        # Verify file existence explicitly
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            relative_path = os.path.join("images", filename)
            logger.info(f"Downloaded image successfully:\n"
                        f"    Original URL: {url}\n"
                        f"    Local path: {relative_path}\n"
                        f"    Absolute path: {filepath}\n"
                        f"    Size: {file_size} bytes, Content-Type: {content_type}")

            return {
                "path": relative_path,
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
    """
    Extract better search terms from the query, title, and entity list.
    
    Args:
        query (str): Original search query
        title (str): Article title
        content (str, optional): Article content for context
        entity_list (list, optional): List of named entities from the article
        
    Returns:
        list: Prioritized list of search terms to try
    """
    search_terms = []
    
    # Start with the original query
    if query:
        search_terms.append(query)
    
    # Add entity-based search terms if available
    if entity_list and isinstance(entity_list, list):
        # Prioritize named entities (people, organizations, locations)
        named_entities = [entity for entity in entity_list 
                         if isinstance(entity, dict) and entity.get('type') in 
                         ['PERSON', 'ORGANIZATION', 'LOCATION', 'GPE']]
        
        if named_entities:
            top_entities = [entity.get('text') for entity in sorted(named_entities, 
                                              key=lambda x: x.get('count', 0), 
                                              reverse=True)[:3]]
            entity_query = " ".join(top_entities)
            if entity_query and entity_query not in search_terms:
                search_terms.append(entity_query)
    
    # Add title-based search terms
    if title:
        # Full title if it's short enough
        if len(title.split()) <= 5 and title not in search_terms:
            search_terms.append(title)
        
        # First half of the title (typically contains the main subject)
        title_words = title.split()
        if len(title_words) > 3:
            first_half = " ".join(title_words[:len(title_words)//2])
            if first_half not in search_terms:
                search_terms.append(first_half)
        
        # Extract significant words from title (excluding common words)
        common_words = ['the', 'a', 'an', 'in', 'on', 'at', 'of', 'to', 'and', 'or', 'for', 'with', 'by']
        significant_words = [word.lower() for word in re.findall(r'\b\w+\b', title) 
                            if len(word) > 3 and word.lower() not in common_words]
        
        if significant_words:
            sig_query = " ".join(significant_words[:3])
            if sig_query not in search_terms:
                search_terms.append(sig_query)
    
    # Add context-based fallback search terms
    if query or title or (content and isinstance(content, str)):
        # Check for certain topics and add specialized terms
        text_to_check = ((query or "") + " " + (title or "") + " " + ((content or "")[:500])).lower()

        context_terms = [
            ("prison", ["prison", "jail", "incarceration"]),
            ("protest", ["protest", "demonstration", "march"]),
            ("strike", ["strike", "labor action", "work stoppage"]),
            ("war", ["conflict", "battlefield", "military operation"]),
            ("election", ["voting", "campaign", "ballot"]),
            ("climate", ["environment", "global warming", "sustainability"]),
            ("health", ["medicine", "healthcare", "medical treatment"]),
            ("technology", ["innovation", "digital", "computer"]),
            ("business", ["company", "corporate", "industry"])
        ]
        
        for keyword, related_terms in context_terms:
            if keyword in text_to_check:
                for term in related_terms:
                    if term not in search_terms:
                        search_terms.append(term)
        
    # Add first word of query as fallback
    if query and " " in query and query.split()[0] not in search_terms:
        search_terms.append(query.split()[0])
    
    # Generic fallback
    search_terms.append("news")
    
    # Remove duplicates while preserving order
    unique_terms = []
    for term in search_terms:
        if term and term not in unique_terms:
            unique_terms.append(term)
    
    return unique_terms

def search_and_download_images(query, article_id, base_name, num_images, title=None, entity_list=None, content=None, requested_width=600):
    """
    Search for images on Wikimedia Commons using multiple strategies and download up to num_images.
    
    Args:
        query (str): Search query (derived from article keywords or title).
        article_id (str): ID of the article (used for naming images).
        base_name (str): Base name for image filenames (typically a sanitized article title).
        num_images (int): Number of images to download.
        title (str, optional): Article title for fallback search terms.
        entity_list (list, optional): List of named entities from the article.
        content (str, optional): Article content for context-based fallbacks.
        requested_width (int, optional): Desired width (in pixels) for the image thumbnail. Defaults to 600.
        
    Returns:
        list: A list of dictionaries, each containing 'url', 'caption', and 'alt'.
    """
    api_url = "https://commons.wikimedia.org/w/api.php"
    
    # Get a prioritized list of search terms
    search_queries = extract_search_terms(query, title, content, entity_list)
    
    logger.debug(f"Will try these search queries in order: {search_queries}")
    
    # Valid image extensions to filter results
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg']
    
    for current_query in search_queries:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {current_query}",  # Explicitly search for images
            "gsrnamespace": 6,  # File namespace
            "gsrlimit": num_images * 3,  # Get more results than needed to filter invalid formats
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": requested_width  # Request a thumbnail at the desired width
        }
        logger.debug(f"Searching Wikimedia Commons with query: '{current_query}' and params: {params}")

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (your.email@example.com)'
            }
            response = requests.get(api_url, headers=headers, params=params, timeout=10)
            logger.debug(f"API Request URL: {response.url}")
            logger.debug(f"Response status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"API request failed (status: {response.status_code}). Response: {response.text[:500]}")
                continue  # Try next query

            try:
                json_response = response.json()
                logger.debug(f"Wikimedia Commons API JSON response (truncated): {json.dumps(json_response, indent=2)[:500]}")
            except ValueError as e:
                logger.error(f"Failed to parse JSON from Wikimedia response: {e}")
                continue  # Try next query

            if 'query' not in json_response or 'pages' not in json_response['query']:
                logger.info(f"No images found in response for query '{current_query}'")
                continue  # Try next query
            
            time.sleep(1)
            images = []
            pages = json_response["query"]["pages"]
            sorted_pages = sorted(pages.values(), key=lambda p: int(p.get("pageid", 0)))
            
            for idx, page in enumerate(sorted_pages, start=1):
                imageinfo = page.get("imageinfo", [])
                if not imageinfo:
                    logger.debug(f"No imageinfo found for page: {page.get('title', 'Unknown')}")
                    continue
                
                info = imageinfo[0]
                # Use the thumbnail URL if available (at requested_width); otherwise, fall back to the original URL
                image_url = info.get("thumburl") or info.get("url")
                
                # Skip if not a valid image URL or not a valid image extension
                if not image_url:
                    continue
                    
                # Check if it has a valid image extension
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
                    if caption and '<' in caption:  # If caption has HTML
                        caption = BeautifulSoup(caption, 'html.parser').get_text()
                
                # Use page title as fallback for caption
                if not caption:
                    caption = page.get("title", "Image").replace("File:", "").replace("_", " ")
                
                image_data = download_image(image_url, article_id, base_name=base_name, counter=idx)
                if image_data:
                    images.append({
                        "url": image_data["path"],
                        "caption": caption[:100],  # Limit caption length
                        "alt": caption[:100]       # Use caption as alt text
                    })
                
                if len(images) >= num_images:
                    break
            
            # If we found at least one image, return the results
            if images:
                logger.info(f"Downloaded {len(images)} images for query: '{current_query}'")
                return images
            
        except Exception as e:
            logger.error(f"Error searching for images on Wikimedia Commons with query '{current_query}': {e}", exc_info=True)
    
    # If all queries failed, return an empty list
    logger.warning("All Wikimedia queries failed to find images. No images will be included.")
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
        standalone_imgs = [img for img in soup.find_all('img') if img.parent.name != 'figure' and 
                          (not img.parent.get('class') or IMAGE_CLASSES["featured"] not in img.parent.get('class', []))]
        
        for img in standalone_imgs:
            src = img.get('src')
            if src and (src.startswith('http://') or src.startswith('https://')):
                image_data = download_image(src, article_id)
                if image_data:
                    img['src'] = image_data["path"]
                    img['data-original-src'] = src
                    
                    # If the image isn't in a proper container, wrap it in one
                    if img.parent.name not in ['div', 'figure'] or not img.parent.get('class'):
                        # Create a figure container
                        figure = soup.new_tag('figure')
                        figure['class'] = IMAGE_CLASSES["article"]
                        
                        # Create a figcaption if alt text exists
                        if img.get('alt') and img.get('alt') != 'Image':
                            figcaption = soup.new_tag('figcaption')
                            figcaption.string = img.get('alt')
                            
                            # Replace the img with the new structure
                            img_copy = img.copy()
                            img.replace_with(figure)
                            figure.append(img_copy)
                            figure.append(figcaption)
                        else:
                            # Just wrap the image without a caption
                            img_copy = img.copy()
                            img.replace_with(figure)
                            figure.append(img_copy)
                else:
                    img['alt'] = f"{img.get('alt', 'Image')} (failed to download)"
                    img['title'] = f"Failed to download: {src}"
        
        # Process images in figures or featured-image divs
        for container in soup.find_all(['figure', 'div']):
            if container.name == 'div' and (not container.get('class') or 
                                            IMAGE_CLASSES["featured"] not in container.get('class', [])):
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
            
            # Ensure the container has the proper class
            if container.name == 'figure' and not container.get('class'):
                container['class'] = IMAGE_CLASSES["article"]
            
            # Ensure it has a figcaption if needed
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
    headers = {
        'User-Agent': 'MySummarizerTest/1.0 (your.email@example.com) requests/2.25.1'
    }

    logger.debug(f"Testing image download with URL: {test_url}")
    
    try:
        response = requests.get(test_url, headers=headers, stream=True, timeout=10)
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
