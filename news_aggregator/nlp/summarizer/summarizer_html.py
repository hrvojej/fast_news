# summarizer_html.py
"""
Module for HTML processing and file operations for the article summarization system.
"""

import os
import re
import html
import requests

from datetime import datetime
from bs4 import BeautifulSoup

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
        
        # Clean the summary HTML
        processed_summary = clean_and_normalize_html(summary)

        # --- Get images based on keywords ---
        featured_image_html = ""
        if keywords and isinstance(keywords, list) and len(keywords) > 0:
            # Create a sanitized base name for image filenames
            base_name = re.sub(r'[^\w\s-]', '', title if title else "Article")
            base_name = re.sub(r'\s+', '_', base_name)[:30]  # Limit length
            
            # Log available keywords for debugging
            logger.debug(f"Keywords for Wikimedia image search: {keywords}")
            
            # Create search query using top keywords
            # Use title as fallback if no keywords available
            search_terms = keywords[:3] if keywords else [title.split()[:3]]
            image_query = " ".join([term for term in search_terms if term])
            
            # If still no query, use fallback
            if not image_query:
                image_query = "news article"
            
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
            
            # Create featured image HTML if images were found
            if images and len(images) > 0:
                featured_image = images[0]  # Use first image as featured image
                featured_image_html = (
                    f'<div style="text-align:center; margin:1.2em 0 1.8em 0;">'
                    f'<img src="{featured_image["url"]}" alt="{featured_image["caption"]}" '
                    f'style="max-width:100%; border-radius:6px; box-shadow:0 2px 12px rgba(0,0,0,0.1);">'
                    f'<p style="font-size:0.9em; color:#666; margin-top:0.5em;">{featured_image["caption"]}</p>'
                    f'</div>'
                )
                
                # Add additional images within the summary if there are more
                if len(images) > 1:
                    additional_images_html = ""
                    for idx, img in enumerate(images[1:], 1):
                        # Alternate image alignment (left/right)
                        alignment = "left" if idx % 2 == 1 else "right"
                        float_style = f"float:{alignment}; margin:{alignment}:0 1.5em 1em 0;" if alignment == "left" else f"float:{alignment}; margin:0 0 1em 1.5em;"
                        
                        additional_images_html += (
                            f'<div style="{float_style} max-width:40%;">'
                            f'<img src="{img["url"]}" alt="{img["caption"]}" '
                            f'style="width:100%; border-radius:4px; box-shadow:0 2px 6px rgba(0,0,0,0.08);">'
                            f'<p style="font-size:0.8em; margin-top:0.3em; color:#666; text-align:center;">{img["caption"]}</p>'
                            f'</div>'
                        )
                    
                    # Insert additional images into the processed summary
                    # Find a good insertion point after the first paragraph
                    first_p_end = processed_summary.find('</p>')
                    if first_p_end > 0:
                        insert_pos = first_p_end + 4  # After </p>
                        processed_summary = processed_summary[:insert_pos] + additional_images_html + processed_summary[insert_pos:]
        
        # Process any images already in the summary, downloading them and updating src attributes
        processed_summary = process_images_in_html(processed_summary, article_id)
        
        # Create filename and filepath
        filename = create_filename_from_title(title, url, article_id)
        filepath = os.path.join(OUTPUT_HTML_DIR, filename)
        logger.debug(f"Preparing to save HTML to: {filepath}")
        
        # Create final HTML content
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title or f'Article {article_id}')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .article-meta {{ color: #777; margin-bottom: 20px; }}
        .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 30px; }}
        .api-response {{ background-color: #eef; padding: 15px; border-radius: 5px; white-space: pre-wrap; overflow-x: auto; }}
        .article-content {{ border-top: 1px solid #ddd; margin-top: 30px; padding-top: 20px; }}
        .footer {{ margin-top: 30px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 0.8em; color: #777; }}
        .clearfix {{ clear: both; }}
    </style>
</head>
<body>
    <h1>{html.escape(title or f'Article {article_id}')}</h1>
    <div class="article-meta">
        <p>Article ID: {article_id}</p>
        <p>URL: <a href="{html.escape(url or '#')}">{html.escape(url or 'N/A')}</a></p>
        <p>Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    {featured_image_html}
    
    <h2>Summary</h2>
    <div class="summary">
        {processed_summary}
        <div class="clearfix"></div>
    </div>    
    <h2>Raw API Response</h2>
    <div class="api-response">
        {html.escape(response_text if response_text else 'No API response available')}
    </div>
    
    <div class="article-content">
        <h2>Original Article Content</h2>
        <div>
            {html.escape(content).replace('\n', '<br>') if content else 'No content available'}
        </div>
    </div>
    
    <div class="footer">
        <p>Generated by Article Summarizer using Gemini API</p>
    </div>
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

        
        # --- Remove Unwanted "Entity Overview" Block ---
        # If "Entity Overview:" appears before "Keywords:" in the summary, remove it.
        if "Keywords:" in summary and "Entity Overview:" in summary:
            entity_index = summary.find("Entity Overview:")
            keywords_index = summary.find("Keywords:")
            if entity_index < keywords_index:
                end_index = summary.find("</div>", entity_index)
                if end_index != -1:
                    summary = summary[:entity_index] + summary[end_index+6:]
        
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
        
        # Create final HTML content by prepending the featured image block (if available)
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title or f'Article {article_id}')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .article-meta {{ color: #777; margin-bottom: 20px; }}
        .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 30px; }}
        .api-response {{ background-color: #eef; padding: 15px; border-radius: 5px; white-space: pre-wrap; }}
        .article-content {{ border-top: 1px solid #ddd; margin-top: 30px; padding-top: 20px; }}
        .footer {{ margin-top: 30px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 0.8em; color: #777; }}
    </style>
</head>
<body>
    <h1>{html.escape(title or f'Article {article_id}')}</h1>
    <div class="article-meta">
        <p>Article ID: {article_id}</p>
        <p>URL: <a href="{html.escape(url or '#')}">{html.escape(url or 'N/A')}</a></p>
        <p>Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    {featured_image_html}
    
    <h2>Summary</h2>
    <div class="summary">
        {processed_summary}
    </div>    
    <h2>Raw API Response</h2>
    <div class="api-response">
        {html.escape(response_text if response_text else 'No API response available')}
    </div>
    
    <div class="article-content">
        <h2>Original Article Content</h2>
        <div>
            {html.escape(content).replace('\n', '<br>') if content else 'No content available'}
        </div>
    </div>
    
    <div class="footer">
        <p>Generated by Article Summarizer using Gemini API</p>
    </div>
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

    try:
        # Ensure output directory exists
        ensure_output_directory()
        
        # Extract featured image URL and alt text from summary if present
        featured_image_html = ""
        lines = summary.splitlines()
        # Filter out empty lines
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        if non_empty_lines and non_empty_lines[0].startswith("http"):
            image_url = non_empty_lines[0]
            alt_text = non_empty_lines[1] if len(non_empty_lines) > 1 else "Featured image"
            # Remove these lines from summary for further processing
            summary = "\n".join(non_empty_lines[2:]) if len(non_empty_lines) > 2 else ""
            # Create HTML snippet for the featured image
            featured_image_html = (
                f'<div style="text-align:center; margin:1.2em 0 1.8em 0;">'
                f'<img src="{image_url}" alt="{alt_text}" '
                f'style="max-width:100%; border-radius:6px; box-shadow:0 2px 12px rgba(0,0,0,0.1);">'
                f'</div>'
            )
        
        # Clean the remaining summary HTML
        processed_summary = clean_and_normalize_html(summary)
        # Process any images in the summary, downloading them and updating src attributes
        processed_summary = process_images_in_html(processed_summary, article_id)
        
        # Create filename and filepath
        filename = create_filename_from_title(title, url, article_id)
        filepath = os.path.join(OUTPUT_HTML_DIR, filename)
        
        # Create final HTML content by prepending the featured image block (if available)
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title or f'Article {article_id}')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .article-meta {{ color: #777; margin-bottom: 20px; }}
        .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 30px; }}
        .api-response {{ background-color: #eef; padding: 15px; border-radius: 5px; white-space: pre-wrap; }}
        .article-content {{ border-top: 1px solid #ddd; margin-top: 30px; padding-top: 20px; }}
        .footer {{ margin-top: 30px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 0.8em; color: #777; }}
    </style>
</head>
<body>
    <h1>{html.escape(title or f'Article {article_id}')}</h1>
    <div class="article-meta">
        <p>Article ID: {article_id}</p>
        <p>URL: <a href="{html.escape(url or '#')}">{html.escape(url or 'N/A')}</a></p>
        <p>Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    {featured_image_html}
    
    <h2>Summary</h2>
    <div class="summary">
        {processed_summary}
    </div>    
    <h2>Raw API Response</h2>
    <div class="api-response">
        {html.escape(response_text if response_text else 'No API response available')}
    </div>
    
    <div class="article-content">
        <h2>Original Article Content</h2>
        <div>
            {html.escape(content).replace('\n', '<br>') if content else 'No content available'}
        </div>
    </div>
    
    <div class="footer">
        <p>Generated by Article Summarizer using Gemini API</p>
    </div>
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
    Save the article and its summary as an HTML file.
    
    Args:
        article_id (str): The article ID
        title (str): The article title
        url (str): The article URL
        content (str): The original article content
        summary (str): The generated summary
        response_text (str): The raw API response
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure output directory exists
        ensure_output_directory()
        
        # Clean the summary HTML
        processed_summary = clean_and_normalize_html(summary)
        # Process any images in the summary, downloading them and updating src attributes
        processed_summary = process_images_in_html(processed_summary, article_id)
        logger.debug(f"Processed summary (first 100 chars): {processed_summary[:100]}...")
        
        # Create filename
        filename = create_filename_from_title(title, url, article_id)
        filepath = os.path.join(OUTPUT_HTML_DIR, filename)
        logger.debug(f"Preparing to save HTML to: {filepath}")
        
        # Create HTML content
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title or f'Article {article_id}')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .article-meta {{ color: #777; margin-bottom: 20px; }}
        .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 30px; }}
        .api-response {{ background-color: #eef; padding: 15px; border-radius: 5px; white-space: pre-wrap; }}
        .article-content {{ border-top: 1px solid #ddd; margin-top: 30px; padding-top: 20px; }}
        .footer {{ margin-top: 30px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 0.8em; color: #777; }}
        .named-individual {{ color: #D55E00; font-weight: bold; text-decoration: underline; }}
        .roles-categories {{ color: #0072B2; font-weight: bold; }}
        .orgs-products {{ color: #009E73; font-weight: bold; }}
        .key-actions {{ color: #CC79A7; font-weight: bold; }}
        hr {{ border: 0; height: 1px; background-color: #ddd; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>{html.escape(title or f'Article {article_id}')}</h1>
    <div class="article-meta">
        <p>Article ID: {article_id}</p>
        <p>URL: <a href="{html.escape(url or '#')}">{html.escape(url or 'N/A')}</a></p>
        <p>Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <h2>Summary</h2>
    <div class="summary">
        {processed_summary}
    </div>    
    <h2>Raw API Response</h2>
    <div class="api-response">
        {html.escape(response_text if response_text else 'No API response available')}
    </div>
    
    <div class="article-content">
        <h2>Original Article Content</h2>
        <div>
            {html.escape(content).replace('\n', '<br>') if content else 'No content available'}
        </div>
    </div>
    
    <div class="footer">
        <p>Generated by Article Summarizer using Gemini API</p>
    </div>
</body>
</html>"""
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
            f.flush()
        
        # Verify file was created
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