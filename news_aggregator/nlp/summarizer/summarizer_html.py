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

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Compute the base directory of your project (assumes summarizer_html.py is two levels deep in nlp/summarizer)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# Define the template directory path relative to your project structure (note: no extra "web" folder)
TEMPLATE_DIR = os.path.join(BASE_DIR, 'frontend', 'templates')

jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)

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
    

def ensure_proper_classes(soup):
    """
    Ensure that only approved classes are used and elements have appropriate classes.
    This is a validation step to catch any inconsistencies from the Gemini response.
    """
    # Complete list of allowed classes from your CSS
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
        'secondary-detail', 'crucial-fact',
        
        # Interesting facts
        'facts-heading', 'facts-container', 'facts-list', 'fact-primary', 
        'fact-secondary', 'fact-conclusion', 'fact-bullet', 'fact-bullet-secondary',
        
        # Legend
        'legend-container', 'legend-heading', 'legend-grid', 'legend-item',
        
        # Separators and misc elements
        'separator', 'divider', 'gradient-divider', 'facts-divider',
        'entity-spacing', 'transition-text', 'date-numeric', 'number-numeric'
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
        
        # Process featured image extraction first
        featured_image_html = ""
        processed_summary = summary        
                              
        # Extract HTML content properly
        clean_summary = ""
        if processed_summary and isinstance(processed_summary, str):
            # Check if summary contains code blocks
            if "```html" in processed_summary:
                try:
                    processed_summary = processed_summary.split("```html")[1].split("```")[0].strip()
                    processed_summary = html.unescape(processed_summary)
                    logger.debug("Extracted and unescaped HTML from code block")
                except Exception as e:
                    logger.warning(f"Error extracting HTML from code block: {e}")

            # Remove any stray style-based list item formatting
            processed_summary = re.sub(r'<li style="[^>]*">', '<li>', processed_summary)
            
            # Clean and normalize the HTML content
            clean_summary = clean_and_normalize_html(processed_summary)
        else:
            logger.warning(f"Invalid summary content: {type(processed_summary)}")
            clean_summary = "<div>No valid summary content available</div>"
        
        # Attempt to extract Gemini-generated title from the cleaned summary HTML
        soup_summary = BeautifulSoup(clean_summary, 'html.parser')
        legend_container = soup_summary.find('div', class_='legend-container')
        if legend_container:
            legend_container.decompose()  # removes the entire legend section
        clean_summary = str(soup_summary)
        
        gemini_title_tag = soup_summary.find('h1', class_='article-title')
        gemini_title = gemini_title_tag.get_text(separator=' ', strip=True) if gemini_title_tag else title
        
        # If clean_summary is empty or just a placeholder, try with the API response
        if not clean_summary or clean_summary in ("<div>No content available</div>", "<div>No valid summary content available</div>"):
            logger.warning("Processed summary is empty, attempting to extract from raw API response")
            try:
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
        
        # If we still don't have a featured image, try to get one from Wikimedia
        if not featured_image_html and ((keywords and isinstance(keywords, list) and len(keywords) > 0) or (title and title.strip() != "")):
            base_name = re.sub(r'[^\w\s-]', '', title if title else "Article")
            base_name = re.sub(r'\s+', '_', base_name)[:30]  # Limit length
            
            logger.debug(f"Keywords for Wikimedia image search: {keywords}")
            
            search_terms = keywords[:3] if keywords else []
            if not search_terms and title:
                title_words = [word.lower() for word in re.findall(r'\b\w+\b', title) 
                               if len(word) > 3 and word.lower() not in ['the', 'and', 'with', 'from', 'that', 'this']]
                search_terms = title_words[:3]
            
            image_query = " ".join([term for term in search_terms if term])
            if not image_query:
                if 'prison' in title.lower() or 'prison' in content.lower()[:500]:
                    image_query = "prison"
                elif 'strike' in title.lower() or 'strike' in content.lower()[:500]:
                    image_query = "strike protest"
            
            if image_query:
                logger.info(f"Using Wikimedia search query: '{image_query}'")
                
                from summarizer_config import CONFIG, get_config_value
                short_threshold = get_config_value(CONFIG, 'image_search', 'short_threshold', 3000)
                medium_threshold = get_config_value(CONFIG, 'image_search', 'medium_threshold', 7000)
                max_images = get_config_value(CONFIG, 'image_search', 'max_images', 3)
                
                content_length = len(content) if content else 0
                if content_length < short_threshold:
                    num_images = 1
                elif content_length < medium_threshold:
                    num_images = 2
                else:
                    num_images = max_images
                
                images = search_and_download_images(image_query, article_id, base_name, num_images)
                logger.info(f"Found {len(images)} images for article {article_id}")
                
                if images and len(images) > 0:
                    featured_image = images[0]
                    featured_image_url = featured_image["url"].replace("\\", "/")
                    featured_image_html = (
                        f'<div class="featured-image">'
                        f'<img src="{featured_image_url}" alt="{featured_image["caption"]}">'
                        f'<figcaption>{featured_image["caption"]}</figcaption>'
                        f'</div>'
                    )
                    logger.info(f"Featured image added to HTML: {featured_image_url}")
                else:
                    featured_image_html = ""
                    logger.warning("No featured image available to add to HTML.")
                    
                if images and len(images) > 1:
                    second_image = images[1]
                    second_image_url = second_image["url"].replace("\\", "/")
                    additional_images_html = (
                        f'<div class="featured-image">'
                        f'<img src="{second_image_url}" alt="{second_image["caption"]}">'
                        f'<figcaption>{second_image["caption"]}</figcaption>'
                        f'</div>'
                    )
                    soup_summary = BeautifulSoup(clean_summary, 'html.parser')
                    interesting_facts = soup_summary.find(lambda tag: tag.name in ['strong', 'h3', 'h4'] and 'Interesting Facts:' in tag.get_text())
                    if interesting_facts:
                        interesting_facts.insert_before(BeautifulSoup(additional_images_html, 'html.parser'))
                        clean_summary = str(soup_summary)
        
        # Process any images in the summary, downloading them and updating src attributes
        if clean_summary and "<img" in clean_summary:
            clean_summary = process_images_in_html(clean_summary, article_id)
        
        # Create filename and filepath
        filename = create_filename_from_title(gemini_title, url, article_id)
        filepath = os.path.join(OUTPUT_HTML_DIR, filename)
        logger.debug(f"Preparing to save HTML to: {filepath}")
        
        # Determine the correct relative path for static assets
        relative_static_path = "../../static"  # Two levels up from articles directory
        
        # Create processed date and current year for footer
        processed_date = datetime.now().strftime("%B %d, %Y %H:%M")
        current_year = datetime.now().year
        
        # Prepare featured image and fetched images context
        if 'images' in locals() and images:
            featured_image_data = {
                "url": images[0]["url"].replace("\\", "/"),
                "alt": images[0].get("caption", "Featured image"),
                "caption": images[0].get("caption", "")
            }
            fetched_images_data = []
            if len(images) > 1:
                for img in images[1:]:
                    fetched_images_data.append({
                        "url": img["url"].replace("\\", "/"),
                        "alt": img.get("caption", "Article image"),
                        "caption": img.get("caption", "")
                    })
        else:
            featured_image_data = None
            fetched_images_data = []
        
        # Prepare context data for the Jinja template
        context = {
            "title": gemini_title or f"Article {article_id}",
            "article_id": article_id,
            "url": url,
            "processed_date": processed_date,
            "featured_image": featured_image_data,
            "summary": clean_summary if clean_summary else "<div>No summary available</div>",
            "fetched_images": fetched_images_data,
            "show_api_response": False,  # Change to True to display raw API response
            "response_text": response_text,
            "content": content,  # Original article content
            "relative_static_path": relative_static_path,
            "current_year": current_year,
        }
        
        # Load the article template from the Jinja2 environment
        template = jinja_env.get_template('article.html')
        
        # Render the final HTML using the template and the provided context
        html_content = template.render(context)
        
        # Write the rendered HTML to the output file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
            f.flush()
        
        if os.path.exists(filepath):
            logger.info(f"HTML file created successfully: {filepath} (Size: {os.path.getsize(filepath)} bytes)")
        else:
            logger.error(f"Failed to create HTML file: {filepath}")
        
        if featured_image_html:
            if featured_image_url in html_content:
                logger.debug(f"Confirmed featured image path '{featured_image_url}' is correctly embedded in HTML.")
            else:
                logger.error(f"Featured image path '{featured_image_url}' is missing in generated HTML.")
        
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
