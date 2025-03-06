# summarizer_path_config.py
"""
Path configuration utility for the summarizer module.
"""

import os
import sys

def configure_paths():
    """
    Configure Python path to include necessary directories for imports.
    """
    # Add path to news_aggregator directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, "../../../"))
    news_aggregator_dir = os.path.join(parent_dir, "news_aggregator")
    if news_aggregator_dir not in sys.path:
        sys.path.insert(0, news_aggregator_dir)
        
def get_project_root():
    """Get the absolute path to the project root directory."""
    # Dynamically determine project root - UPDATED
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(current_dir, "../../../"))

def get_templates_dir():
    """Get the absolute path to the templates directory."""
    # Updated to new frontend location - UPDATED
    return os.path.join(get_project_root(), "news_aggregator", "frontend", "templates")

def get_static_dir():
    """Get the absolute path to the static files directory."""
    # Updated to new frontend location - UPDATED
    return os.path.join(get_project_root(), "news_aggregator", "frontend", "static")

def get_output_dir():
    """Get the absolute path to the output directory."""
    # Updated to new frontend location - UPDATED
    return os.path.join(get_project_root(), "news_aggregator", "frontend", "web", "articles")

def ensure_directory_exists(directory_path):
    """Ensure that a directory exists, creating it if necessary."""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
    return os.path.exists(directory_path)
