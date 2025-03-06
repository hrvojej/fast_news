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
        
    # Add any other necessary directories to path
    # Example:
    # other_dir = os.path.join(parent_dir, "some_other_module")
    # if other_dir not in sys.path:
    #     sys.path.insert(0, other_dir)