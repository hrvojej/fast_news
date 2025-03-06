# summarizer_db.py
"""
Module for database operations for the article summarization system.
"""

import os
import sys
import uuid
from datetime import datetime, timezone
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

def get_articles(db_context, schema, limit=None):
    """
    Get articles from the database to be processed.
    
    Args:
        db_context: Database context for session management
        schema (str): Database schema name
        limit (int, optional): Maximum number of articles to retrieve
        
    Returns:
        list: List of article rows from the database
    """
    try:
        with db_context.session() as session:
            # Build query
            query = f"SELECT article_id, title, url, content FROM {schema}.articles"
            
            # Add conditions to filter out articles that already have summaries
            # Uncomment this if you want to only process articles without summaries
            # query += " WHERE summary IS NULL OR summary = ''"
            
            # Add limit if specified
            if limit and isinstance(limit, int) and limit > 0:
                query += f" LIMIT {limit}"
            
            # Execute query
            result = session.execute(text(query))
            articles = result.fetchall()
            
            logger.info(f"Retrieved {len(articles)} articles from database")
            return articles
            
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
            # Handle string article_id (convert to UUID)
            if isinstance(article_id, str):
                try:
                    article_id = uuid.UUID(article_id)
                except ValueError as e:
                    logger.error(f"Invalid article_id format: {article_id} - {e}")
                    return False
            
            # Use raw SQL instead of ORM to avoid model conflicts
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
            
            # Check if the update was successful
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
            # Handle string article_id (convert to UUID)
            if isinstance(article_id, str):
                try:
                    article_id = uuid.UUID(article_id)
                except ValueError as e:
                    logger.error(f"Invalid article_id format: {article_id} - {e}")
                    return None
            
            # Query for article metadata
            query = text(f"""
                SELECT 
                    title, url, published_at, author, category_id
                FROM 
                    {schema}.articles
                WHERE 
                    article_id = :article_id
            """)
            
            result = session.execute(query, {"article_id": article_id})
            metadata = result.fetchone()
            
            if metadata:
                # Convert to dictionary
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
            
            # Create dictionary mapping category_id to name
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
            # Query for total articles
            total_query = text(f"SELECT COUNT(*) as count FROM {schema}.articles")
            total_result = session.execute(total_query).fetchone()
            
            # Query for summarized articles
            summarized_query = text(f"""
                SELECT COUNT(*) as count 
                FROM {schema}.articles 
                WHERE summary IS NOT NULL AND summary != ''
            """)
            summarized_result = session.execute(summarized_query).fetchone()
            
            # Calculate percentages
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