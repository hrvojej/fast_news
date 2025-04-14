# main.py
"""
Main entry point for the article summarization system.
"""

import os
import sys
import argparse
import time
import traceback

# Add current directory to path
from summarizer_path_config import configure_paths
configure_paths()

# Import our modules
from summarizer_logging import get_logger
from summarizer_core import ArticleSummarizer
from summarizer_config import CONFIG, get_config_value, ensure_output_directory
from summarizer_db import get_articles, get_summarization_stats
from summarizer_monitoring import process_metrics, print_progress

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
    parser = argparse.ArgumentParser(description='Article Summarization System')
    
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
    parser.add_argument('--batch-size', type=int, default=None,
                        help="Number of articles to process in each batch")
    
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
    parser.add_argument('--continuous', action='store_true',
                        help="Run continuously, processing new articles as they arrive")
    parser.add_argument('--interval', type=int, default=3600,
                        help="Interval in seconds between continuous runs (default: 3600)")
    parser.add_argument('--verbose', action='store_true',
                        help="Enable verbose logging")
    parser.add_argument('--recent-timeout', type=int, default=6,
                        help="Do not process articles that have been processed within the last specified number of hours (default: 6)")

    
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

def process_single_article(args, summarizer):
    """
    Process a single article by ID.
    
    Args:
        args (argparse.Namespace): Command line arguments
        summarizer (ArticleSummarizer): The summarizer instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Processing single article ID: {args.article_id}")
    
    try:
        with DatabaseContext.get_instance(args.env).session() as session:
            from sqlalchemy import text
            query = text("SELECT article_id, title, url, content, summary_article_gemini_title FROM {}.articles WHERE article_id = :article_id".format(args.schema))

            article = session.execute(query, {"article_id": args.article_id}).fetchone()

            if article:
                article_info = dict(article._mapping)
                success = summarizer.summarize_article(article_info)
                logger.info(f"Article processing {'succeeded' if success else 'failed'}")
                return success
            else:
                logger.error(f"Article ID {args.article_id} not found")
                return False
    except Exception as e:
        logger.error(f"Error processing article ID {args.article_id}: {e}", exc_info=True)
        return False

def run_batch_mode(args, summarizer):
    try:
        # Get batch size from args or config
        batch_size = args.batch_size
        if batch_size is None:
            batch_size = get_config_value(CONFIG, 'database', 'batch_size', 10)
            
        # Determine effective limit
        if args.limit and args.limit < batch_size:
            effective_limit = args.limit
        elif args.limit is None:
            effective_limit = batch_size
        else:
            effective_limit = args.limit
            
        logger.info(f"Processing up to {effective_limit} articles from {args.schema} in {args.env}")
        
        # WAIT LOOP: Check until there is at least one article ready for processing.
        db_context = DatabaseContext.get_instance(args.env)
        articles = get_articles(db_context, args.schema)
        while not articles:
            logger.info("No articles found to process. Waiting for 30 seconds before rechecking...")
            time.sleep(30)
            db_context = DatabaseContext.get_instance(args.env)
            articles = get_articles(db_context, args.schema)
        
        if not args.dry_run:
            stats_before = get_summarization_stats(DatabaseContext.get_instance(args.env), args.schema)
            total_articles = stats_before['total_articles']
            process_metrics.start_run(total_articles)

            # Run summarizer
            result = summarizer.run(limit=effective_limit)

            stats_after = get_summarization_stats(DatabaseContext.get_instance(args.env), args.schema)
            process_metrics.complete_run()
            
            # Show progress
            print_progress()
            
            processed = summarizer.processed_count
            failed = summarizer.failed_count
            logger.info(f"Completed batch. Processed: {processed}, Failed: {failed}")
            
        return True
        
    except Exception as e:
        logger.error(f"Error in batch mode: {e}", exc_info=True)
        return False


def run_continuous_mode(args, summarizer):
    """
    Run the summarizer in continuous mode, processing articles at regular intervals.
    
    Args:
        args (argparse.Namespace): Command line arguments
        summarizer (ArticleSummarizer): The summarizer instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Starting continuous mode with interval of {args.interval} seconds")
    
    try:
        # Get batch size from args or config
        batch_size = args.batch_size
        if batch_size is None:
            batch_size = get_config_value(CONFIG, 'database', 'batch_size', 10)
        
        # Run indefinitely
        run_count = 0
        while True:
            run_count += 1
            logger.info(f"Starting continuous run #{run_count}")
            
            # Run a batch
            success = run_batch_mode(args, summarizer)
            
            # Sleep for the interval
            logger.info(f"Completed run #{run_count}. Sleeping for {args.interval} seconds...")
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        logger.info("Continuous mode interrupted by user")
        print("\nContinuous mode interrupted by user")
        return True
        
    except Exception as e:
        logger.error(f"Error in continuous mode: {e}", exc_info=True)
        return False

def main():
    """Main entry point for the article summarization system."""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Set log level if verbose
        if args.verbose:
            import logging
            from summarizer_logging import DEFAULT_LOG_LEVEL
            os.environ['LOG_LEVEL'] = 'DEBUG'
        
        # Show statistics if requested
        if args.stats:
            show_stats(args)
            return
        
        # Override output directory if specified
        if args.output_dir:
            global OUTPUT_HTML_DIR
            from summarizer_config import OUTPUT_HTML_DIR
            OUTPUT_HTML_DIR = args.output_dir
            
        # Ensure output directory exists
        if not args.skip_html:
            ensure_output_directory()
        
        # Set up models for the specified schema
        article_model = create_portal_article_model(args.schema)
        
        # Create summarizer instance
        summarizer = ArticleSummarizer(
            schema=args.schema,
            article_model=article_model,
            env=args.env,
            debug_mode=args.debug
        )
        
        # Set the recent timeout (in hours) so that articles processed within this time window are skipped.
        summarizer.recent_timeout = args.recent_timeout
        logger.info(f"Skipping articles processed in the last {args.recent_timeout} hours")
        
        # Process based on mode
        if args.article_id:
            # Process a single article
            process_single_article(args, summarizer)
        elif args.continuous:
            # Run in continuous mode
            run_continuous_mode(args, summarizer)
        else:
            # Run in batch mode
            run_batch_mode(args, summarizer)
        
        logger.info("Summarization process completed")
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        print("\nProcess interrupted by user")
        
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
