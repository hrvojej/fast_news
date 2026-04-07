# summarizer_db.py
"""
Module for database operations for the article summarization system.
"""

import os
import re
import sys
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import text

# Add the proper path to locate db_scripts
# Import path configuration first
from summarizer_path_config import configure_paths
configure_paths()

# Now import db_scripts
from db_scripts.db_context import DatabaseContext
from summarizer_logging import get_logger

# Initialize logger
logger = get_logger(__name__)


def get_articles(db_context, schema, limit=None, recent_timeout_hours=None):
    """
    Get articles from the database to be processed.
    This version retrieves articles that have html_processing_status false and then further
    filters out those whose article_html_file_location indicates an HTML file that already exists on disk.

    Args:
        db_context: Database context for session management
        schema (str): Database schema name
        limit (int, optional): Maximum number of articles to retrieve

    Returns:
        list: List of article rows from the database that need processing.
    """
    from summarizer_config import OUTPUT_HTML_DIR
    import os
    try:
        with db_context.session() as session:
            query = f"""
                SELECT a.article_id, a.title, a.keywords, a.url, a.content, a.article_html_file_location, a.pub_date
                FROM {schema}.articles a
                JOIN {schema}.article_status s ON a.url = s.url
                WHERE s.html_processing_status = false
                ORDER BY a.pub_date DESC
            """
            result = session.execute(text(query))
            articles = result.fetchall()
            logger.info(f"Retrieved {len(articles)} articles from database")

            # --- New File Existence Filtering ---
            filtered_articles = []
            for article in articles:
                file_location = article._mapping.get('article_html_file_location')
                if file_location:
                    full_path = os.path.join(OUTPUT_HTML_DIR, file_location)
                    if os.path.exists(full_path):
                        logger.info(f"Skipping article {article._mapping.get('article_id')} because file exists at {full_path}")
                        continue
                filtered_articles.append(article)
            logger.info(f"After file-check filtering, {len(filtered_articles)} articles eligible for processing")

            # --- Apply the Limit in Python ---
            if limit and isinstance(limit, int) and limit > 0:
                filtered_articles = filtered_articles[:limit]
                logger.info(f"Returning top {len(filtered_articles)} articles based on limit parameter")

            return filtered_articles
    except Exception as e:
        logger.error(f"Error retrieving articles from database: {e}", exc_info=True)
        return []


def update_article_summary(db_context, schema, article_id, summary):
    """
    Update an article with its summary in the database.
    
    Args:
        db_context: Database context for session management
        schema (str): Database schema name
        article_id: The ID of the article to update
        summary (str): The generated summary
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with db_context.session() as session:
            if isinstance(article_id, str):
                try:
                    article_id = uuid.UUID(article_id)
                except ValueError as e:
                    logger.error(f"Invalid article_id format: {article_id} - {e}")
                    return False
            
            # UPDATE query instead of SELECT
            query = text(f"""
                UPDATE {schema}.articles
                SET summary = :summary, 
                    nlp_updated_at = :updated_at
                WHERE article_id = :article_id
            """)
            
            params = {
                "summary": summary,
                "updated_at": datetime.now(timezone.utc),
                "article_id": article_id
            }
            
            result = session.execute(query, params)
            session.commit()
            
            rows_affected = result.rowcount
            if rows_affected > 0:
                logger.info(f"Article ID {article_id} summary updated in the database")
                return True
            else:
                logger.error(f"Article ID {article_id} not found in the database")
                return False
    except Exception as e:
        logger.error(f"Database error updating article ID {article_id}: {e}", exc_info=True)
        if 'session' in locals():
            session.rollback()
        return False

def get_article_metadata(db_context, schema, article_id):
    """
    Get metadata for a specific article.
    
    Args:
        db_context: Database context for session management
        schema (str): Database schema name
        article_id: The ID of the article
        
    Returns:
        dict: Article metadata or None if error
    """
    try:
        with db_context.session() as session:
            if isinstance(article_id, str):
                try:
                    article_id = uuid.UUID(article_id)
                except ValueError as e:
                    logger.error(f"Invalid article_id format: {article_id} - {e}")
                    return None
            
            # Use pub_date instead of published_at
            query = text(f"""
                SELECT 
                    title, url, pub_date, author, category_id
                FROM 
                    {schema}.articles
                WHERE 
                    article_id = :article_id
            """)
            
            result = session.execute(query, {"article_id": article_id})
            metadata = result.fetchone()
            
            if metadata:
                return dict(metadata._mapping)
            else:
                logger.error(f"Article ID {article_id} metadata not found")
                return None
    except Exception as e:
        logger.error(f"Error retrieving article metadata: {e}", exc_info=True)
        return None

def get_article_categories(db_context, schema):
    """
    Get all article categories from the database.
    
    Args:
        db_context: Database context for session management
        schema (str): Database schema name
        
    Returns:
        dict: Dictionary mapping category IDs to names
    """
    try:
        with db_context.session() as session:
            query = text(f"SELECT category_id, name FROM {schema}.categories")
            result = session.execute(query)
            categories = {row.category_id: row.name for row in result}
            logger.info(f"Retrieved {len(categories)} categories from database")
            return categories
    except Exception as e:
        logger.error(f"Error retrieving categories: {e}", exc_info=True)
        return {}

def get_summarization_stats(db_context, schema):
    """
    Get statistics about summarization progress.
    
    Args:
        db_context: Database context for session management
        schema (str): Database schema name
        
    Returns:
        dict: Statistics about summarization progress
    """
    try:
        with db_context.session() as session:
            total_query = text(f"SELECT COUNT(*) as count FROM {schema}.articles")
            total_result = session.execute(total_query).fetchone()
            
            summarized_query = text(f"""
                SELECT COUNT(*) as count 
                FROM {schema}.articles 
                WHERE summary IS NOT NULL AND summary != ''
            """)
            summarized_result = session.execute(summarized_query).fetchone()
            
            total = total_result.count if total_result else 0
            summarized = summarized_result.count if summarized_result else 0
            percentage = (summarized / total * 100) if total > 0 else 0
            
            return {
                "total_articles": total,
                "summarized_articles": summarized,
                "remaining_articles": total - summarized,
                "completion_percentage": round(percentage, 2)
            }
    except Exception as e:
        logger.error(f"Error retrieving summarization stats: {e}", exc_info=True)
        return {
            "total_articles": 0,
            "summarized_articles": 0,
            "remaining_articles": 0,
            "completion_percentage": 0,
            "error": str(e)
        }

def update_article_summary_details(db_context, schema, article_id, context):
    """
    Update additional summary fields for an article in the database.

    Args:
        db_context: Database context for session management.
        schema (str): Database schema name.
        article_id: The ID of the article to update.
        context (dict): Dictionary containing additional summary fields:
            - processed_date: Date string for summary_generated_at.
            - title: Gemini title for summary_article_gemini_title.
            - featured_image: Dictionary with image data for summary_featured_image.
            - summary_paragraphs: List of dictionaries; the first paragraph's content is used
                                  for summary_first_paragraph.
            - popularity_score: Integer value for the article's popularity score.

    Returns:
        bool: True if update successful, False otherwise.
    """
    try:
        with db_context.session() as session:
            if isinstance(article_id, str):
                try:
                    import uuid
                    article_id = uuid.UUID(article_id)
                except ValueError as e:
                    logger.error(f"Invalid article_id format: {article_id} - {e}")
                    return False

            import json

            processed_date = context.get("summary_generated_at") or datetime.now(timezone.utc)
            gemini_title = context.get("title")
            featured_image_data = context.get("featured_image")
            if featured_image_data is not None:
                featured_image_data = json.dumps(featured_image_data)
            summary_paragraphs = context.get("summary_paragraphs", [])
            summary_first_paragraph = None
            if summary_paragraphs:
                first_paragraph = summary_paragraphs[0]
                if isinstance(first_paragraph, dict):
                    summary_first_paragraph = first_paragraph.get('text') or first_paragraph.get('content')
                if summary_first_paragraph:
                    summary_first_paragraph = re.sub(r'<[^>]+>', '', summary_first_paragraph).strip()
            popularity_score = context.get("popularity_score", 0)

            columns_query = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema AND table_name = 'articles'
            """)
            existing_columns = {
                row.column_name for row in session.execute(columns_query, {"schema": schema}).fetchall()
            }

            column_values = {
                "summary_generated_at": ("scalar", processed_date),
                "summary_article_gemini_title": ("scalar", gemini_title),
                "summary_featured_image": ("scalar", featured_image_data),
                "summary_first_paragraph": ("scalar", summary_first_paragraph),
                "nlp_updated_at": ("scalar", datetime.now(timezone.utc)),
                "popularity_score": ("scalar", popularity_score),
                "article_html_file_location": ("scalar", context.get("article_html_file_location")),
                "summary_plan_json": ("jsonb", context.get("summary_plan_json")),
                "summary_keywords_json": ("jsonb", context.get("summary_keywords_json")),
                "summary_entities_json": ("jsonb", context.get("summary_entities_json")),
                "summary_sections_json": ("jsonb", context.get("summary_sections_json")),
                "summary_facts_json": ("jsonb", context.get("summary_facts_json")),
                "summary_resources_json": ("jsonb", context.get("summary_resources_json")),
                "summary_sentiment_json": ("jsonb", context.get("summary_sentiment_json")),
                "summary_popularity_json": ("jsonb", context.get("summary_popularity_json")),
            }

            set_clauses = []
            params = {"article_id": article_id}
            for column_name, (value_type, value) in column_values.items():
                if column_name not in existing_columns:
                    continue
                if value_type == "jsonb":
                    set_clauses.append(f"{column_name} = CAST(:{column_name} AS jsonb)")
                    params[column_name] = json.dumps(value) if value is not None else None
                else:
                    set_clauses.append(f"{column_name} = :{column_name}")
                    params[column_name] = value

            if not set_clauses:
                logger.error(f"No summary detail columns available for schema {schema}")
                return False

            query = text(f"""
                UPDATE {schema}.articles
                SET {', '.join(set_clauses)}
                WHERE article_id = :article_id
            """)

            result = session.execute(query, params)
            session.commit()
            rows_affected = result.rowcount

            if rows_affected > 0:
                logger.info(f"Article ID {article_id} additional summary details updated successfully.")
                return True
            else:
                logger.error(f"Article ID {article_id} not found when updating summary details.")
                return False
    except Exception as e:
        logger.error(f"Error updating article summary details for article ID {article_id}: {e}", exc_info=True)
        if 'session' in locals():
            session.rollback()
        return False

def get_related_articles(db_context, schema, current_article_id, current_keywords, limit=5):
    """
    Retrieve related articles based on matching keywords, popularity, and recency.

    Args:
        db_context: Database context for session management.
        schema (str): Database schema name.
        current_article_id: ID of the current article to exclude.
        current_keywords (list): List of keywords from the current article.
        limit (int, optional): Number of related articles to return (default: 5).

    Returns:
        list: List of dictionaries with keys 'title' and 'link' for related articles.
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import text

    cutoff_time = datetime.now(timezone.utc) - timedelta(days=60)
    query = text(f"""
        SELECT article_id, summary_article_gemini_title, article_html_file_location, keywords, summary_generated_at, popularity_score 
        FROM {schema}.articles
        WHERE summary_generated_at IS NOT NULL 
          AND summary_generated_at >= :cutoff_time
    """)
    params = {"cutoff_time": cutoff_time}

    try:
        with db_context.session() as session:
            result = session.execute(query, params)
            articles = result.fetchall()
    except Exception as e:
        logger.error(f"Error retrieving related articles: {e}", exc_info=True)
        return []

    candidates = []
    for row in articles:
        if str(row.article_id) == str(current_article_id):
            continue
        if not row.summary_article_gemini_title or not row.article_html_file_location:
            continue

        candidate_keywords = []
        if row.keywords:
            if isinstance(row.keywords, list):
                candidate_keywords = [str(kw).strip().lower() for kw in row.keywords if str(kw).strip()]
            elif isinstance(row.keywords, str):
                candidate_keywords = [kw.strip().lower() for kw in row.keywords.split(',') if kw.strip()]
        
        matching_keywords = set([kw.lower() for kw in current_keywords]).intersection(set(candidate_keywords))
        matching_count = len(matching_keywords)
        
        candidate = {
            "article_id": row.article_id,
            "title": row.summary_article_gemini_title,
            "link": row.article_html_file_location,
            "matching_count": matching_count,
            "popularity_score": row.popularity_score if row.popularity_score is not None else 0,
            "summary_generated_at": row.summary_generated_at
        }
        candidates.append(candidate)
    
    sorted_candidates = sorted(candidates, key=lambda x: (x["matching_count"], x["popularity_score"], x["summary_generated_at"]), reverse=True)
    related_articles = [{"title": cand["title"], "link": cand["link"]} for cand in sorted_candidates[:limit]]
    return related_articles


# New function to update the html_date in the article_status table
def update_article_status_html_date(db_context, schema, url, html_date):
    """
    Update the html_date field for a record in the article_status table.

    Args:
        db_context: Database context for session management.
        schema (str): Database schema name.
        url (str): The article URL (used as unique identifier).
        html_date (datetime): Timestamp when the HTML was saved.

    Returns:
        bool: True if update successful, False otherwise.
    """
    try:
        with db_context.session() as session:
            query = text(f"""
                UPDATE {schema}.article_status
                SET html_date = :html_date
                WHERE url = :url
            """)
            params = {"html_date": html_date, "url": url}
            result = session.execute(query, params)
            session.commit()
            if result.rowcount > 0:
                logger.info(f"Article status updated for URL {url} with html_date {html_date}")
                return True
            else:
                logger.warning(f"No article status record found for URL {url} to update html_date")
                return False
    except Exception as e:
        logger.error(f"Error updating html_date for URL {url}: {e}", exc_info=True)
        return False

def update_article_status_processing(db_context, schema, url, processing_status=True):
    """
    Update the html_processing_status for a record in the article_status table.
    
    Args:
        db_context: Database context for session management.
        schema (str): Database schema name.
        url (str): The article URL (used as unique identifier).
        processing_status (bool): The processing flag to set (default: True).
        
    Returns:
        bool: True if the update was successful, False otherwise.
    """
    try:
        with db_context.session() as session:
            query = text(f"""
                UPDATE {schema}.article_status
                SET html_processing_status = :status
                WHERE url = :url
            """)
            params = {"status": processing_status, "url": url}
            result = session.execute(query, params)
            session.commit()
            if result.rowcount > 0:
                logger.info(f"Article status for URL {url} set to processing status {processing_status}")
                return True
            else:
                logger.warning(f"No article status record found for URL {url} when setting processing status")
                return False
    except Exception as e:
        logger.error(f"Error updating processing status for URL {url}: {e}", exc_info=True)
        return False


def claim_article(db_context, schema):
    """
    Atomically select and claim a single article for processing.
    This function selects one article meeting all the criteria (html_processing_status is false
    and either article_html_file_location is NULL/empty or file does not exist on disk),
    locks the row using FOR UPDATE SKIP LOCKED, updates its status to mark it as processing,
    and then commits the transaction so that no other process can claim it.

    Args:
        db_context: Database context for session management.
        schema (str): Database schema name.

    Returns:
        A row representing the claimed article, or None if no eligible article was found.
    """
    from summarizer_config import OUTPUT_HTML_DIR
    import os
    try:
        with db_context.session() as session:
            # Atomically select a single eligible article and lock the row.
            query = f"""
                SELECT a.article_id, a.title, a.keywords, a.url, a.content, a.article_html_file_location, a.pub_date
                FROM {schema}.articles a
                JOIN {schema}.article_status s ON a.url = s.url
                WHERE s.html_processing_status = false
                  AND (a.article_html_file_location IS NULL OR a.article_html_file_location = '')
                ORDER BY a.pub_date DESC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            """
            result = session.execute(text(query))
            article = result.fetchone()
            if article is None:
                logger.info("No eligible article found to claim.")
                return None

            # Optionally, perform an additional check on disk: if article_html_file_location is set,
            # ensure that the file does not exist.
            file_location = article._mapping.get('article_html_file_location')
            if file_location:
                full_path = os.path.join(OUTPUT_HTML_DIR, file_location)
                if os.path.exists(full_path):
                    logger.info(f"Skipping article {article._mapping.get('article_id')} because file exists at {full_path}")
                    return None

            # Update the flag to mark this article as being processed.
            update_query = text(f"""
                UPDATE {schema}.article_status
                SET html_processing_status = true
                WHERE url = :url
            """)
            session.execute(update_query, {"url": article._mapping.get("url")})
            session.commit()
            logger.info(f"Claimed article {article._mapping.get('article_id')} for processing.")
            return article
    except Exception as e:
        logger.error(f"Error claiming article: {e}", exc_info=True)
        return None


def get_articles_for_backfill(db_context, schema, limit=None):
    """
    Return articles that already have a summary/HTML but are missing the JSONB structured fields.
    These are candidates for the backfill-json pipeline: run LLM on their content and store
    only the 8 JSONB columns without touching HTML files or legacy columns.

    Args:
        db_context: Database context for session management.
        schema (str): Database schema name.
        limit (int, optional): Maximum number of articles to return.

    Returns:
        list[dict]: List of article dicts with keys article_id, title, url, content,
                    summary_article_gemini_title.
    """
    try:
        with db_context.session() as session:
            limit_clause = f"LIMIT {limit}" if (limit and isinstance(limit, int) and limit > 0) else ""
            query = f"""
                SELECT article_id, title, url, content, summary_article_gemini_title
                FROM {schema}.articles
                WHERE summary_plan_json IS NULL
                  AND content IS NOT NULL AND content != ''
                  AND article_html_file_location IS NOT NULL AND article_html_file_location != ''
                ORDER BY pub_date DESC
                {limit_clause}
            """
            result = session.execute(text(query))
            rows = result.fetchall()
            logger.info(f"[backfill] Found {len(rows)} articles needing JSONB backfill in {schema}")
            return [dict(row._mapping) for row in rows]
    except Exception as e:
        logger.error(f"[backfill] Error fetching backfill articles for {schema}: {e}", exc_info=True)
        return []


def update_jsonb_fields_only(db_context, schema, article_id, structured_summary):
    """
    Update only the 8 JSONB structured-summary columns for an existing article.
    Does NOT touch: article_html_file_location, summary_article_gemini_title,
    summary_featured_image, summary_first_paragraph, popularity_score, or html_date.

    Args:
        db_context: Database context for session management.
        schema (str): Database schema name.
        article_id (str | uuid.UUID): The article's primary key.
        structured_summary (dict): The canonical structured-summary dict produced by
                                   merge_plan_and_sections().

    Returns:
        bool: True if the row was updated, False otherwise.
    """
    from summarizer_structured import build_structured_db_fields
    import json

    fields = build_structured_db_fields(structured_summary)
    if not fields:
        logger.warning(f"[backfill] build_structured_db_fields returned empty for {article_id}")
        return False

    try:
        with db_context.session() as session:
            if isinstance(article_id, str):
                article_id = uuid.UUID(article_id)

            columns_query = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema AND table_name = 'articles'
            """)
            existing_columns = {
                row.column_name
                for row in session.execute(columns_query, {"schema": schema}).fetchall()
            }

            jsonb_cols = [
                "summary_plan_json",
                "summary_keywords_json",
                "summary_entities_json",
                "summary_sections_json",
                "summary_facts_json",
                "summary_resources_json",
                "summary_sentiment_json",
                "summary_popularity_json",
            ]

            set_clauses = []
            params = {"article_id": article_id}
            for col in jsonb_cols:
                if col not in existing_columns:
                    continue
                set_clauses.append(f"{col} = CAST(:{col} AS jsonb)")
                value = fields.get(col)
                params[col] = json.dumps(value) if value is not None else None

            if not set_clauses:
                logger.warning(f"[backfill] No JSONB columns present in {schema}.articles — skipping")
                return False

            # Also bump nlp_updated_at so we know when the backfill ran
            if "nlp_updated_at" in existing_columns:
                set_clauses.append("nlp_updated_at = NOW()")

            query = text(f"""
                UPDATE {schema}.articles
                SET {', '.join(set_clauses)}
                WHERE article_id = :article_id
            """)
            result = session.execute(query, params)
            session.commit()

            if result.rowcount > 0:
                logger.info(f"[backfill] JSONB fields updated for article {article_id} in {schema}")
                return True
            else:
                logger.error(f"[backfill] Article {article_id} not found in {schema}")
                return False
    except Exception as e:
        logger.error(f"[backfill] Error updating JSONB fields for {article_id}: {e}", exc_info=True)
        if "session" in locals():
            session.rollback()
        return False


def update_opinion_analysis(db_context, schema, article_id, opinion_data):
    """
    Persist the opinion_analysis_json JSONB payload for a single article.

    Args:
        db_context: Database context for session management.
        schema (str): Database schema name (e.g. 'pt_reuters').
        article_id (str | uuid.UUID): The article's primary key.
        opinion_data (dict): The payload produced by build_opinion_analysis().

    Returns:
        bool: True if the row was updated, False otherwise.
    """
    import json

    if not opinion_data:
        return False

    try:
        with db_context.session() as session:
            if isinstance(article_id, str):
                article_id = uuid.UUID(article_id)

            query = text(f"""
                UPDATE {schema}.articles
                SET opinion_analysis_json = CAST(:data AS jsonb),
                    nlp_updated_at = NOW()
                WHERE article_id = :article_id
            """)
            result = session.execute(query, {
                "data": json.dumps(opinion_data),
                "article_id": article_id,
            })
            session.commit()

            if result.rowcount > 0:
                logger.info(f"[opinion] Saved opinion_analysis_json for {article_id} in {schema}")
                return True
            else:
                logger.warning(f"[opinion] Article {article_id} not found in {schema} — opinion not saved")
                return False
    except Exception as exc:
        logger.error(f"[opinion] Error saving opinion_analysis_json for {article_id}: {exc}", exc_info=True)
        if "session" in locals():
            session.rollback()
        return False
