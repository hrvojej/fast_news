# summarizer_core.py
"""
Core functionality for the article summarization system.
This module contains the main class and orchestration logic.
"""

import os
import sys
import time
import random
import uuid
from datetime import datetime, timezone

# Add package root to path
# Import path configuration first
from summarizer_path_config import configure_paths
configure_paths()

# Import our modules
from summarizer_logging import get_logger
from summarizer_prompt import create_prompt
from summarizer_api import call_gemini_api
from summarizer_html import clean_and_normalize_html, save_as_html
from summarizer_db import get_articles, update_article_summary
from summarizer_config import OUTPUT_HTML_DIR, ensure_output_directory
from summarizer_image import ensure_images_directory

# Import database models and context
from db_scripts.db_context import DatabaseContext

logger = get_logger(__name__)

def rate_limit_sleep():
    """Sleep for a random duration to respect API rate limits."""
    sleep_time = random.uniform(15.0, 17.0)
    logger.info(f"Sleeping for {sleep_time:.2f} seconds to respect rate limits.")
    time.sleep(sleep_time)

class ArticleSummarizer:
    """Main class for article summarization workflow."""
    
    def __init__(self, schema, article_model, env='dev', debug_mode=False):
        """
        Initialize the article summarizer.
        
        Args:
            schema (str): The database schema to use
            article_model: SQLAlchemy model for articles
            env (str): Environment to run in ('dev', 'stage', 'prod')
            debug_mode (bool): Whether to run in debug mode
        """
        self.schema = schema
        self.env = env
        self.debug_mode = debug_mode
        self.article_model = article_model
        self.db_context = DatabaseContext.get_instance(env)
        self.processed_count = 0
        self.failed_count = 0
        ensure_output_directory()
        ensure_images_directory()  # Add this line

        
        logger.info(f"Initialized ArticleSummarizer for {schema} (env={env}, debug_mode={debug_mode})")
    
    def summarize_article(self, article_info):
        try:
            # Extract article information
            content = article_info.get('content', '')
            article_id = article_info.get('article_id')
            title = article_info.get('title', '')
            url = article_info.get('url', '')
            
            # Validate input
            if not content or not isinstance(content, str):
                content_length = len(content) if content else 0
                logger.error(
                    f"Invalid content for article ID: {article_id}. "
                    f"Type: {type(content)}, Length: {content_length}. "
                    f"Content snippet: {content[:200] if isinstance(content, str) else 'N/A'}"
                )
                return False
            else:
                # Also log a debug snippet if in debug mode
                logger.debug(f"Article ID {article_id} content length: {len(content)}. Preview: {content[:200]}")
            
            # Ensure we strip whitespace after validating type
            content = content.strip()
            
            logger.info(f"=== START ARTICLE ID: {article_id} ===")
            logger.info(f"ARTICLE CONTENT LENGTH: {len(content)} characters")
            logger.debug(f"ARTICLE CONTENT PREVIEW:\n{content[:500]}...")
            
            # Create prompt
            try:
                from summarizer_config import CONFIG, get_config_value
                include_featured_image = get_config_value(CONFIG, 'summarization', 'enable_featured_image_search', True)
                prompt = create_prompt(content, len(content), include_images=include_featured_image, enable_entity_links=True)

                if prompt is None:
                    logger.error(f"Failed to create prompt for article ID {article_id}: prompt is None")
                    return False
                logger.debug(f"PROMPT PREVIEW:\n{prompt[:1000]}...")
            except Exception as e:
                logger.error(f"Error creating prompt for article ID {article_id}: {e}")
                return False
            
            # Get summary
            if self.debug_mode:
                logger.info("DEBUG MODE: Using demo response instead of API call")
                summary_text = """<div><h1>Demo Summary</h1><p>This is a demo summary.</p></div>"""
                raw_response_text = "DEBUG MODE: Demo response used instead of actual API call"
            else:
                summary_text, raw_response_text = call_gemini_api(prompt, article_id, len(content))
                if not summary_text:
                    logger.error(f"Failed to generate summary for article ID: {article_id}")
                    return False
            
            # Process and update database
            cleaned_summary = clean_and_normalize_html(summary_text)
            if not self.debug_mode:
                success = update_article_summary(
                    self.db_context, 
                    self.schema, 
                    article_id, 
                    cleaned_summary
                )
                if not success:
                    logger.error(f"Failed to update database for article ID: {article_id}")
                    return False
            
            # Save as HTML, now passing keywords from the database to enable image search
            # Save as HTML, now passing the schema along with keywords
            html_saved = save_as_html(
                article_id, title, url, content, summary_text, raw_response_text, self.schema,
                keywords=article_info.get('keywords'),
                existing_gemini_title=article_info.get('summary_article_gemini_title')
            )

            if not html_saved:
                logger.error(f"Failed to save HTML output for article ID: {article_id}")
                return False
            
            logger.info(f"ARTICLE SUMMARY for ID {article_id} (first 500 chars):\n{summary_text[:500]}...")
            logger.info(f"=== END ARTICLE ID: {article_id} ===")
            return True
        except Exception as e:
            logger.error(f"Unhandled exception in summarize_article for ID {article_id}: {e}", exc_info=True)
            return False


    def run(self, limit=None):
            """
            Run the summarization process for multiple articles.

            Args:
                limit (int, optional): Maximum number of articles to process
            """
            logger.info(f"Starting Article Summarizer for {self.schema} schema (debug_mode={self.debug_mode})")
            try:
                # Get articles (without filtering on summary, ordering by pub_date DESC)
                articles = get_articles(self.db_context, self.schema, limit)
                article_count = len(articles)
                logger.info(f"Found {article_count} articles to process")

                # Report number of articles with empty HTML file location
                missing_html_count = len([a for a in articles if not a._mapping.get('article_html_file_location')])
                logger.info(f"{missing_html_count} articles have an empty article_html_file_location and need to be generated")

                # Process each article
                for idx, article in enumerate(articles):
                    article_info = dict(article._mapping)
                    article_id = article_info.get('article_id')
                    
                    # Log all article details (pub_date, title, article_id, HTML file location)
                    logger.info(
                        f"Article details - ID: {article_id}, "
                        f"Title: {article_info.get('title')}, "
                        f"Pub Date: {article_info.get('pub_date')}, "
                        f"HTML File: {article_info.get('article_html_file_location')}"
                    )
                    
                    # Check if an HTML file is already defined and exists on disk
                    html_file_location = article_info.get('article_html_file_location')
                    if html_file_location:
                        from os import path
                        full_path = path.join(OUTPUT_HTML_DIR, html_file_location)
                        if path.exists(full_path):
                            logger.info(f"Skipping article {article_id} as HTML file exists at {full_path}")
                            continue  # Skip this article since the file exists
                    else:
                        logger.info(f"No HTML file location defined for article {article_id}; processing article.")
                    
                    logger.info(f"[{idx+1}/{article_count}] Processing article ID: {article_id}")

                    
                    
                    try:
                        success = self.summarize_article(article_info)
                        if success:
                            self.processed_count += 1
                            logger.info(f"Successfully processed article {idx+1}/{article_count}")
                        else:
                            self.failed_count += 1
                            logger.error(f"Failed to process article {idx+1}/{article_count}")
                    except Exception as e:
                        self.failed_count += 1
                        logger.error(f"Exception processing article ID {article_id}: {e}", exc_info=True)
                        continue

                logger.info(f"Summarization completed. Processed: {self.processed_count}, Failed: {self.failed_count}")

            except Exception as e:
                logger.error(f"Error in run method: {e}", exc_info=True)
                raise