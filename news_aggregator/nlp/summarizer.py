import sys
import os
import argparse
import time
import random
import re
import traceback
from datetime import datetime, timezone
import html
import json
from bs4 import BeautifulSoup  # Added for HTML validation and cleaning
from sqlalchemy import text
from summarizer_prompt import create_prompt  # Import the create_prompt function from summarizer_prompt.py

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Set up shared logging with increased verbosity
from portals.modules.logging_config import setup_script_logging
logger = setup_script_logging(__file__, log_level='DEBUG')  # Increase to DEBUG level

# Import database models and context
from db_scripts.models.models import create_portal_article_model, create_portal_category_model
from db_scripts.db_context import DatabaseContext

# Import Gemini API client from the new SDK
from google import genai
from google.genai import types

API_KEY = "AIzaSyAQClE8j_yigCu8DU_1S130KX_f5denga8"
client = genai.Client(api_key=API_KEY)

NYTCategory = create_portal_category_model("pt_nyt")
NYTArticle = create_portal_article_model("pt_nyt")

# Define the output HTML directory
OUTPUT_HTML_DIR = os.path.join(current_dir, "data", "output_html")

def is_valid_html(text):
    """Improved HTML validation using BeautifulSoup"""
    if not text or not isinstance(text, str):
        return False
    try:
        soup = BeautifulSoup(text, 'html.parser')
        return bool(soup.find())
    except Exception:
        return False

def clean_and_normalize_html(text):
    """Clean and normalize HTML content to ensure it's valid"""
    if not text or not isinstance(text, str):
        return "<div>No content available</div>"
    
    if "```html" in text:
        try:
            text = text.split('```html')[1].split('```')[0].strip()
        except Exception as e:
            logger.warning(f"Error extracting HTML from code block: {e}")
    
    text = re.sub(r'^#\s+', '', text, flags=re.MULTILINE)
    
    try:
        soup = BeautifulSoup(text, 'html.parser')
        cleaned_html = str(soup)
        if not soup.find() or cleaned_html.strip() == "":
            return f"<div>{html.escape(text)}</div>"
        return cleaned_html
    except Exception as e:
        logger.warning(f"Error cleaning HTML: {e}")
        return f"<div>{html.escape(text)}</div>"

def ensure_output_directory():
    """Ensure the output directory exists and is writable"""
    if not os.path.exists(OUTPUT_HTML_DIR):
        try:
            os.makedirs(OUTPUT_HTML_DIR)
            logger.info(f"Created output directory: {OUTPUT_HTML_DIR}")
            test_file = os.path.join(OUTPUT_HTML_DIR, "test_write.txt")
            with open(test_file, 'w') as f:
                f.write("Test")
            os.remove(test_file)
            logger.info(f"Output directory is writable: {OUTPUT_HTML_DIR}")
        except Exception as e:
            logger.error(f"Failed to create or write to output directory: {e}")
            raise
    else:
        logger.info(f"Output directory already exists: {OUTPUT_HTML_DIR}")
        try:
            test_file = os.path.join(OUTPUT_HTML_DIR, "test_write.txt")
            with open(test_file, 'w') as f:
                f.write("Test")
            os.remove(test_file)
            logger.info(f"Output directory is writable: {OUTPUT_HTML_DIR}")
        except Exception as e:
            logger.error(f"Cannot write to output directory: {e}")
            raise

def rate_limit_sleep():
    sleep_time = random.uniform(6.0, 9.0)
    print(f"Sleeping for {sleep_time:.2f} seconds to respect rate limits.")
    time.sleep(sleep_time)

def create_filename_from_title(title, url, article_id):
    if not title or title.strip() == '':
        if url:
            url_parts = url.strip('/').split('/')
            return f"{url_parts[-1][:50]}.html"
        else:
            return f"article_{article_id}.html"
    
    filename = re.sub(r'[^\w\s-]', '', title)
    filename = re.sub(r'\s+', '_', filename)
    filename = filename[:50]
    return f"{filename}.html"

def save_as_html(article_id, title, url, content, summary, response_text):
    try:
        processed_summary = clean_and_normalize_html(summary)
        logger.debug(f"Processed summary (first 100 chars): {processed_summary[:100]}...")
        filename = create_filename_from_title(title, url, article_id)
        filepath = os.path.join(OUTPUT_HTML_DIR, filename)
        logger.debug(f"Preparing to save HTML to: {filepath}")
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title or f'NYT Article {article_id}')}</title>
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
    <h1>{html.escape(title or f'NYT Article {article_id}')}</h1>
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
        <p>Generated by NYT Article Summarizer using Gemini API</p>
    </div>
</body>
</html>"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
            f.flush()
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            logger.info(f"Successfully saved HTML output to {filepath} (size: {file_size} bytes)")
            return True
        else:
            logger.error(f"File wasn't created despite no errors: {filepath}")
            return False
    except Exception as e:
        logger.error(f"Error saving HTML file {filepath if 'filepath' in locals() else 'unknown'}:")
        logger.error(traceback.format_exc())
        return False

class NYTArticleSummarizer:
    def __init__(self, env='dev', debug_mode=False):
        self.env = env
        self.debug_mode = debug_mode
        self.logger = logger
        self.db_context = DatabaseContext.get_instance(env)
        self.NYTArticle = NYTArticle
        self.processed_count = 0
        self.failed_count = 0
        ensure_output_directory()

    def summarize_article(self, article_info):
        content = article_info.get('content', '').strip()
        article_id = article_info.get('article_id')
        title = article_info.get('title', '')
        url = article_info.get('url', '')
        
        if not content:
            self.logger.info("No content to summarize for article ID: %s.", article_id)
            return False
        
        self.logger.info("=== START ARTICLE ID: %s ===", article_id)
        self.logger.info(f"ARTICLE CONTENT LENGTH: {len(content)} characters")
        self.logger.debug(f"ARTICLE CONTENT PREVIEW:\n{content[:500]}...")
        
        prompt = create_prompt(content, len(content))
        self.logger.debug(f"PROMPT PREVIEW:\n{prompt[:1000]}...")
        
        if self.debug_mode:
            self.logger.info("DEBUG MODE: Using demo response instead of API call")
            summary_text = """<div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
    <!-- Demo summary content -->
    </div>"""
            raw_response_text = "DEBUG MODE: Demo response used instead of actual API call"
        else:
            try:
                self.logger.info("Calling Gemini API for article ID: %s", article_id)
                model = 'gemini-2.0-flash'
                if len(content) > 15000:
                    model = 'gemini-2.0-pro'
                
                config_kwargs = {
                    "max_output_tokens": 8192 if len(content) > 10000 else 5120,
                    "temperature": 0.7,
                    "top_p": 0.9,
                }
                if hasattr(types, 'HarmCategory') and hasattr(types, 'HarmBlockThreshold'):
                    if len(content) > 10000:
                        config_kwargs["safety_settings"] = [
                            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                                                threshold=types.HarmBlockThreshold.BLOCK_NONE),
                            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                                                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH),
                            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                                                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
                            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                                                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
                        ]
                config = types.GenerateContentConfig(**config_kwargs)
                
                response = client.models.generate_content(
                    model=model,
                    contents=[{"role": "user", "parts": [{"text": prompt}]}],
                    config=config
                )
                
            except Exception as api_error:
                self.logger.error(f"API call failed for article ID {article_id}: {api_error}")
                self.logger.error(traceback.format_exc())
                return False

            summary_text = response.text.strip() if response and hasattr(response, 'text') else None
            raw_response_text = str(response)
        
        if not summary_text:
            self.logger.error("Failed to generate summary for article ID: %s.", article_id)
            return False

        if not self.debug_mode:
            with self.db_context.session() as session:
                try:
                    if isinstance(article_id, str):
                        from uuid import UUID
                        article_id = UUID(article_id)
                    
                    article_obj = session.query(self.NYTArticle).filter(
                        self.NYTArticle.article_id == article_id
                    ).first()
                    
                    if article_obj:
                        cleaned_summary = clean_and_normalize_html(summary_text)
                        article_obj.summary = cleaned_summary
                        article_obj.nlp_updated_at = datetime.now(timezone.utc)
                        if not title and hasattr(article_obj, 'title'):
                            title = article_obj.title
                        if not url and hasattr(article_obj, 'url'):
                            url = article_obj.url
                        session.commit()
                        self.logger.info("Article ID %s summary updated in the database.", article_id)
                    else:
                        self.logger.error("Article ID %s not found in the database.", article_id)
                        return False
                        
                except Exception as db_error:
                    session.rollback()
                    self.logger.error("Database error updating article ID %s: %s", article_id, db_error)
                    self.logger.error(traceback.format_exc())
                    return False

        html_saved = save_as_html(article_id, title, url, content, summary_text, raw_response_text)
        if not html_saved:
            self.logger.error(f"Failed to save HTML output for article ID: {article_id}")
            return False

        self.logger.info("ARTICLE SUMMARY for ID %s (first 500 chars):\n%s", article_id, 
                         summary_text[:500] + "..." if len(summary_text) > 500 else summary_text)
        self.logger.info("=== END ARTICLE ID: %s ===", article_id)
        return True

    def run(self, limit=None):
        self.logger.info("Starting NYT Article Summarizer for pt_nyt schema (debug_mode=%s).", self.debug_mode)
        try:
            with self.db_context.session() as session:
                query = "SELECT article_id, title, url, content FROM pt_nyt.articles"
                if limit:
                    query += f" LIMIT {limit}"
                articles = session.execute(text(query)).fetchall()

            self.logger.info("Found %d articles to process.", len(articles))

            for idx, article in enumerate(articles):
                article_info = dict(article._mapping)
                article_id = article_info.get('article_id')
                self.logger.info("[%d/%d] Processing article ID: %s.", idx+1, len(articles), article_id)
                try:
                    success = self.summarize_article(article_info)
                    if success:
                        self.processed_count += 1
                        self.logger.info(f"Successfully processed article {idx+1}/{len(articles)}")
                    else:
                        self.failed_count += 1
                        self.logger.error(f"Failed to process article {idx+1}/{len(articles)}")
                    
                    if not self.debug_mode:
                        rate_limit_sleep()
                    
                except Exception as e:
                    self.failed_count += 1
                    self.logger.error(f"Exception processing article ID {article_id}: {e}")
                    self.logger.error(traceback.format_exc())
                    continue
            
        except Exception as e:
            self.logger.error(f"Error in run method: {e}")
            self.logger.error(traceback.format_exc())
            raise

        self.logger.info("Summarization completed. Processed: %d, Failed: %d", self.processed_count, self.failed_count)

def main():
    parser = argparse.ArgumentParser(description='NYT Article Summarizer')
    parser.add_argument(
        '--env',
        type=str,
        default='dev',
        choices=['dev', 'stage', 'prod'],
        help="Environment to run in (dev, stage, prod)"
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help="Run in debug mode (uses sample response instead of API call)"
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help="Limit the number of articles to process"
    )
    args = parser.parse_args()
    
    try:
        summarizer = NYTArticleSummarizer(env=args.env, debug_mode=args.debug)
        summarizer.run(limit=args.limit)
        logger.info("Article summarization completed successfully.")
    except Exception as e:
        logger.error("Script execution failed: %s", e)
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()
