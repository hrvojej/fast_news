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
from summarizer_db import claim_article  # ensure you import the new function
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
        from db_scripts.db_context import DatabaseContext
        from summarizer_db import update_article_status_processing
        # Mark the article as being processed so that concurrent processes skip it
        if not update_article_status_processing(DatabaseContext.get_instance(self.env), self.schema, article_info["url"], True):
            self.logger.info(f"Article {article_info['article_id']} is already being processed by another worker. Skipping.")
            return False
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
        logger.info(f"Starting Article Summarizer for {self.schema} schema (debug_mode={self.debug_mode})")
        claimed_articles = []
        try:
            # Claim articles one by one until you reach the limit or no more are available.
            num_to_claim = limit if (limit and isinstance(limit, int) and limit > 0) else 10  # default batch size if no limit provided
            for i in range(num_to_claim):
                article = claim_article(self.db_context, self.schema)
                if article is None:
                    logger.info("No more eligible articles to claim.")
                    break
                claimed_articles.append(article)
            total_claimed = len(claimed_articles)
            logger.info(f"Claimed {total_claimed} articles for processing.")

            # Process each claimed article
            for idx, article in enumerate(claimed_articles):
                article_info = dict(article._mapping)
                article_id = article_info.get('article_id')
                logger.info(f"[{idx+1}/{total_claimed}] Processing article ID: {article_id}")
                try:
                    success = self.summarize_article(article_info)
                    if success:
                        self.processed_count += 1
                        logger.info(f"Successfully processed article {idx+1}/{total_claimed}")
                    else:
                        self.failed_count += 1
                        logger.error(f"Failed to process article {idx+1}/{total_claimed}")
                except Exception as e:
                    self.failed_count += 1
                    logger.error(f"Exception processing article ID {article_id}: {e}", exc_info=True)
                    continue

            logger.info(f"Summarization completed. Processed: {self.processed_count}, Failed: {self.failed_count}")
        except Exception as e:
            logger.error(f"Error in run method: {e}", exc_info=True)
            raise
