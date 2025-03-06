# summarizer_error.py
"""
Module for error handling and reporting in the article summarization system.
"""

import sys
import traceback
from datetime import datetime
import json
import os

from summarizer_logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Error types
class ErrorType:
    API_ERROR = "API_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    HTML_ERROR = "HTML_ERROR"
    FILE_ERROR = "FILE_ERROR"
    PROMPT_ERROR = "PROMPT_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

class ErrorHandler:
    """Class for handling and reporting errors."""
    
    def __init__(self, error_log_path=None):
        """
        Initialize the error handler.
        
        Args:
            error_log_path (str, optional): Path to the error log file
        """
        self.errors = []
        self.error_log_path = error_log_path or os.path.join("logs", "error_log.json")
        
        # Create the log directory if it doesn't exist
        os.makedirs(os.path.dirname(self.error_log_path), exist_ok=True)
    
    def add_error(self, error_type, error_message, article_id=None, details=None):
        """
        Add an error to the error log.
        
        Args:
            error_type (str): The type of error
            error_message (str): The error message
            article_id (str, optional): The article ID associated with the error
            details (dict, optional): Additional error details
            
        Returns:
            str: The error ID
        """
        error_id = f"ERR_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.errors)+1}"
        
        error_entry = {
            "error_id": error_id,
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": str(error_message),
            "article_id": article_id,
            "details": details or {}
        }
        
        self.errors.append(error_entry)
        logger.error(f"Error {error_id}: {error_type} - {error_message}")
        
        # Save to file
        self.save_errors()
        
        return error_id
    
    def add_exception(self, exception, error_type=None, article_id=None, details=None):
        """
        Add an exception to the error log.
        
        Args:
            exception (Exception): The exception object
            error_type (str, optional): The type of error (if not provided, inferred from exception)
            article_id (str, optional): The article ID associated with the error
            details (dict, optional): Additional error details
            
        Returns:
            str: The error ID
        """
        if error_type is None:
            error_type = self._infer_error_type(exception)
        
        # Get traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = ''.join(tb_lines)
        
        # Create details
        error_details = details or {}
        error_details.update({
            "exception_type": type(exception).__name__,
            "traceback": tb_text
        })
        
        return self.add_error(error_type, str(exception), article_id, error_details)
    
    def save_errors(self):
        """Save errors to the error log file."""
        try:
            # Load existing errors if file exists
            existing_errors = []
            if os.path.exists(self.error_log_path):
                try:
                    with open(self.error_log_path, 'r') as f:
                        existing_errors = json.load(f)
                except json.JSONDecodeError:
                    logger.warning(f"Error log file {self.error_log_path} is not valid JSON. Creating new file.")
            
            # Combine with new errors
            all_errors = existing_errors + self.errors
            
            # Write to file
            with open(self.error_log_path, 'w') as f:
                json.dump(all_errors, f, indent=2)
            
            # Reset in-memory errors
            self.errors = []
            
        except Exception as e:
            logger.error(f"Failed to save errors to log file: {e}", exc_info=True)
    
    def get_errors(self, error_type=None, article_id=None, limit=None):
        """
        Get filtered errors from the error log.
        
        Args:
            error_type (str, optional): Filter by error type
            article_id (str, optional): Filter by article ID
            limit (int, optional): Maximum number of errors to return
            
        Returns:
            list: Filtered error entries
        """
        try:
            # Load errors from file
            if os.path.exists(self.error_log_path):
                with open(self.error_log_path, 'r') as f:
                    all_errors = json.load(f)
            else:
                all_errors = []
            
            # Apply filters
            filtered_errors = all_errors
            
            if error_type:
                filtered_errors = [e for e in filtered_errors if e.get("error_type") == error_type]
            
            if article_id:
                filtered_errors = [e for e in filtered_errors if e.get("article_id") == article_id]
            
            # Sort by timestamp (newest first)
            filtered_errors.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
            
            # Apply limit
            if limit and isinstance(limit, int):
                filtered_errors = filtered_errors[:limit]
            
            return filtered_errors
            
        except Exception as e:
            logger.error(f"Failed to get errors from log file: {e}", exc_info=True)
            return []
    
    def _infer_error_type(self, exception):
        """
        Infer the error type from the exception.
        
        Args:
            exception (Exception): The exception object
            
        Returns:
            str: The inferred error type
        """
        exception_type = type(exception).__name__
        exception_module = type(exception).__module__
        
        # Infer error type based on exception class
        if "api" in exception_module.lower() or "request" in exception_module.lower():
            return ErrorType.API_ERROR
        elif "db" in exception_module.lower() or "sql" in exception_module.lower():
            return ErrorType.DATABASE_ERROR
        elif "html" in exception_module.lower() or "soup" in exception_module.lower():
            return ErrorType.HTML_ERROR
        elif "io" in exception_module.lower() or "file" in exception_module.lower():
            return ErrorType.FILE_ERROR
        elif "validation" in exception_module.lower():
            return ErrorType.VALIDATION_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR

    def get_error_summary(self):
        """
        Get a summary of errors by type.
        
        Returns:
            dict: Error counts by type
        """
        try:
            # Load errors from file
            if os.path.exists(self.error_log_path):
                with open(self.error_log_path, 'r') as f:
                    all_errors = json.load(f)
            else:
                all_errors = []
            
            # Count errors by type
            error_counts = {}
            for error in all_errors:
                error_type = error.get("error_type", ErrorType.UNKNOWN_ERROR)
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
            return {
                "total_errors": len(all_errors),
                "error_counts": error_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to get error summary: {e}", exc_info=True)
            return {
                "total_errors": 0,
                "error_counts": {},
                "error": str(e)
            }

# Global error handler instance
error_handler = ErrorHandler()

# Test function
def test_error_handler():
    """Test the error handler functionality."""
    handler = ErrorHandler()
    
    # Test adding a simple error
    handler.add_error(
        ErrorType.API_ERROR,
        "API request failed",
        "test_article_123",
        {"status_code": 500}
    )
    
    # Test adding an exception
    try:
        # Simulate an exception
        1/0
    except Exception as e:
        handler.add_exception(e, article_id="test_article_456")
    
    # Print error summary
    print(handler.get_error_summary())
    
    return True

if __name__ == "__main__":
    test_error_handler()