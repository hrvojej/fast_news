#!/usr/bin/env python3
"""
NYT Article Summarizer using Gemini API

This script connects to the 'pt_nyt' schema, retrieves articles, and for each article
that has content, calls the Google Gemini API to generate a summary using the prompt:
"Summarize the following text in simple, clear English. Break it down into many short, easy-to-understand sentences and keep every key detail (names, numbers, clauses, etc.) intact."
The summary is stored in the article's "summary" field and logged for analysis.
"""

import sys
import os
import argparse
import time
import random
from datetime import datetime, timezone
from sqlalchemy import text

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Set up shared logging
from portals.modules.logging_config import setup_script_logging
logger = setup_script_logging(__file__)

# Import database models and context
from db_scripts.models.models import create_portal_article_model, create_portal_category_model
from db_scripts.db_context import DatabaseContext

# Import Gemini API client from the new SDK
from google import genai
from google.genai import types

# Configure your API key.
# It is recommended to store your key as an environment variable (e.g. GOOGLE_API_KEY).
# For testing, we are directly assigning it here.
API_KEY = "AIzaSyAQClE8j_yigCu8DU_1S130KX_f5denga8"
client = genai.Client(api_key=API_KEY)

NYTCategory = create_portal_category_model("pt_nyt")
NYTArticle = create_portal_article_model("pt_nyt")

def random_sleep():
    sleep_time = random.uniform(1, 2)
    logger.info("Sleeping for %.2f seconds.", sleep_time)
    time.sleep(sleep_time)
    
def rate_limit_sleep():
    sleep_time = 4.0  # seconds, to ensure no more than 15 requests per minute
    logger.info("Sleeping for %.2f seconds to respect rate limits.", sleep_time)
    time.sleep(sleep_time)


class NYTArticleSummarizer:
    def __init__(self, env='dev'):
        self.env = env
        self.logger = logger
        self.db_context = DatabaseContext.get_instance(env)
        self.NYTArticle = NYTArticle
        self.processed_count = 0
        self.failed_count = 0

    def summarize_article(self, article_info):
        content = article_info.get('content', '').strip()
        article_id = article_info.get('article_id')
        if not content:
            self.logger.info("No content to summarize for article ID: %s.", article_id)
            return False
        
        # Log start marker and article content
        self.logger.info("=== START ARTICLE ID: %s ===", article_id)
        self.logger.info("ARTICLE CONTENT:\n%s", content)

        # Prepare the prompt using the provided instructions
        prompt = (
            "Summarize the following text into a concise, engaging narrative. Combine related facts into fluid sentences "
            "without losing key details such as names, numbers, dates, and events. Avoid unnecessary repetition and overly "
            "fragmented sentences; instead, create a summary that flows naturally while remaining clear and accurate.\n\n"
            f"{content}"
        )
        self.logger.info("GENERATED PROMPT:\n%s", prompt)

        try:
            # Call the Gemini API using the 'gemini-2.0-flash' model for robust text summarization.
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=300,  # adjust as needed for your summaries
                    temperature=0.7,
                    top_p=0.9,
                ),
            )
            # Extract the summary text from the response
            summary_text = response.text.strip() if response and hasattr(response, 'text') else None
            if not summary_text:
                self.logger.error("Failed to generate summary for article ID: %s.", article_id)
                return False

            # Update the article record with the new summary
            with self.db_context.session() as session:
                try:
                    # Use UUID for lookup if article_id is a string
                    if isinstance(article_id, str):
                        from uuid import UUID
                        article_id = UUID(article_id)
                    
                    # Get the article using the ORM
                    article_obj = session.query(self.NYTArticle).filter(
                        self.NYTArticle.article_id == article_id
                    ).first()
                    
                    if article_obj:
                        # Update the summary field
                        article_obj.summary = summary_text
                        # Also update the nlp_updated_at timestamp
                        article_obj.nlp_updated_at = datetime.now(timezone.utc)
                        # Commit the transaction
                        session.commit()
                        self.logger.info("Article ID %s summary updated in the database.", article_id)
                    else:
                        self.logger.error("Article ID %s not found in the database.", article_id)
                        return False
                        
                except Exception as db_error:
                    session.rollback()
                    self.logger.error("Database error updating article ID %s: %s", article_id, db_error)
                    return False

            # Log the summary with clear markers
            self.logger.info("ARTICLE SUMMARY for ID %s:\n%s", article_id, summary_text)
            self.logger.info("=== END ARTICLE ID: %s ===", article_id)
            return True

        except Exception as e:
            self.logger.error("Error summarizing article ID %s: %s", article_id, e)
            return False

    def run(self):
        self.logger.info("Starting NYT Article Summarizer for pt_nyt schema.")
        with self.db_context.session() as session:
            # Retrieve articles from the pt_nyt schema (assumes columns: article_id, content)
            articles = session.execute(text("SELECT article_id, content FROM pt_nyt.articles")).fetchall()

        self.logger.info("Found %d articles to process.", len(articles))

        for article in articles:
            article_info = dict(article._mapping)
            article_id = article_info.get('article_id')
            self.logger.info("Processing article ID: %s.", article_id)
            success = self.summarize_article(article_info)
            if success:
                self.processed_count += 1
            else:
                self.failed_count += 1
            rate_limit_sleep()

        self.logger.info("Summarization completed. Processed: %d, Failed: %d", self.processed_count, self.failed_count)

def main():
    parser = argparse.ArgumentParser(description="NYT Article Summarizer using Gemini API")
    parser.add_argument(
        '--env',
        choices=['dev', 'prod'],
        default='dev',
        help="Specify the environment (default: dev)"
    )
    args = parser.parse_args()
    try:
        summarizer = NYTArticleSummarizer(env=args.env)
        summarizer.run()
        logger.info("Article summarization completed successfully.")
    except Exception as e:
        logger.error("Script execution failed: %s", e)
        raise

if __name__ == "__main__":
    main()
