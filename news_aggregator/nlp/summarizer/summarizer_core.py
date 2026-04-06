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
from summarizer_api import call_llm_api, set_model_config
from summarizer_html import clean_and_normalize_html, save_as_html
from summarizer_db import get_articles, update_article_summary
from summarizer_config import OUTPUT_HTML_DIR, ensure_output_directory
from summarizer_image import ensure_images_directory

# Import database models and context
from db_scripts.db_context import DatabaseContext

logger = get_logger(__name__)


def build_debug_summary(title, content):
    """Build a rich debug HTML summary from the article's actual title and content.
    
    Generates HTML with all CSS classes expected by extract_summary_fields(),
    using real article data to produce realistic pages for pipeline testing.
    """
    import re as _re
    
    # Extract first few sentences for summary paragraphs
    sentences = _re.split(r'(?<=[.!?])\s+', content.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    intro = sentences[0] if len(sentences) > 0 else "This article covers a developing story."
    supporting1 = sentences[1] if len(sentences) > 1 else "Additional details continue to emerge."
    supporting2 = sentences[2] if len(sentences) > 2 else "Experts weigh in on the implications."
    transition = sentences[3] if len(sentences) > 3 else "The situation remains fluid as new information comes to light."
    secondary = sentences[4] if len(sentences) > 4 else "Further analysis is expected in the coming days."

    # Extract keywords from content - find most common capitalized multi-word phrases or single words
    words = _re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
    word_freq = {}
    for w in words:
        if len(w) > 3 and w.lower() not in ('this', 'that', 'with', 'from', 'have', 'been', 'were', 'also', 'said', 'they', 'their', 'would', 'could', 'about', 'more', 'some', 'will', 'when', 'what', 'which'):
            word_freq[w] = word_freq.get(w, 0) + 1
    top_keywords = sorted(word_freq, key=word_freq.get, reverse=True)[:8]
    if not top_keywords:
        top_keywords = ["News", "Update", "Report", "Analysis", "World"]

    keyword_pills = "\n".join(f'       <span class="keyword-pill">{kw}</span>' for kw in top_keywords)

    # Extract potential entity names (capitalized sequences)
    people = []
    orgs = []
    for w in sorted(word_freq, key=word_freq.get, reverse=True):
        if ' ' in w and len(people) < 3:
            people.append(w)
        elif ' ' not in w and len(orgs) < 3:
            orgs.append(w)
        if len(people) >= 3 and len(orgs) >= 3:
            break
    if not people:
        people = ["Key Figure"]
    if not orgs:
        orgs = ["Organization"]

    people_links = ", ".join(
        f'<strong class="named-individual"><a href="https://www.google.com/search?q={p.replace(" ", "+")}" target="_blank">{p}</a></strong>'
        for p in people
    )
    orgs_links = ", ".join(
        f'<strong class="orgs-products"><a href="https://www.google.com/search?q={o.replace(" ", "+")}" target="_blank">{o}</a></strong>'
        for o in orgs
    )

    # Build interesting facts from later sentences
    facts_html = ""
    if len(sentences) > 5:
        fact_items = []
        for i, s in enumerate(sentences[5:10]):
            cls = "fact-primary" if i < 2 else "fact-secondary"
            fact_items.append(f'<li class="{cls}">{s}</li>')
        if fact_items:
            facts_html = f"""
    <div class="facts-container">
      <ul class="facts-list">
        {"".join(fact_items)}
      </ul>
    </div>"""

    # Sentiment analysis for top entity
    sentiment_entity = people[0] if people else "Subject"
    
    summary_html = f"""<div>
  <h1 class="article-title">{title}</h1>
  <div>
    <p class="source-attribution"><span class="label">Source:</span> <span>News Analysis (Debug Mode)</span></p>
  </div>
  <div class="keywords-container">
    <p class="keywords-heading"><strong>Keywords:</strong></p>
    <div class="keywords-tags">
{keyword_pills}
    </div>
  </div>
  <div class="separator"></div>
  <h2 class="entity-overview-heading">Entity Overview</h2>
  <div class="entity-grid">
    <div class="entity-category">
      <h3 class="entity-category-title">Named Individuals</h3>
      <p class="entity-list">{people_links}</p>
    </div>
    <div class="entity-category">
      <h3 class="entity-category-title">Organizations &amp; Products</h3>
      <p class="entity-list">{orgs_links}</p>
    </div>
  </div>
  <div class="separator"></div>
  <p class="summary-intro">{intro}</p>
  <p class="supporting-point">{supporting1}</p>
  <p class="supporting-point">{supporting2}</p>
  <p class="transition-text">{transition}</p>
  <p class="secondary-detail">{secondary}</p>
  <div class="separator"></div>
  {facts_html}
  <div class="separator"></div>
  <div class="entity-sentiment">
    <h4 class="entity-name">{sentiment_entity}</h4>
    <p class="entity-sentiment-details">
      <span class="sentiment-positive">Positive: 3</span>
      <span class="sentiment-negative">Negative: 1</span>
    </p>
    <p class="entity-summary">Central figure in the article narrative.</p>
    <p class="entity-keywords">Keywords: {", ".join(top_keywords[:4])}</p>
  </div>
  <div class="popularity-container">
    <h3 class="popularity-title">Topic Popularity</h3>
    <div class="popularity-score">
      <span class="popularity-number">72</span>
    </div>
    <p class="popularity-description">Moderately trending topic based on current news cycle.</p>
  </div>
  <div class="more-on-topic-container">
    <h3 class="more-on-topic-heading">More on Topic</h3>
    <ul class="related-terminology-list">
      <li class="terminology-item">
        <a class="resource-link" href="https://www.google.com/search?q={top_keywords[0].replace(' ', '+')}" target="_blank">{top_keywords[0]} - Latest Developments</a>
        <span class="resource-description">Search for the latest coverage and analysis on this topic.</span>
      </li>
    </ul>
  </div>
</div>"""
    return summary_html


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
                logger.info("DEBUG MODE: Using rich demo response generated from article content")
                summary_text = build_debug_summary(title, content)
                raw_response_text = "DEBUG MODE: Rich demo response generated from article content"
            else:
                summary_text, raw_response_text = call_llm_api(prompt, article_id, len(content))
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
