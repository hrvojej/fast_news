# summarizer_cli.py
"""
Command-line interface for the article summarization system.
"""

import os
import sys
import argparse
import time
import traceback

# Add package root to path
# Import path configuration first
from summarizer_path_config import configure_paths
configure_paths()

# Import our modules
from summarizer_logging import get_logger
from summarizer_core import ArticleSummarizer
from summarizer_config import CONFIG, get_config_value, ensure_output_directory
from summarizer_db import get_summarization_stats

# Import database models
from db_scripts.models.models import create_portal_article_model, create_portal_category_model
from db_scripts.db_context import DatabaseContext

# Initialize logger
logger = get_logger(__name__)

def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: The parsed arguments
    """
    parser = argparse.ArgumentParser(description='Article Summarizer CLI')
    
    # Environment and operation mode
    parser.add_argument('--env', type=str, default='dev', choices=['dev', 'stage', 'prod'],
                        help="Environment to run in (dev, stage, prod)")
    parser.add_argument('--debug', action='store_true',
                        help="Run in debug mode (uses sample response instead of API call)")
    
    # Article selection
    parser.add_argument('--limit', type=int, default=None,
                        help="Limit the number of articles to process")
    parser.add_argument('--schema', type=str, default='pt_nyt',
                        help="Database schema to use")
    parser.add_argument('--article-id', type=str, default=None,
                        help="Process a specific article by ID")
    
    # Output options
    parser.add_argument('--skip-html', action='store_true',
                        help="Skip generating HTML files")
    parser.add_argument('--output-dir', type=str, default=None,
                        help="Custom output directory for HTML files")
    
    # Behavior options
    parser.add_argument('--dry-run', action='store_true',
                        help="Dry run mode (don't update database)")
    parser.add_argument('--force', action='store_true',
                        help="Force regeneration even if a summary exists")
    parser.add_argument('--stats', action='store_true',
                        help="Show summarization statistics and exit")
    
    return parser.parse_args()

def show_stats(args):
    """
    Display summarization statistics.
    
    Args:
        args (argparse.Namespace): Command line arguments
    """
    try:
        # Create database context
        db_context = DatabaseContext.get_instance(args.env)
        
        # Get statistics
        stats = get_summarization_stats(db_context, args.schema)
        
        # Display statistics
        print("\n=== Article Summarization Statistics ===")
        print(f"Schema: {args.schema}")
        print(f"Environment: {args.env}")
        print(f"Total articles: {stats['total_articles']}")
        print(f"Summarized articles: {stats['summarized_articles']}")
        print(f"Remaining articles: {stats['remaining_articles']}")
        print(f"Completion: {stats['completion_percentage']}%")
        print("=========================================\n")
        
    except Exception as e:
        logger.error(f"Error displaying statistics: {e}")
        print(f"Error: {e}")

def main():
    """Main entry point for the CLI."""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Show statistics if requested
        if args.stats:
            show_stats(args)
            return
        
        # Set up models for the specified schema
        article_model = create_portal_article_model(args.schema)
        
        # Override output directory if specified
        if args.output_dir:
            global OUTPUT_HTML_DIR
            from summarizer_config import OUTPUT_HTML_DIR
            OUTPUT_HTML_DIR = args.output_dir
            
        # Ensure output directory exists
        if not args.skip_html:
            ensure_output_directory()
        
        # Get configuration values
        batch_size = get_config_value(CONFIG, 'database', 'batch_size', 10)
        
        # Create and run the summarizer
        summarizer = ArticleSummarizer(
            schema=args.schema,
            article_model=article_model,
            env=args.env,
            debug_mode=args.debug
        )
        
        # Run the summarizer
        if args.article_id:
            # Process a single article
            logger.info(f"Processing single article ID: {args.article_id}")
            with DatabaseContext.get_instance(args.env).session() as session:
                from sqlalchemy import text
                query = text(f"SELECT article_id, title, url, content FROM {args.schema}.articles WHERE article_id = :article_id")
                article = session.execute(query, {"article_id": args.article_id}).fetchone()
                
                if article:
                    article_info = dict(article._mapping)
                    success = summarizer.summarize_article(article_info)
                    logger.info(f"Article processing {'succeeded' if success else 'failed'}")
                else:
                    logger.error(f"Article ID {args.article_id} not found")
                    
        else:
            # Process multiple articles with the specified limit
            if args.limit and args.limit < batch_size:
                effective_limit = args.limit
            elif args.limit is None:
                effective_limit = batch_size
            else:
                effective_limit = args.limit
                
            logger.info(f"Processing up to {effective_limit} articles")
            summarizer.run(limit=effective_limit)
        
        logger.info("Summarization process completed")
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        print("\nProcess interrupted by user")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        logger.error(traceback.format_exc())
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()