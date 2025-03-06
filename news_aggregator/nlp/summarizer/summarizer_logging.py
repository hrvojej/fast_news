# summarizer_logging.py
"""
Module for setting up logging for the article summarization system.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import sys
from datetime import datetime
import uuid

# Constants
DEFAULT_LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DIR = 'logs'

def setup_log_directory():
    """Create log directory if it doesn't exist."""
    if not os.path.exists(LOG_DIR):
        try:
            os.makedirs(LOG_DIR)
        except Exception as e:
            print(f"Error creating log directory: {e}", file=sys.stderr)
            return False
    return True

def get_logger(name, log_level=None):
    """
    Get or create a logger with the specified name and level.
    
    Args:
        name (str): The name of the logger
        log_level (str, optional): The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        logging.Logger: A configured logger instance
    """
    # Convert string log level to logging constant
    if log_level is None:
        log_level = os.environ.get('LOG_LEVEL', DEFAULT_LOG_LEVEL)
    
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = getattr(logging, DEFAULT_LOG_LEVEL)
    
    # Create logger
    logger = logging.getLogger(name)
    if logger.handlers:  # Logger already exists and has handlers
        return logger
    
    logger.setLevel(numeric_level)
    logger.propagate = False  # Don't pass messages to ancestor loggers
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_format = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # Create file handler if log directory exists
    if setup_log_directory():
        try:
            # Generate a unique log file name
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            log_filename = f"{os.path.basename(name)}_{timestamp}_{unique_id}.log"
            log_path = os.path.join(LOG_DIR, log_filename)
            
            # Create rotating file handler (10 MB max size, 5 backup files)
            file_handler = RotatingFileHandler(
                log_path, 
                maxBytes=10*1024*1024,  # 10 MB
                backupCount=5
            )
            file_handler.setLevel(numeric_level)
            file_format = logging.Formatter(LOG_FORMAT)
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)
            
            # Log the startup of the logger
            logger.info(f"Logging initialized to file: {log_path}")
            
        except Exception as e:
            # Log the error to console only
            logger.error(f"Failed to create file handler: {e}")
    
    return logger

# Testing function
def test_logger():
    """Test the logger setup."""
    logger = get_logger(__name__, 'DEBUG')
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
if __name__ == "__main__":
    test_logger()