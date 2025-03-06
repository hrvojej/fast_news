# summarizer_html.py
"""
Module for HTML processing and file operations for the article summarization system.
"""

import os
import re
import html
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from summarizer_logging import get_logger
from summarizer_config import OUTPUT_HTML_DIR, ensure_output_directory
from summarizer_image import process_images_in_html


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

def clean_and_normalize_html(text):
    """
    Clean and normalize HTML content to ensure it's valid.
    
    Args:
        text (str): The HTML text to clean
        
    Returns:
        str: Cleaned and normalized HTML
    """
    if not text or not isinstance(text, str):
        logger.warning("Invalid input to clean_and_normalize_html")
        return "<div>No content available</div>"
    
    try:
        # Extract HTML from code blocks if needed
        if "```html" in text:
            try:
                text = text.split('```html')[1].split('```')[0].strip()
                logger.debug("Extracted HTML from code block")
            except Exception as e:
                logger.warning(f"Error extracting HTML from code block: {e}")
        
        # Remove any heading markdown
        text = re.sub(r'^#\s+', '', text, flags=re.MULTILINE)
        
        # Use BeautifulSoup to parse and clean the HTML
        soup = BeautifulSoup(text, 'html.parser')
        
        # Check if the cleaned HTML has any content
        cleaned_html = str(soup)
        if not soup.find() or cleaned_html.strip() == "":
            logger.warning("Empty or invalid HTML after cleaning")
            return f"<div>{html.escape(text)}</div>"
        
        # Ensure the HTML is wrapped in a div if not already
        if soup.find() and soup.find().name != "div":
            # Check if we have multiple top-level elements
            top_level_elements = [tag for tag in soup.children if tag.name is not None]
            if len(top_level_elements) > 1:
                # Wrap multiple top-level elements in a div
                new_soup = BeautifulSoup("<div></div>", "html.parser")
                div = new_soup.div
                for element in top_level_elements:
                    div.append(element.extract())
                cleaned_html = str(new_soup)
                logger.debug("Wrapped multiple elements in a div")
        
        logger.debug(f"Cleaned HTML (first 100 chars): {cleaned_html[:100]}...")
        return cleaned_html
        
    except Exception as e:
        logger.error(f"Error cleaning HTML: {e}", exc_info=True)
        return f"<div>{html.escape(text)}</div>"

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

def save_as_html(article_id, title, url, content, summary, response_text, keywords=None):
    """
    Save the article and its summary as an HTML file, with images from Wikimedia based on keywords.
    
    Args:
        article_id (str): The article ID
        title (str): The article title
        url (str): The article URL
        content (str): The original article content
        summary (str): The generated summary
        response_text (str): The raw API response
        keywords (list, optional): List of article keywords for Wikimedia image searches
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure output directory exists
        ensure_output_directory()
        
        # Debug the raw summary and response
        logger.debug(f"Raw summary type: {type(summary)}")
        logger.debug(f"Raw summary preview: {summary[:300] if summary else 'None'}")
        
        # Extract HTML content properly
        processed_summary = ""
        if summary and isinstance(summary, str):
            # Check if summary contains code blocks
            if "```html" in summary:
                try:
                    # Extract the HTML content from the code block
                    summary = summary.split("```html")[1].split("```")[0].strip()
                    logger.debug("Extracted HTML from code block")
                except Exception as e:
                    logger.warning(f"Error extracting HTML from code block: {e}")
            
            # Try to clean and normalize the HTML content
            processed_summary = clean_and_normalize_html(summary)
        else:
            logger.warning(f"Invalid summary content: {type(summary)}")
            processed_summary = "<div>No valid summary content available</div>"
        
        # Verification step
        logger.debug(f"Processed summary length: {len(processed_summary)}")
        logger.debug(f"Processed summary preview: {processed_summary[:300]}")
        
        # If processed_summary is empty or just a placeholder, try to extract content from the API response
        if not processed_summary or processed_summary == "<div>No content available</div>" or processed_summary == "<div>No valid summary content available</div>":
            logger.warning("Processed summary is empty, attempting to extract from raw API response")
            try:
                # Try to find HTML content in the API response
                if response_text and "```html" in response_text:
                    html_content = response_text.split("```html")[1].split("```")[0].strip()
                    if html_content:
                        processed_summary = clean_and_normalize_html(html_content)
                        logger.info("Successfully extracted HTML content from API response")
                elif response_text and "<html" in response_text or "<div" in response_text:
                    # Try to extract HTML content using regex
                    import re
                    html_match = re.search(r'(<div.*?>.*?</div>|<html.*?>.*?</html>)', response_text, re.DOTALL)
                    if html_match:
                        html_content = html_match.group(0)
                        processed_summary = clean_and_normalize_html(html_content)
                        logger.info("Successfully extracted HTML content from API response using regex")
            except Exception as e:
                logger.error(f"Error extracting HTML from API response: {e}")
        
        # --- Get images based on keywords ---
        featured_image_html = ""
        if keywords and isinstance(keywords, list) and len(keywords) > 0:
            # Create a sanitized base name for image filenames
            base_name = re.sub(r'[^\w\s-]', '', title if title else "Article")
            base_name = re.sub(r'\s+', '_', base_name)[:30]  # Limit length
            
            # Log available keywords for debugging
            logger.debug(f"Keywords for Wikimedia image search: {keywords}")
            
            # Create search query using top keywords
            search_terms = keywords[:3] if keywords else []
            
            # If no keywords, try to use words from the title
            if not search_terms and title:
                title_words = [word.lower() for word in re.findall(r'\b\w+\b', title) 
                              if len(word) > 3 and word.lower() not in ['the', 'and', 'with', 'from', 'that', 'this']]
                search_terms = title_words[:3]
            
            image_query = " ".join([term for term in search_terms if term])
            
            # If still no query, try additional contextual terms
            if not image_query:
                if 'prison' in title.lower() or 'prison' in content.lower()[:500]:
                    image_query = "prison"
                elif 'strike' in title.lower() or 'strike' in content.lower()[:500]:
                    image_query = "strike protest"
            
            if image_query:
                logger.info(f"Using Wikimedia search query: '{image_query}'")
                
                # Calculate number of images to request based on content length
                content_length = len(content) if content else 0
                from summarizer_config import CONFIG, get_config_value
                short_threshold = get_config_value(CONFIG, 'image_search', 'short_threshold', 3000)
                medium_threshold = get_config_value(CONFIG, 'image_search', 'medium_threshold', 7000)
                max_images = get_config_value(CONFIG, 'image_search', 'max_images', 3)
                
                if content_length < short_threshold:
                    num_images = 1
                elif content_length < medium_threshold:
                    num_images = 2
                else:
                    num_images = max_images
                
                # Search for and download images from Wikimedia
                from summarizer_image import search_and_download_images
                images = search_and_download_images(image_query, article_id, base_name, num_images)
                
                logger.info(f"Found {len(images)} images for article {article_id}")
                
                # Create featured image HTML if images were found
                if images and len(images) > 0:
                    featured_image = images[0]  # Use first image as featured image
                    
                    # Make sure the image URL is properly formatted
                    if not featured_image["url"].startswith(("http://", "https://", "/")):
                        featured_image["url"] = "/" + featured_image["url"]
                    
                    featured_image_html = (
                        f'<div class="featured-image">'
                        f'<img src="{featured_image["url"]}" alt="{featured_image["caption"]}">'
                        f'<figcaption>{featured_image["caption"]}</figcaption>'
                        f'</div>'
                    )
        
        # Create filename and filepath
        filename = create_filename_from_title(title, url, article_id)
        filepath = os.path.join(OUTPUT_HTML_DIR, filename)
        logger.debug(f"Preparing to save HTML to: {filepath}")
        
        # Determine the correct relative path for static assets
        relative_static_path = "../../static"  # Two levels up from articles directory
        
        # Create final HTML content
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title or f'Article {article_id}')}</title>
    <link rel="stylesheet" href="{relative_static_path}/css/main.css">
    <link rel="stylesheet" href="{relative_static_path}/css/article.css">
    <style>
        /* Fallback styles in case external CSS fails to load */
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .article-meta {{ color: #777; margin-bottom: 20px; }}
        .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 30px; }}
        .api-response {{ background-color: #eef; padding: 15px; border-radius: 5px; white-space: pre-wrap; overflow-x: auto; }}
        .article-content {{ border-top: 1px solid #ddd; margin-top: 30px; padding-top: 20px; }}
        .featured-image {{ text-align: center; margin: 1.2em 0; }}
        .featured-image img {{ max-width: 100%; border-radius: 6px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); }}
        .featured-image figcaption {{ font-size: 0.9em; color: #666; margin-top: 0.5em; }}
        .clearfix {{ clear: both; }}
    </style>
</head>
<body>
<header class="site-header">
    <div class="header-content">
        <div class="logo">
            <a href="/">Article Summarizer</a>
        </div>
        <nav class="main-nav">
            <ul>
                <li><a href="/">Home</a></li>
                <li><a href="/stats">Statistics</a></li>
                <li><a href="/about">About</a></li>
            </ul>
        </nav>
    </div>
</header>    
    <div class="container">
    <h1>{html.escape(title or f'Article {article_id}')}</h1>
    
    <div class="article-meta">
        <p>Article ID: {article_id}</p>
        <p>URL: <a href="{html.escape(url or '#')}">{html.escape(url or 'N/A')}</a></p>
        <p>Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    {featured_image_html}
    
    <div class="summary">
        <h2>Summary</h2>
        {processed_summary}
        <div class="clearfix"></div>
    </div>
    
    <div class="api-response">
        <h2>Raw API Response</h2>
        <pre>{html.escape(response_text if response_text else 'No API response available')}</pre>
    </div>
    
    <div class="article-content">
        <h2>Original Article Content</h2>
        <div>
            {html.escape(content).replace('\n', '<br>') if content else 'No content available'}
        </div>
    </div>
    </div>
    
<aside class="sidebar">
    <div class="sidebar-content">
        <h3>Recent Summaries</h3>
        <ul class="recent-list">
                <li>No recent articles</li>
        </ul>
    </div>
    
<div class="ad-container">
    <!-- Ad placeholder -->
    <div class="ad-unit">
        <div class="ad-placeholder">
            <p>Advertisement</p>
        </div>
    </div>
</div></aside>    
<footer class="site-footer">
    <div class="footer-content">
        <p>&copy; {datetime.now().year} Article Summarizer. All rights reserved.</p>
    </div>
</footer>    
        <script src="{relative_static_path}/js/main.js"></script>
</body>
</html>"""
        
        # Write the HTML file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
            f.flush()
        
        # Verify file creation
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            logger.info(f"Successfully saved HTML output to {filepath} (size: {file_size} bytes)")
            return True
        else:
            logger.error(f"File wasn't created despite no errors: {filepath}")
            return False
    except Exception as e:
        logger.error(f"Error saving HTML file {filepath if 'filepath' in locals() else 'unknown'}", exc_info=True)
        return False
    """
    Save the article and its summary as an HTML file, with images from Wikimedia based on keywords.
    
    Args:
        article_id (str): The article ID
        title (str): The article title
        url (str): The article URL
        content (str): The original article content
        summary (str): The generated summary
        response_text (str): The raw API response
        keywords (list, optional): List of article keywords for Wikimedia image searches
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure output directory exists
        ensure_output_directory()
        
        # --- Featured Image Extraction ---
        featured_image_html = ""
        lines = summary.splitlines()
        image_section = []
        rest_lines = []
        marker_found = False
        for line in lines:
            if line.strip() == "---END IMAGE URL---":
                marker_found = True
                continue
            if not marker_found:
                image_section.append(line.strip())
            else:
                rest_lines.append(line)
        if marker_found and image_section:
            image_url = image_section[0] if image_section[0].startswith("http") else ""
            alt_text = image_section[1] if len(image_section) > 1 else "Featured image"
            # --- Verify the image URL ---
            if image_url:
                try:
                    head_response = requests.head(image_url, timeout=5)
                    if head_response.status_code != 200:
                        # Image URL is broken; do not embed any image.
                        image_url = ""
                except Exception as e:
                    # In case of any exception (e.g. timeout), treat as not found.
                    image_url = ""
            if image_url:
                featured_image_html = (
                    f'<div style="text-align:center; margin:1.2em 0 1.8em 0;">'
                    f'<img src="{image_url}" alt="{alt_text}" '
                    f'style="max-width:100%; border-radius:6px; box-shadow:0 2px 12px rgba(0,0,0,0.1);">'
                    f'</div>'
                )
        # Use the remaining lines as the summary content
        summary = "\n".join(rest_lines)

        # --- Get images based on keywords ---
        if not featured_image_html and keywords and isinstance(keywords, list) and len(keywords) > 0:
            # Create a sanitized base name for image filenames
            base_name = re.sub(r'[^\w\s-]', '', title if title else "Article")
            base_name = re.sub(r'\s+', '_', base_name)[:30]  # Limit length
            
            # Log available keywords for debugging
            logger.debug(f"Keywords for Wikimedia image search: {keywords}")
            
            # Create search query using top keywords
            search_terms = keywords[:3] if keywords else []
            
            # If no keywords, try to use words from the title
            if not search_terms and title:
                title_words = [word.lower() for word in re.findall(r'\b\w+\b', title) 
                              if len(word) > 3 and word.lower() not in ['the', 'and', 'with', 'from', 'that', 'this']]
                search_terms = title_words[:3]
            
            image_query = " ".join([term for term in search_terms if term])
            
            # If still no query, use fallback based on article title or content
            if not image_query and title:
                image_query = " ".join(title.split()[:3])
            
            logger.info(f"Using Wikimedia search query: '{image_query}'")
            
            # Calculate number of images to request based on content length
            content_length = len(content) if content else 0
            from summarizer_config import CONFIG, get_config_value
            short_threshold = get_config_value(CONFIG, 'image_search', 'short_threshold', 3000)
            medium_threshold = get_config_value(CONFIG, 'image_search', 'medium_threshold', 7000)
            max_images = get_config_value(CONFIG, 'image_search', 'max_images', 3)
            
            if content_length < short_threshold:
                num_images = 1
            elif content_length < medium_threshold:
                num_images = 2
            else:
                num_images = max_images
            
            # Search for and download images from Wikimedia
            from summarizer_image import search_and_download_images
            images = search_and_download_images(image_query, article_id, base_name, num_images)
            
            logger.info(f"Found {len(images)} images for article {article_id}")
            
            # Create featured image HTML if images were found
            if images and len(images) > 0:
                featured_image = images[0]  # Use first image as featured image
                
                # Make sure the image URL is properly formatted for HTML
                if not featured_image["url"].startswith(("http://", "https://", "/")):
                    featured_image["url"] = "/" + featured_image["url"]
                
                featured_image_html = (
                    f'<div class="featured-image">'
                    f'<img src="{featured_image["url"]}" alt="{featured_image["caption"]}">'
                    f'<figcaption>{featured_image["caption"]}</figcaption>'
                    f'</div>'
                )
        
        # --- Clean up Incomplete HTML Fragments ---
        # Remove any stray <li> fragments that might be incomplete.
        summary = re.sub(r'<li style="margin-bottom:0; padding-left:1\.[^>]*>', '', summary)
        
        # Clean the remaining summary HTML
        processed_summary = clean_and_normalize_html(summary)
        # Process any images in the summary, downloading them and updating src attributes
        processed_summary = process_images_in_html(processed_summary, article_id)
        
        # Create filename and filepath
        filename = create_filename_from_title(title, url, article_id)
        filepath = os.path.join(OUTPUT_HTML_DIR, filename)
        logger.debug(f"Preparing to save HTML to: {filepath}")
        
        # Determine the correct relative path for static assets
        relative_static_path = "../../static"  # Two levels up from articles directory
        
        # Create final HTML content
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title or f'Article {article_id}')}</title>
    <link rel="stylesheet" href="{relative_static_path}/css/main.css">
    <link rel="stylesheet" href="{relative_static_path}/css/article.css">
    <style>
        /* Fallback styles in case external CSS fails to load */
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .article-meta {{ color: #777; margin-bottom: 20px; }}
        .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 30px; }}
        .api-response {{ background-color: #eef; padding: 15px; border-radius: 5px; white-space: pre-wrap; overflow-x: auto; }}
        .article-content {{ border-top: 1px solid #ddd; margin-top: 30px; padding-top: 20px; }}
        .featured-image {{ text-align: center; margin: 1.2em 0; }}
        .featured-image img {{ max-width: 100%; border-radius: 6px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); }}
        .featured-image figcaption {{ font-size: 0.9em; color: #666; margin-top: 0.5em; }}
        .clearfix {{ clear: both; }}
    </style>
</head>
<body>
<header class="site-header">
    <div class="header-content">
        <div class="logo">
            <a href="/">Article Summarizer</a>
        </div>
        <nav class="main-nav">
            <ul>
                <li><a href="/">Home</a></li>
                <li><a href="/stats">Statistics</a></li>
                <li><a href="/about">About</a></li>
            </ul>
        </nav>
    </div>
</header>    
    <div class="container">
    <h1>{html.escape(title or f'Article {article_id}')}</h1>
    
    <div class="article-meta">
        <p>Article ID: {article_id}</p>
        <p>URL: <a href="{html.escape(url or '#')}">{html.escape(url or 'N/A')}</a></p>
        <p>Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    {featured_image_html}
    
    <div class="summary">
        <h2>Summary</h2>
        {processed_summary}
        <div class="clearfix"></div>
    </div>
    
    <div class="api-response">
        <h2>Raw API Response</h2>
        <pre>{html.escape(response_text if response_text else 'No API response available')}</pre>
    </div>
    
    <div class="article-content">
        <h2>Original Article Content</h2>
        <div>
            {html.escape(content).replace('\n', '<br>') if content else 'No content available'}
        </div>
    </div>
    </div>
    
<aside class="sidebar">
    <div class="sidebar-content">
        <h3>Recent Summaries</h3>
        <ul class="recent-list">
                <li>No recent articles</li>
        </ul>
    </div>
    
<div class="ad-container">
    <!-- Ad placeholder -->
    <div class="ad-unit">
        <div class="ad-placeholder">
            <p>Advertisement</p>
        </div>
    </div>
</div></aside>    
<footer class="site-footer">
    <div class="footer-content">
        <p>&copy; {datetime.now().year} Article Summarizer. All rights reserved.</p>
    </div>
</footer>    
        <script src="{relative_static_path}/js/main.js"></script>
</body>
</html>"""
        
        # Write the HTML file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
            f.flush()
        
        # Verify file creation
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            logger.info(f"Successfully saved HTML output to {filepath} (size: {file_size} bytes)")
            return True
        else:
            logger.error(f"File wasn't created despite no errors: {filepath}")
            return False
    except Exception as e:
        logger.error(f"Error saving HTML file {filepath if 'filepath' in locals() else 'unknown'}", exc_info=True)
        return False