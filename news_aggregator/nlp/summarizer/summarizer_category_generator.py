"""
Module for generating category pages, the homepage, the about page, the dynamic header file,
and subcategory pages.
This script loads templates, renders them with data from the database, and writes the output to:
  - Category pages: frontend/web/categories/category_*.html
  - Homepage: frontend/web/homepage.html
  - About page: frontend/web/about.html
  - Header file: frontend/web/header.html  <-- New dynamic header file
  - Subcategory pages: frontend/web/categories/subcategory_*.html  <-- New subcategory pages
"""

import os
import re
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
    "popularity_score, "
    "pub_date "
    "FROM pt_nyt.articles "
    "WHERE article_html_file_location <> ''"
)
articles_data = db_context.fetch_all(query)
articles_data = [article for article in articles_data if article.get("article_html_file_location")]

# Initialize logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define BASE_DIR (points to the frontend folder)
BASE_DIR = os.path.join(package_root, "frontend")

# Convert absolute Windows paths to relative paths for articles
ARTICLES_BASE_PATH = os.path.join(BASE_DIR, "web", "articles")
for article in articles_data:
    location = article["article_html_file_location"]
    if re.match(r'^[A-Za-z]:[\\/]', location) or os.path.isabs(location):
        relative_location = os.path.relpath(location, ARTICLES_BASE_PATH)
        article["article_html_file_location"] = relative_location.replace("\\", "/")

# Check physical existence of article HTML files and filter out missing ones
valid_articles = []
for article in articles_data:
    file_full_path = os.path.join(ARTICLES_BASE_PATH, article["article_html_file_location"])
    if os.path.exists(file_full_path):
        valid_articles.append(article)
    else:
        logger.warning(f"HTML file not found for article: {article['summary_article_gemini_title']} at {file_full_path}")
articles_data = valid_articles

# Convert summary_featured_image from string to dict if needed.
for article in articles_data:
    sfi = article.get("summary_featured_image")
    if sfi and isinstance(sfi, str):
        sfi_strip = sfi.strip()
        if sfi_strip.startswith("{"):
            try:
                article["summary_featured_image"] = json.loads(sfi_strip)
            except Exception as e:
                logger.error(f"Error parsing summary_featured_image JSON: {e}")
                article["summary_featured_image"] = {"url": sfi_strip, "alt": "", "caption": ""}
        else:
            article["summary_featured_image"] = {"url": sfi_strip, "alt": "", "caption": ""}

# Define directories for static files, templates, and output pages
STATIC_IMAGE_DIR = os.path.join(BASE_DIR, "web", "static", "images")
CATEGORY_IMAGES_DIR = os.path.join(BASE_DIR, "web", "categories", "images")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
OUTPUT_CATEGORY_DIR = os.path.join(BASE_DIR, "web", "categories")
# Ensure the categories/images folder exists.
if not os.path.exists(CATEGORY_IMAGES_DIR):
    os.makedirs(CATEGORY_IMAGES_DIR)
    logger.debug(f"Created categories images directory: {CATEGORY_IMAGES_DIR}")
if not os.path.exists(OUTPUT_CATEGORY_DIR):
    os.makedirs(OUTPUT_CATEGORY_DIR)
    logger.debug(f"Created output directory: {OUTPUT_CATEGORY_DIR}")

# --- Generate header categories ---
# Read category page files from frontend/web/categories and build header_categories.
categories_folder = os.path.join(BASE_DIR, "web", "categories")
category_files = [f for f in os.listdir(categories_folder) if f.startswith("category_") and f.endswith(".html")]
header_categories = []
for file in category_files:
    slug = file.replace("category_", "").replace(".html", "")
    if slug.lower() == "espanol":
        continue
    display_name = "NY" if slug.lower() == "nyregion" else slug.title()
    # Use an absolute URL for category pages.
    link = f"/categories/category_{slug}.html"
    header_categories.append({"slug": slug, "name": display_name, "link": link})

# --- Prepare initial context for non-header templates (if needed) ---
cat_context = {
    "relative_static_path": "../static",
    "relative_articles_path": "../articles/",
    "relative_category_images_path": "images",
    "relative_root_path": "..",
    "relative_categories_path": ".",
    "header_categories": header_categories
}

# --- Setup Jinja2 environment ---
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)

# --- Extract Category Info from Articles ---
def extract_category_info(article_html_file_location):
    if "/" not in article_html_file_location:
        return {'category': "Uncategorized", 'subcategory': None}
    parts = article_html_file_location.split('/')
    category = parts[0] if parts[0] else "Uncategorized"
    subcategory = parts[1] if len(parts) > 1 and parts[1] and not parts[1].endswith(".html") else None
    return {'category': category, 'subcategory': subcategory}

for article in articles_data:
    cat_info = extract_category_info(article["article_html_file_location"])
    article["extracted_category"] = cat_info.get("category")
    article["extracted_subcategory"] = cat_info.get("subcategory")

# Normalize extracted categories to lowercase
for article in articles_data:
    if article.get("extracted_category"):
        article["extracted_category"] = article["extracted_category"].lower()
    if article.get("extracted_subcategory"):
        article["extracted_subcategory"] = article["extracted_subcategory"].lower()

# --- Group Articles by Top-Level Category ---
categories_group = {}
for article in articles_data:
    top_category = article.get("extracted_category") or "Uncategorized"
    categories_group.setdefault(top_category, []).append(article)

# --- Generate Global subcategories_by_category for header ---
subcategories_by_category = {}
for header_cat in header_categories:
    cat_slug = header_cat["slug"].lower()
    subcats = set()
    if cat_slug in categories_group:
        for article in categories_group[cat_slug]:
            subcat = article.get("extracted_subcategory")
            if subcat and subcat != cat_slug:
                subcats.add(subcat)
    subcat_list = []
    for subcat in sorted(subcats):
        # Use an absolute URL for subcategory pages under /categories.
        subcat_obj = {
            "slug": subcat,
            "name": subcat.title(),
            "link": f"/categories/subcategory_{subcat}.html"
        }
        subcat_list.append(subcat_obj)
    subcategories_by_category[cat_slug] = subcat_list

# Update our global header context within cat_context for other pages.
cat_context["subcategories_by_category"] = subcategories_by_category

# --- Define header context for dynamic header file (using absolute paths) ---
header_context = {
    "relative_static_path": "/static",
    "relative_articles_path": "/articles/",
    "relative_category_images_path": "/categories/images",
    "relative_root_path": "/",           # Ensures that paths like homepage.html become /homepage.html
    "relative_categories_path": "/categories",
    "header_categories": header_categories,
    "subcategories_by_category": subcategories_by_category
}

# --- Sort Articles by Publication Date and Popularity ---
articles_data = sorted(
    articles_data,
    key=lambda x: (x.get("pub_date"), x.get("popularity_score", 0)),
    reverse=True
)

# --- Preserve & Process Images ---
for article in articles_data:
    if article.get("summary_featured_image") and article["summary_featured_image"].get("url"):
        if "original_url" not in article["summary_featured_image"]:
            article["summary_featured_image"]["original_url"] = article["summary_featured_image"]["url"]
for article in articles_data:
    if article.get("summary_featured_image") and article["summary_featured_image"].get("url"):
        original_url = article["summary_featured_image"]["url"]
        if original_url == "path/to/default/small_image.jpg":
            article["has_valid_image"] = False
        else:
            article["has_valid_image"] = True
            base, ext = os.path.splitext(original_url)
            expected_large = f"{base}_{TOP_LEVEL_WIDTH}x{TOP_LEVEL_HEIGHT}{ext}"
            expected_small = f"{base}_{SUBCAT_WIDTH}x{SUBCAT_HEIGHT}{ext}"
            processed_large_path = os.path.join(CATEGORY_IMAGES_DIR, expected_large)
            if not os.path.exists(processed_large_path):
                input_image = os.path.join(STATIC_IMAGE_DIR, original_url)
                success = crop_and_resize_image(input_image, os.path.join(CATEGORY_IMAGES_DIR, original_url),
                                                target_width=TOP_LEVEL_WIDTH, target_height=TOP_LEVEL_HEIGHT)
                if success:
                    article["summary_featured_image_large"] = expected_large
                else:
                    logger.error(f"Failed to process top-level image for article: {article['summary_article_gemini_title']}")
                    article["summary_featured_image_large"] = original_url
            else:
                article["summary_featured_image_large"] = expected_large
            processed_small_path = os.path.join(CATEGORY_IMAGES_DIR, expected_small)
            if not os.path.exists(processed_small_path):
                input_image = os.path.join(STATIC_IMAGE_DIR, original_url)
                success = crop_and_resize_image(input_image, os.path.join(CATEGORY_IMAGES_DIR, original_url),
                                                target_width=SUBCAT_WIDTH, target_height=SUBCAT_HEIGHT)
                if success:
                    article["summary_featured_image_small"] = expected_small
                else:
                    logger.error(f"Failed to process subcategory image for article: {article['summary_article_gemini_title']}")
                    article["summary_featured_image_small"] = original_url
            else:
                article["summary_featured_image_small"] = expected_small
    else:
        article["has_valid_image"] = False

# Set slicing counts for grid items
MAIN_GRID_COUNT = 16
SUBCAT_GRID_COUNT = 16

# --- Generate Category Pages ---
for top_category, articles in categories_group.items():
    articles = sorted(
        articles,
        key=lambda x: (x.get("pub_date"), x.get("popularity_score", 0)),
        reverse=True
    )
    featured_articles = [a for a in articles if a.get("has_valid_image", True)]
    featured_articles = featured_articles[:MAIN_GRID_COUNT]
    main_grid_ids = {id(a) for a in featured_articles}
    additional_articles = [a for a in articles if id(a) not in main_grid_ids]
    subcat_articles = [a for a in articles if id(a) not in main_grid_ids]
    real_subcats = [a.get("extracted_subcategory") for a in subcat_articles if a.get("extracted_subcategory") and a.get("extracted_subcategory") != top_category]
    if not real_subcats:
        subcategories = {}
    else:
        subcategories = {}
        for article in subcat_articles:
            subcat = article.get("extracted_subcategory")
            if subcat and subcat != top_category:
                subcategories.setdefault(subcat, []).append(article)
        for key in subcategories:
            sorted_sub = sorted(
                subcategories[key],
                key=lambda x: (x.get("pub_date"), x.get("popularity_score", 0)),
                reverse=True
            )
            featured_sub = [a for a in sorted_sub if a.get("has_valid_image", True)][:SUBCAT_GRID_COUNT]
            others_sub = [a for a in sorted_sub if a not in featured_sub]
            subcategories[key] = {"featured": featured_sub, "others": others_sub}
    
    context = {
        "category": {"name": top_category},
        "featured_articles": featured_articles,
        "additional_articles": additional_articles,
        "subcategories": subcategories,
        "canonical_url": "https://fast-news.net/categories/category_" + top_category.lower().replace(' ', '_') + ".html",
        **cat_context
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

# --- Generate Homepage ---
HOMEPAGE_OUTPUT_FILE = os.path.join(BASE_DIR, "web", "homepage.html")
homepage_context = {
    "homepage_title": "Latest News",
    "canonical_url": "https://fast-news.net/homepage.html",
    "header_categories": header_categories,
    "relative_static_path": "static",
    "relative_articles_path": "articles/",
    "relative_category_images_path": "categories/images",
    "relative_root_path": ".",
    "relative_categories_path": "categories",
    "subcategories_by_category": subcategories_by_category
}


IMPORTANT_CATEGORIES = ["us", "world", "business", "technology", "sports"]
HOMEPAGE_FEATURED_COUNT = 5
homepage_sections = []
for important_cat in IMPORTANT_CATEGORIES:
    for group_key, group_articles in categories_group.items():
        if group_key.lower() == important_cat:
            valid_articles = [a for a in group_articles if a.get("has_valid_image", False)]
            sorted_articles = sorted(
                valid_articles,
                key=lambda x: (x.get("pub_date"), x.get("popularity_score", 0)),
                reverse=True
            )
            homepage_sections.append({
                "category": group_key,
                "featured": sorted_articles[:HOMEPAGE_FEATURED_COUNT]
            })
            break
homepage_context["homepage_sections"] = homepage_sections

try:
    template = jinja_env.get_template("homepage.html")
    rendered_html = template.render(homepage_context)
    logger.debug("Successfully rendered the homepage template.")
except Exception as e:
    logger.error(f"Error rendering homepage template: {e}")
    sys.exit(1)

try:
    with open(HOMEPAGE_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(rendered_html)
    logger.debug(f"Homepage generated at: {HOMEPAGE_OUTPUT_FILE}")
except Exception as e:
    logger.error(f"Error writing homepage to file: {e}")
    sys.exit(1)

# --- Generate About Page ---
ABOUT_OUTPUT_FILE = os.path.join(BASE_DIR, "web", "about.html")
about_context = {
    "canonical_url": "https://fast-news.net/about.html",
    "relative_static_path": "static",
    "relative_articles_path": "articles/",
    "relative_category_images_path": "categories/images",
    "relative_root_path": ".",
    "relative_categories_path": "categories",
    "header_categories": header_categories,
    "subcategories_by_category": subcategories_by_category
}

try:
    template = jinja_env.get_template("about.html")
    rendered_html = template.render(about_context)
    logger.debug("Successfully rendered the about page template.")
except Exception as e:
    logger.error(f"Error rendering about page template: {e}")
    sys.exit(1)

try:
    with open(ABOUT_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(rendered_html)
    logger.debug(f"About page generated at: {ABOUT_OUTPUT_FILE}")
except Exception as e:
    logger.error(f"Error writing about page to file: {e}")
    sys.exit(1)

# --- Generate Subcategory Pages ---
# We'll generate one subcategory page for each distinct subcategory found across all articles.
GLOBAL_SUBCAT_DIR = os.path.join(BASE_DIR, "web", "categories")
try:
    subcat_template = jinja_env.get_template("subcategory.html")
except Exception as e:
    logger.error(f"Subcategory template not found: {e}")
    sys.exit(1)

global_subcategories = {}
for article in articles_data:
    subcat = article.get("extracted_subcategory")
    if subcat:
        global_subcategories.setdefault(subcat, []).append(article)

for subcat, articles in global_subcategories.items():
    articles_sorted = sorted(
        articles,
        key=lambda x: (x.get("pub_date"), x.get("popularity_score", 0)),
        reverse=True
    )
    context = {
        "subcategory": {"name": subcat.title()},
        "articles": articles_sorted,
        "canonical_url": "https://fast-news.net/categories/subcategory_" + subcat + ".html",
        "relative_static_path": "/static",
        "relative_articles_path": "/articles/",
        "relative_category_images_path": "/categories/images",
        "relative_root_path": "/",
        "relative_categories_path": "/categories"
    }


    output_filename = f"subcategory_{subcat}.html"
    output_file_path = os.path.join(GLOBAL_SUBCAT_DIR, output_filename)
    try:
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(subcat_template.render(context))
        logger.debug(f"Subcategory page for {subcat} generated at: {output_file_path}")
    except Exception as e:
        logger.error(f"Error writing subcategory page for {subcat} to file: {e}")
        sys.exit(1)

# --- Generate Dynamic Header File ---
HEADER_OUTPUT_FILE = os.path.join(BASE_DIR, "web", "header.html")
try:
    header_template = jinja_env.get_template("components/header.html")
    rendered_header = header_template.render(header_context)
    with open(HEADER_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(rendered_header)
    logger.debug(f"Header file generated at: {HEADER_OUTPUT_FILE}")
except Exception as e:
    logger.error(f"Error generating header file at {HEADER_OUTPUT_FILE}: {e}")
    sys.exit(1)
    
    
# --- Generate Sitemap XML for Google Search Console ---
# This sitemap.xml includes the homepage, about page, all category pages, subcategory pages, and every article page.
base_url = "https://fast-news.net"
sitemap_urls = set()

# Add homepage and about page URLs
sitemap_urls.add(f"{base_url}/homepage.html")
sitemap_urls.add(f"{base_url}/about.html")

# Add category pages URLs from header_categories
for cat in header_categories:
    # cat["link"] is like "/categories/category_{slug}.html"
    sitemap_urls.add(f"{base_url}{cat['link']}")

# Add subcategory pages URLs from global_subcategories (defined in the subcategory pages generation section)
for subcat in global_subcategories.keys():
    sitemap_urls.add(f"{base_url}/categories/subcategory_{subcat}.html")

# Add article pages URLs from articles_data
for article in articles_data:
    # article_html_file_location was converted to a relative path (e.g., "us/article1.html")
    article_path = article["article_html_file_location"]
    sitemap_urls.add(f"{base_url}/articles/{article_path}")

# Generate XML content
sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
for url in sitemap_urls:
    sitemap_content += "  <url>\n"
    sitemap_content += f"    <loc>{url}</loc>\n"
    sitemap_content += "  </url>\n"
sitemap_content += '</urlset>\n'

# Define output file path for sitemap.xml (placing it in the frontend/web folder)
SITEMAP_OUTPUT_FILE = os.path.join(BASE_DIR, "web", "sitemap.xml")
try:
    with open(SITEMAP_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(sitemap_content)
    logger.debug(f"Sitemap generated successfully at: {SITEMAP_OUTPUT_FILE}")
except Exception as e:
    logger.error(f"Error writing sitemap.xml to file: {e}")
    sys.exit(1)

