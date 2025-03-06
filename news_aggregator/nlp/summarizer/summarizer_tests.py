# summarizer_tests.py
"""
Unit tests for the article summarization system.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add package root to path
# Import path configuration first
from summarizer_path_config import configure_paths
configure_paths()

# Import modules to test
from summarizer_prompt import create_prompt
from summarizer_html import clean_and_normalize_html, is_valid_html
from summarizer_api import call_gemini_api
from summarizer_config import load_config
from summarizer_error import ErrorHandler, ErrorType

class TestPromptModule(unittest.TestCase):
    """Tests for the prompt creation module."""
    
    def test_create_prompt_with_valid_input(self):
        """Test creating a prompt with valid input."""
        content = "This is a test article about AI technology."
        article_length = len(content)
        
        prompt = create_prompt(content, article_length)
        
        self.assertIsNotNone(prompt)
        self.assertIsInstance(prompt, str)
        self.assertIn(content, prompt)
        self.assertIn("MAIN TOPIC IDENTIFICATION", prompt)
    
    def test_create_prompt_with_invalid_content(self):
        """Test creating a prompt with invalid content."""
        # Test with None
        prompt = create_prompt(None, 100)
        self.assertIsNone(prompt)
        
        # Test with empty string
        prompt = create_prompt("", 100)
        self.assertIsNone(prompt)
        
        # Test with non-string
        prompt = create_prompt(123, 100)
        self.assertIsNone(prompt)
    
    def test_create_prompt_with_invalid_length(self):
        """Test creating a prompt with invalid length."""
        content = "This is a test article."
        
        # Test with negative length
        prompt = create_prompt(content, -10)
        self.assertIsNone(prompt)
        
        # Test with zero length
        prompt = create_prompt(content, 0)
        self.assertIsNone(prompt)
        
        # Test with non-integer
        prompt = create_prompt(content, "100")
        self.assertIsNone(prompt)
    
    def test_create_prompt_with_long_article(self):
        """Test creating a prompt for a long article."""
        content = "This is a test article." * 300  # Create a long string
        article_length = len(content)
        
        prompt = create_prompt(content, article_length)
        
        self.assertIsNotNone(prompt)
        self.assertIsInstance(prompt, str)
        self.assertIn("CRITICAL FOR LONGER ARTICLES", prompt)
        self.assertIn(content, prompt)

class TestHtmlModule(unittest.TestCase):
    """Tests for the HTML processing module."""
    
    def test_is_valid_html(self):
        """Test HTML validation."""
        # Valid HTML
        self.assertTrue(is_valid_html("<div>Test</div>"))
        self.assertTrue(is_valid_html("<html><body><p>Test</p></body></html>"))
        
        # Invalid HTML
        self.assertFalse(is_valid_html(None))
        self.assertFalse(is_valid_html(""))
        self.assertFalse(is_valid_html(123))
    
    def test_clean_and_normalize_html(self):
        """Test HTML cleaning and normalization."""
        # Clean valid HTML
        html = "<div>Test</div>"
        cleaned = clean_and_normalize_html(html)
        self.assertEqual(cleaned, html)
        
        # Clean HTML with code blocks
        html_in_code_block = "```html\n<div>Test</div>\n```"
        cleaned = clean_and_normalize_html(html_in_code_block)
        self.assertEqual(cleaned, "<div>Test</div>")
        
        # Handle invalid input
        self.assertIn("<div>", clean_and_normalize_html(None))
        self.assertIn("<div>", clean_and_normalize_html(""))
        self.assertIn("<div>", clean_and_normalize_html(123))
        
        # Handle markdown headings
        markdown_html = "# Heading\n<div>Content</div>"
        cleaned = clean_and_normalize_html(markdown_html)
        self.assertNotIn("#", cleaned)
        self.assertIn("<div>Content</div>", cleaned)
        
        # Wrap multiple elements in a div
        multi_element_html = "<p>Para 1</p><p>Para 2</p>"
        cleaned = clean_and_normalize_html(multi_element_html)
        self.assertRegex(cleaned, r"<.*?>.*?<p>Para 1</p><p>Para 2</p>.*?</.*?>")

class TestApiModule(unittest.TestCase):
    """Tests for the API interaction module."""
    
    @patch('summarizer_api.client.models.generate_content')
    @patch('summarizer_api.initialize_api')
    def test_call_gemini_api_success(self, mock_initialize, mock_generate):
        """Test successful API call."""
        # Mock successful API response
        mock_initialize.return_value = True
        mock_response = MagicMock()
        mock_response.text = "Generated summary"
        mock_generate.return_value = mock_response
        
        prompt = "Test prompt"
        article_id = "test_123"
        content_length = 100
        
        summary, raw_response = call_gemini_api(prompt, article_id, content_length)
        
        self.assertEqual(summary, "Generated summary")
        self.assertIsNotNone(raw_response)
        mock_initialize.assert_called_once()
        mock_generate.assert_called_once()
    
    @patch('summarizer_api.client.models.generate_content')
    @patch('summarizer_api.initialize_api')
    def test_call_gemini_api_failure(self, mock_initialize, mock_generate):
        """Test failed API call."""
        # Mock failed API initialization
        mock_initialize.return_value = False
        
        prompt = "Test prompt"
        article_id = "test_123"
        content_length = 100
        
        summary, raw_response = call_gemini_api(prompt, article_id, content_length)
        
        self.assertIsNone(summary)
        self.assertIsNone(raw_response)
        mock_initialize.assert_called_once()
        mock_generate.assert_not_called()
    
    def test_call_gemini_api_invalid_input(self):
        """Test API call with invalid input."""
        # Empty prompt
        summary, raw_response = call_gemini_api("", "test_123", 100)
        self.assertIsNone(summary)
        self.assertIsNone(raw_response)
        
        # None prompt
        summary, raw_response = call_gemini_api(None, "test_123", 100)
        self.assertIsNone(summary)
        self.assertIsNone(raw_response)

class TestConfigModule(unittest.TestCase):
    """Tests for the configuration module."""
    
    def test_load_config(self):
        """Test configuration loading."""
        # Test with non-existent file (should create default)
        test_config_path = "test_config.json"
        if os.path.exists(test_config_path):
            os.remove(test_config_path)
        
        config = load_config(test_config_path)
        
        self.assertIsNotNone(config)
        self.assertIsInstance(config, dict)
        self.assertIn("api", config)
        self.assertIn("summarization", config)
        
        # Clean up
        if os.path.exists(test_config_path):
            os.remove(test_config_path)

class TestErrorModule(unittest.TestCase):
    """Tests for the error handling module."""
    
    def setUp(self):
        """Set up for tests."""
        self.error_log_path = "test_error_log.json"
        self.handler = ErrorHandler(self.error_log_path)
    
    def tearDown(self):
        """Clean up after tests."""
        if os.path.exists(self.error_log_path):
            os.remove(self.error_log_path)
    
    def test_add_error(self):
        """Test adding an error."""
        error_id = self.handler.add_error(
            ErrorType.API_ERROR,
            "Test error",
            "test_article_123",
            {"detail": "Additional information"}
        )
        
        self.assertIsNotNone(error_id)
        self.assertTrue(os.path.exists(self.error_log_path))
        
        # Get errors
        errors = self.handler.get_errors()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], ErrorType.API_ERROR)
        self.assertEqual(errors[0]["article_id"], "test_article_123")
    
    def test_add_exception(self):
        """Test adding an exception."""
        try:
            # Simulate an exception
            1/0
        except Exception as e:
            error_id = self.handler.add_exception(
                e,
                ErrorType.UNKNOWN_ERROR,
                "test_article_456"
            )
            
            self.assertIsNotNone(error_id)
            
            # Get errors
            errors = self.handler.get_errors()
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0]["error_type"], ErrorType.UNKNOWN_ERROR)
            self.assertEqual(errors[0]["article_id"], "test_article_456")
            self.assertIn("ZeroDivisionError", errors[0]["details"]["exception_type"])

if __name__ == "__main__":
    unittest.main()