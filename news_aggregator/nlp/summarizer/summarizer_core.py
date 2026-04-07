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
from summarizer_prompt import create_plan_prompt, create_section_prompt
from summarizer_api import call_llm_api, set_model_config
from summarizer_html import clean_and_normalize_html, save_as_html
from summarizer_db import get_articles, update_article_summary
from summarizer_config import OUTPUT_HTML_DIR, ensure_output_directory
from summarizer_image import ensure_images_directory
from summarizer_structured import extract_json_payload, merge_plan_and_sections, render_summary_html_fragment

# Import database models and context
from db_scripts.db_context import DatabaseContext

logger = get_logger(__name__)


def build_structured_summary(article_id, title, content, include_featured_image):
    """Generate a structured summary in two stages: plan first, then section content."""
    plan_prompt = create_plan_prompt(content, len(content))
    if not plan_prompt:
        raise ValueError(f"Failed to build planning prompt for article ID {article_id}")

    logger.debug(f"PLAN PROMPT PREVIEW for {article_id}:\n{plan_prompt[:1000]}...")
    plan_text, plan_raw_response = call_llm_api(
        plan_prompt,
        article_id,
        len(content),
        response_format="json",
    )
    if not plan_text:
        raise ValueError(f"Planning stage returned no content for article ID {article_id}")

    plan_data = extract_json_payload(plan_text)

    section_prompt = create_section_prompt(content, len(content), plan_data)
    if not section_prompt:
        raise ValueError(f"Failed to build section prompt for article ID {article_id}")

    logger.debug(f"SECTION PROMPT PREVIEW for {article_id}:\n{section_prompt[:1000]}...")
    section_text, section_raw_response = call_llm_api(
        section_prompt,
        article_id,
        len(content),
        response_format="json",
    )
    if not section_text:
        raise ValueError(f"Section stage returned no content for article ID {article_id}")

    section_data = extract_json_payload(section_text)
    structured_summary = merge_plan_and_sections(plan_data, section_data, title)
    summary_html = render_summary_html_fragment(structured_summary)
    raw_response_text = (
        f"structured_plan: {plan_raw_response}\n"
        f"structured_sections: {section_raw_response}\n"
        f"include_featured_image={include_featured_image}"
    )

    return structured_summary, summary_html, raw_response_text


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


def _extract_entities_from_structured(structured_summary) -> dict:
    """
    Extract persons, localities, and institutions from a structured summary dict.

    Reads the 'entity_overview' section produced by merge_plan_and_sections().
    The entity_overview format is a list of grouped entries:
        [{"category": "People", "items": ["Name1", "Name2"]}, ...]
    Returns: {persons: [...], localities: [...], institutions: [...]}
    """
    persons = []
    localities = []
    institutions = []

    if not structured_summary:
        return {"persons": persons, "localities": localities, "institutions": institutions}

    _PERSON_CATS = {"people", "persons", "person", "key figures", "politicians", "leaders", "officials"}
    _LOCALITY_CATS = {"countries", "country", "locations", "location", "regions", "region",
                      "places", "place", "geographies", "geography", "localities", "locality", "nations"}
    _INSTITUTION_CATS = {"organizations", "organization", "organisations", "organisation",
                         "institutions", "institution", "companies", "agencies", "bodies", "groups"}

    entity_overview = structured_summary.get("entity_overview") or []
    if isinstance(entity_overview, list):
        for entry in entity_overview:
            if not isinstance(entry, dict):
                continue
            # Handle grouped format: {category, items}
            category = (entry.get("category") or entry.get("title") or "").strip().lower()
            items = entry.get("items") or entry.get("entities") or entry.get("values") or []
            if category and isinstance(items, list) and items:
                clean_items = [str(i).strip() for i in items if i and str(i).strip()]
                if category in _PERSON_CATS:
                    persons.extend(clean_items)
                elif category in _LOCALITY_CATS:
                    localities.extend(clean_items)
                elif category in _INSTITUTION_CATS:
                    institutions.extend(clean_items)
                continue
            # Fallback: flat format {name, type}
            name = entry.get("name") or entry.get("entity") or ""
            entity_type = (entry.get("type") or entry.get("entity_type") or "").lower()
            if not name:
                continue
            if entity_type in _PERSON_CATS:
                persons.append(name)
            elif entity_type in _LOCALITY_CATS:
                localities.append(name)
            elif entity_type in _INSTITUTION_CATS:
                institutions.append(name)
    elif isinstance(entity_overview, dict):
        persons = [str(p) for p in entity_overview.get("persons", []) if p]
        localities = [str(loc) for loc in entity_overview.get("localities", []) if loc]
        institutions = [str(inst) for inst in entity_overview.get("institutions", []) if inst]

    return {"persons": persons[:10], "localities": localities[:10], "institutions": institutions[:10]}


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
        self.skip_opinions = False
        self.skip_youtube = False
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
            
            structured_summary = None
            summary_text = None
            raw_response_text = None

            if self.debug_mode:
                logger.info("DEBUG MODE: Using rich demo response generated from article content")
                summary_text = build_debug_summary(title, content)
                raw_response_text = "DEBUG MODE: Rich demo response generated from article content"
            else:
                from summarizer_config import CONFIG, get_config_value
                include_featured_image = get_config_value(CONFIG, 'summarization', 'enable_featured_image_search', True)

                structured_summary, summary_text, raw_response_text = build_structured_summary(
                    article_id,
                    title,
                    content,
                    include_featured_image,
                )
                logger.info(f"Structured summary generated successfully for article ID {article_id}")
            
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
            
            # --- Collect public opinion data (before HTML save so it's included in one render) ---
            opinion_data = None
            if not self.debug_mode and not self.skip_opinions:
                try:
                    from opinion_analyzer import build_opinion_analysis
                    from summarizer_config import CONFIG, get_config_value
                    youtube_key = get_config_value(CONFIG, 'api_keys', 'youtube', '') or ''
                    collect_cfg = get_config_value(CONFIG, 'opinion_collection', None) or {}
                    if self.skip_youtube:
                        collect_cfg = dict(collect_cfg)
                        collect_cfg['skip_youtube'] = True
                    if collect_cfg.get('enabled', True):
                        entities_dict = _extract_entities_from_structured(structured_summary)
                        opinion_data = build_opinion_analysis(
                            article_id, title, entities_dict,
                            youtube_api_key=youtube_key,
                            collect_config=collect_cfg,
                        )
                except Exception as oe:
                    logger.warning(f"[opinion] Collection failed for {article_id}: {oe}", exc_info=True)

            # Save as HTML, now passing keywords from the database to enable image search
            # Save as HTML, now passing the schema along with keywords
            html_saved = save_as_html(
                article_id, title, url, content, summary_text, raw_response_text, self.schema,
                keywords=article_info.get('keywords'),
                existing_gemini_title=article_info.get('summary_article_gemini_title'),
                structured_summary=structured_summary,
                opinion_data=opinion_data,
            )

            if not html_saved:
                logger.error(f"Failed to save HTML output for article ID: {article_id}")
                return False

            # Persist opinion data to DB after HTML is saved
            if opinion_data and not self.debug_mode:
                try:
                    from summarizer_db import update_opinion_analysis
                    update_opinion_analysis(self.db_context, self.schema, article_id, opinion_data)
                except Exception as oe:
                    logger.warning(f"[opinion] DB save failed for {article_id}: {oe}")
            
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
