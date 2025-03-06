# summarizer_template.py
"""
Module for template rendering using Jinja2 for the article summarization system.
"""

import os
import jinja2
from datetime import datetime

from summarizer_logging import get_logger
from summarizer_path_config import get_templates_dir, get_static_dir
from summarizer_config import get_config_value, CONFIG

# Initialize logger
logger = get_logger(__name__)

# Initialize Jinja2 environment
template_env = None

def initialize_template_environment():
    """
    Initialize the Jinja2 template environment.
    
    Returns:
        jinja2.Environment: The template environment instance
    """
    global template_env
    
    try:
        # Get configuration values
        template_dir = get_templates_dir()
        cache_templates = get_config_value(CONFIG, 'templates', 'cache_templates', True)
        
        # Create Jinja2 environment
        template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
            cache_size=100 if cache_templates else 0
        )
        
        # Add custom filters and globals
        template_env.filters["datetime_format"] = lambda dt, fmt="%Y-%m-%d %H:%M:%S": dt.strftime(fmt) if dt else ""
        template_env.globals["now"] = lambda fmt="%Y": datetime.now().strftime(fmt)
        template_env.globals["static_url"] = static_url
        
        logger.info(f"Initialized Jinja2 template environment with template directory: {template_dir}")
        return template_env
        
    except Exception as e:
        logger.error(f"Error initializing template environment: {e}", exc_info=True)
        return None

def static_url(path):
    """
    Generate a URL for a static asset.
    
    Args:
        path (str): The path to the static asset relative to the static directory
        
    Returns:
        str: The URL to the static asset
    """
    static_prefix = get_config_value(CONFIG, "static", "url_prefix", "/static/")
    return f"{static_prefix.rstrip('/')}/{path.lstrip('/')}"

def render_template(template_name, **context):
    """
    Render a template with the given context.
    
    Args:
        template_name (str): The name of the template to render
        **context: Template context variables
        
    Returns:
        str: The rendered template, or None if rendering failed
    """
    global template_env
    
    try:
        # Initialize template environment if not done already
        if template_env is None:
            template_env = initialize_template_environment()
            
        if template_env is None:
            logger.error("Template environment is not initialized")
            return None
            
        # Get the template
        template = template_env.get_template(template_name)
        
        # Render the template
        rendered = template.render(**context)
        return rendered
        
    except jinja2.exceptions.TemplateNotFound as e:
        logger.error(f"Template not found: {template_name} - {e}")
        return None
        
    except Exception as e:
        logger.error(f"Error rendering template {template_name}: {e}", exc_info=True)
        return None

def get_default_template_context():
    """
    Get the default context for templates.
    
    Returns:
        dict: The default template context
    """
    return {
        "app_name": "Article Summarizer",
        "current_year": datetime.now().year,
        "recent_articles": []  # This should be populated with actual data
    }
