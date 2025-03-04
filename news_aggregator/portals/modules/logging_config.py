# logging_config.py
import os
import logging
from logging.handlers import RotatingFileHandler

def setup_script_logging(script_file, log_level=logging.DEBUG, max_bytes=50 * 1024):
    """
    Set up logging for a script.
    Args:
        script_file (str): **file** from the calling script.
        log_level (int): Logging level (default: logging.DEBUG).
        max_bytes (int): Maximum size in bytes of the log file before truncation.
       
    Returns:
        Logger object configured with a file handler and console handler.
    """
    # Get the directory containing the script file
    script_dir = os.path.dirname(os.path.abspath(script_file))
    
    # Navigate up to the project root
    project_root = os.path.abspath(os.path.join(script_dir, "../"))
    
    # Define log directory within the project
    log_dir = os.path.join(project_root, "log")
   
    # Ensure that the log directory exists.
    os.makedirs(log_dir, exist_ok=True)
   
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
   
    # Create a RotatingFileHandler with UTF-8 encoding and a safe error handler.
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=0, encoding="utf-8", errors="backslashreplace"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
   
    # Create a console handler.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
   
    # Add handlers to the logger.
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
   
    # Log a startup message.
    logger.info(f"Logging configured for {script_name}. Log file: {log_file}")
    
    # Add a debug message to verify logger is working
    logger.debug(f"Debug logging is enabled. Log directory: {log_dir}")
   
    return logger