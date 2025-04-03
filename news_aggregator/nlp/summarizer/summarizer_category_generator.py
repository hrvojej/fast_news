r"""
Module for generating a minimal category page.
This script loads the category template, renders it with data from the database,
and writes the output to:
C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend\web\categories\category_test.html
"""

import os
import sys
import logging
import json
from jinja2 import Environment, FileSystemLoader, select_autoescape

from summarizer_category_utilities import ensure_category_images_folder, crop_and_resize_image

# Define dimensions for images
TOP_LEVEL_WIDTH = 300
TOP_LEVEL_HEIGHT = 200
SUBCAT_WIDTH = 400
SUBCAT_HEIGHT = 300

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)
    
# Load articles from database
from db_scripts.db_context import DatabaseContext
db_context = DatabaseContext()
query = (
    "SELECT summary_article_gemini_title, "
    "article_html_file_location, "
    "summary_featured_image, "
    "popularity_score "
    "FROM pt_nyt.articles "
    "WHERE article_html_file_location <> ''"
)
articles_data = db_context.fetch_all(query)
articles_data = [article for article in articles_data if article.get("article_html_file_location")]

# Convert summary_featured_image from string to dict if needed.
for article in articles_data:
    sfi = article.get("summary_featured_image")
    if sfi and isinstance(sfi, str):
        sfi_strip = sfi.strip()
        if sfi_strip.startswith("{"):
            try:
                article["summary_featured_image"] = json.loads(sfi_strip)
            except Exception as e:
                logging.error(f"Error parsing summary_featured_image JSON: {e}")
                article["summary_featured_image"] = {"url": sfi_strip, "alt": "", "caption": ""}
        else:
            article["summary_featured_image"] = {"url": sfi_strip, "alt": "", "caption": ""}

# Initialize logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define directories
STATIC_IMAGE_DIR = os.path.join(package_root, "frontend", "web", "static", "images")
CATEGORY_IMAGES_DIR = os.path.join(package_root, "frontend", "web", "categories", "images")
BASE_DIR = os.path.join(package_root, "frontend")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
OUTPUT_CATEGORY_DIR = os.path.join(BASE_DIR, "web", "categories")
if not os.path.exists(OUTPUT_CATEGORY_DIR):
    os.makedirs(OUTPUT_CATEGORY_DIR)
    logger.debug(f"Created output directory: {OUTPUT_CATEGORY_DIR}")

# Setup Jinja2 environment
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)

def extract_category_info(article_html_file_location):
    parts = article_html_file_location.split('/')
    if not parts or parts[0] == '':
        return {'category': None, 'subcategory': None}
    category = parts[0]
    subcategory = parts[1] if len(parts) > 1 and parts[1] else None
    return {'category': category, 'subcategory': subcategory}

# Extract category info for each article
for article in articles_data:
    cat_info = extract_category_info(article["article_html_file_location"])
    article["extracted_category"] = cat_info.get("category")
    article["extracted_subcategory"] = cat_info.get("subcategory")
    
# Group articles by top-level category
categories_group = {}
for article in articles_data:
    top_category = article.get("extracted_category") or "Uncategorized"
    categories_group.setdefault(top_category, []).append(article)

# Sort articles by popularity descending
articles_data = sorted(articles_data, key=lambda x: x.get("popularity_score", 0), reverse=True)

# Preserve original image URL
for article in articles_data:
    if article.get("summary_featured_image") and article["summary_featured_image"].get("url"):
        if "original_url" not in article["summary_featured_image"]:
            article["summary_featured_image"]["original_url"] = article["summary_featured_image"]["url"]

# Process images for each article; store processed filenames as plain strings.
for article in articles_data:
    if article.get("summary_featured_image") and article["summary_featured_image"].get("url"):
        original_url = article["summary_featured_image"]["url"]
        base, ext = os.path.splitext(original_url)
        expected_large = f"{base}_{TOP_LEVEL_WIDTH}x{TOP_LEVEL_HEIGHT}{ext}"
        expected_small = f"{base}_{SUBCAT_WIDTH}x{SUBCAT_HEIGHT}{ext}"
        
        # Process top-level image (300x200)
        processed_large_path = os.path.join(CATEGORY_IMAGES_DIR, expected_large)
        if not os.path.exists(processed_large_path):
            input_image = os.path.join(STATIC_IMAGE_DIR, original_url)
            success = crop_and_resize_image(input_image, os.path.join(CATEGORY_IMAGES_DIR, original_url),
                                            target_width=TOP_LEVEL_WIDTH, target_height=TOP_LEVEL_HEIGHT)
            if success:
                article["summary_featured_image_large"] = expected_large
            else:
                logger.error(f"Failed to process top-level image for article: {article['summary_article_gemini_title']}")
                article["summary_featured_image_large"] = original_url  # fallback
        else:
            article["summary_featured_image_large"] = expected_large
        
        # Process subcategory image (400x300)
        processed_small_path = os.path.join(CATEGORY_IMAGES_DIR, expected_small)
        if not os.path.exists(processed_small_path):
            input_image = os.path.join(STATIC_IMAGE_DIR, original_url)
            success = crop_and_resize_image(input_image, os.path.join(CATEGORY_IMAGES_DIR, original_url),
                                            target_width=SUBCAT_WIDTH, target_height=SUBCAT_HEIGHT)
            if success:
                article["summary_featured_image_small"] = expected_small
            else:
                logger.error(f"Failed to process subcategory image for article: {article['summary_article_gemini_title']}")
                article["summary_featured_image_small"] = original_url  # fallback
        else:
            article["summary_featured_image_small"] = expected_small

# --- Set slicing counts for grid items (16 items for a 4x4 grid)
MAIN_GRID_COUNT = 16
SUBCAT_GRID_COUNT = 16

# Process per-category pages
for top_category, articles in categories_group.items():
    # Sort articles by popularity descending
    articles = sorted(articles, key=lambda x: x.get("popularity_score", 0), reverse=True)
    
    # Build main grid: use top MAIN_GRID_COUNT articles (if available)
    featured_articles = articles[:MAIN_GRID_COUNT]
    
    # Build additional main articles: remaining articles (excluding those in the main grid)
    main_grid_ids = {id(a) for a in featured_articles}
    additional_articles = [a for a in articles if id(a) not in main_grid_ids]
    
    # Group remaining articles (not in main grid) into subcategories
    subcat_articles = [a for a in articles if id(a) not in main_grid_ids]
    # Only group if at least one article has a non-null extracted_subcategory different from the top category
    real_subcats = [a.get("extracted_subcategory") for a in subcat_articles if a.get("extracted_subcategory") and a.get("extracted_subcategory") != top_category]
    if not real_subcats:
        subcategories = {}
    else:
        subcategories = {}
        for article in subcat_articles:
            subcat = article.get("extracted_subcategory")
            if subcat and subcat != top_category:
                subcategories.setdefault(subcat, []).append(article)
        # For each subcategory, build grid and additional list
        for key in subcategories:
            sorted_sub = sorted(subcategories[key], key=lambda x: x.get("popularity_score", 0), reverse=True)
            featured_sub = sorted_sub[:SUBCAT_GRID_COUNT]
            others_sub = sorted_sub[SUBCAT_GRID_COUNT:]
            subcategories[key] = {"featured": featured_sub, "others": others_sub}
    
    context = {
        "category": {"name": top_category},
        "featured_articles": featured_articles,
        "additional_articles": additional_articles,
        "subcategories": subcategories,
        "relative_static_path": "../static",
        "relative_articles_path": "../articles/",
        "relative_category_images_path": "images"
    }
    
    try:
        template = jinja_env.get_template("category.html")
        rendered_html = template.render(context)
        logger.debug(f"Successfully rendered the category template for {top_category}.")
    except Exception as e:
        logger.error(f"Error rendering template for {top_category}: {e}")
        continue
    
    output_filename = f"category_{top_category.lower().replace(' ', '_')}.html"
    output_file_path = os.path.join(OUTPUT_CATEGORY_DIR, output_filename)
    try:
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)
        logger.debug(f"Category page for {top_category} generated at: {output_file_path}")
    except Exception as e:
        logger.error(f"Error writing category page for {top_category} to file: {e}")
        sys.exit(1)
