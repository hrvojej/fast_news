# summarizer_db.py
"""
Module for database operations for the article summarization system.
"""

import os
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

            processed_date = context.get("processed_date")
            gemini_title = context.get("title")
            featured_image_data = context.get("featured_image")
            if featured_image_data is not None:
                import json
                featured_image_data = json.dumps(featured_image_data)
            summary_paragraphs = context.get("summary_paragraphs", [])
            summary_first_paragraph = summary_paragraphs[0]['content'] if summary_paragraphs else None
            popularity_score = context.get("popularity_score", 0)

            query = text(f"""
                UPDATE {schema}.articles
                SET summary_generated_at = :processed_date,
                    summary_article_gemini_title = :gemini_title,
                    summary_featured_image = :featured_image,
                    summary_first_paragraph = :first_paragraph,
                    nlp_updated_at = :updated_at,
                    popularity_score = :popularity_score,
                    article_html_file_location = :article_html_file_location
                WHERE article_id = :article_id
            """)

            params = {
                "processed_date": processed_date,
                "gemini_title": gemini_title,
                "featured_image": featured_image_data,
                "first_paragraph": summary_first_paragraph,
                "updated_at": datetime.now(timezone.utc),
                "popularity_score": popularity_score,
                "article_html_file_location": context.get("article_html_file_location"),
                "article_id": article_id
            }

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
