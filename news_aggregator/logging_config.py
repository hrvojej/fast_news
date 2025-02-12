# logging_config.py
import os
import logging
from logging.handlers import RotatingFileHandler

def setup_script_logging(script_file, log_level=logging.DEBUG, max_bytes=50 * 1024):
    """
    Set up logging for a script.

    Args:
        script_file (str): __file__ from the calling script.
        log_level (int): Logging level (default: logging.DEBUG).
        max_bytes (int): Maximum size in bytes of the log file before truncation.
        
    Returns:
        Logger object configured with a file handler and console handler.
    """
    # Use os.getcwd() to get the directory where the script is executed.
    # If you prefer the log file to be stored next to the script file, use:
    #   log_dir = os.path.dirname(os.path.abspath(script_file))
    log_dir = os.getcwd()
    
    # Use the script's base name to create a unique log file name.
    script_name = os.path.splitext(os.path.basename(script_file))[0]
    log_file = os.path.join(log_dir, f"{script_name}.log")
    
    # Create or retrieve a logger unique to this script.
    logger = logging.getLogger(script_name)
    logger.setLevel(log_level)
    
    # Prevent duplicate handlers if the logger is already configured.
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Define a common formatter.
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create a RotatingFileHandler that overwrites the file once max_bytes is reached.
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=0
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Optionally, add a console handler.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Add handlers to the logger.
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log a startup message.
    logger.info(f"Logging configured for {script_name}. Log file: {log_file}")
    
    return logger
