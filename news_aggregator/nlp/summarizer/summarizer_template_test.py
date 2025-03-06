# summarizer_template_test.py
"""
Test module for the template rendering system.
"""

import os
from summarizer_template import initialize_template_environment, render_template, get_default_template_context
from summarizer_path_config import get_output_dir, ensure_directory_exists

def test_template_rendering():
    """Test the template rendering functionality."""
    # Initialize the template environment
    env = initialize_template_environment()
    
    if env is None:
        print("Failed to initialize template environment")
        return False
    
    # Get default context and add test values
    context = get_default_template_context()
    context.update({
        'title': 'Test Page',
        'content': '<p>This is test content.</p>'
    })
    
    # Try rendering a simple template
    rendered = render_template("base.html", **context)
    
    if rendered is None:
        print("Failed to render template")
        return False
    
    print("Template rendering test successful")
    print(f"Rendered length: {len(rendered)} characters")
    
    # Ensure output directory exists
    output_dir = get_output_dir()
    ensure_directory_exists(output_dir)
    
    # Save the rendered template to a file for inspection
    test_output_path = os.path.join(output_dir, "template_test.html")
    with open(test_output_path, "w", encoding="utf-8") as f:
        f.write(rendered)
    
    print(f"Saved test output to {test_output_path}")
    return True

if __name__ == "__main__":
    test_template_rendering()
