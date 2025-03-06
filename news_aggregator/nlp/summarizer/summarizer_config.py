# summarizer_config.py
"""
Configuration module for the article summarization system.
"""

import os
import json
from pathlib import Path
import traceback

from summarizer_logging import get_logger

# Initialize logger
logger = get_logger(__name__)

from summarizer_path_config import configure_paths, get_output_dir, ensure_directory_exists
configure_paths()  # Still call this to set up sys.path
OUTPUT_HTML_DIR = get_output_dir()
ensure_directory_exists(OUTPUT_HTML_DIR)

# Default configuration values
DEFAULT_CONFIG = {
    "api": {
        "max_retries": 3,
        "timeout": 60,
        "default_temperature": 0.7,
        "default_top_p": 0.9
    },
    "summarization": {
        "include_images": True,
        "enable_entity_links": True,
        "enable_featured_image_search": True,  # New flag added
        "char_limit_long_article": 5000,
        "default_summary_length": "medium"
    },
    "output": {
        "save_html": True,
        "save_markdown": False,
        "save_text": False
    },
    "database": {
        "batch_size": 10,
        "update_on_success": True
    },
    "rate_limiting": {
        "min_delay": 15.0,
        "max_delay": 17.0,
        "adaptive": True
    },
    "templates": {
        "use_templates": True,
        "default_template": "article.html",
        "cache_templates": True
    },
    "static": {
        "url_prefix": "/static/"
    },
    "image_search": {
        "provider": "wikimedia",
        "short_threshold": 3000,   # Articles with fewer than 3000 characters get 1 image
        "medium_threshold": 7000,  # Articles between 3000 and 7000 characters get 2 images
        "max_images": 3            # Articles longer than 7000 characters get 3 images
    }

}



def ensure_output_directory():
    """
    Ensure the output directory exists and is writable.
    
    Returns:
        bool: True if the directory exists and is writable, False otherwise
    """
    try:
        if not os.path.exists(OUTPUT_HTML_DIR):
            os.makedirs(OUTPUT_HTML_DIR)
            logger.info(f"Created output directory: {OUTPUT_HTML_DIR}")
        
        # Test write access
        test_file = os.path.join(OUTPUT_HTML_DIR, "test_write.txt")
        with open(test_file, 'w') as f:
            f.write("Test")
        os.remove(test_file)
        
        logger.info(f"Output directory is writable: {OUTPUT_HTML_DIR}")
        return True
        
    except Exception as e:
        logger.error(f"Error with output directory: {e}")
        logger.error(traceback.format_exc())
        return False

def load_config(config_path=None):
    """
    Load configuration from a JSON file, or create default if not exists.
    
    Args:
        config_path (str, optional): Path to the configuration file
        
    Returns:
        dict: The configuration dictionary
    """
    # If no config path provided, use default in current directory
    if not config_path:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, "config.json")
    
    config = DEFAULT_CONFIG.copy()
    
    # Try to load existing config
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                # Update each section while preserving defaults for missing values
                for section, values in file_config.items():
                    if section in config:
                        config[section].update(values)
                    else:
                        config[section] = values
            logger.info(f"Loaded configuration from {config_path}")
        else:
            # Create default config file
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Created default configuration at {config_path}")
    
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        logger.error(traceback.format_exc())
    
    return config

def get_env_value(key, default=None):
    """
    Get a value from environment variables.
    
    Args:
        key (str): The environment variable name
        default: Default value if not found
        
    Returns:
        The value from environment or default
    """
    return os.environ.get(key, default)

def get_config_value(config, section, key, default=None):
    """
    Get a value from the configuration.
    
    Args:
        config (dict): The configuration dictionary
        section (str): The configuration section
        key (str): The configuration key
        default: Default value if not found
        
    Returns:
        The value from configuration or default
    """
    try:
        return config.get(section, {}).get(key, default)
    except Exception as e:
        logger.error(f"Error getting config value [{section}.{key}]: {e}")
        return default

def get_article_display_url(base_url, article_id):
    """
    Generate a display URL for viewing an article summary.
    
    Args:
        base_url (str): The base URL for the application
        article_id (str): The article ID
        
    Returns:
        str: The full URL for viewing the article summary
    """
    return f"{base_url.rstrip('/')}/articles/{article_id}/summary"

# Global configuration
CONFIG = load_config()

# Example usage of configuration
if __name__ == "__main__":
    print(f"Output HTML directory: {OUTPUT_HTML_DIR}")
    print(f"API max retries: {get_config_value(CONFIG, 'api', 'max_retries', 3)}")
    print(f"Include images: {get_config_value(CONFIG, 'summarization', 'include_images', True)}")
    print(f"Sample display URL: {get_article_display_url('https://news.example.com', '12345')}")