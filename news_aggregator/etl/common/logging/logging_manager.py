from typing import Optional
import logging
import logging.handlers
import os
from pathlib import Path
from config.environment.environment_config_manager import config_manager

class LoggingManager:
    """Manages centralized logging configuration."""
    
    def __init__(self):
        self.config = config_manager.get_logging_config()
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging based on environment settings."""
        log_file = self.config.get('file', 'logs/news_aggregator.log')
        log_level = getattr(logging, self.config.get('level', 'INFO'))
        log_format = self.config.get('format', 
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Create logs directory if it doesn't exist
        Path(os.path.dirname(log_file)).mkdir(parents=True, exist_ok=True)

        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance with the specified name."""
        return logging.getLogger(name)

# Singleton instance
logging_manager = LoggingManager()
