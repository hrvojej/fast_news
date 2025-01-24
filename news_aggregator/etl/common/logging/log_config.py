import logging
import logging.config
import yaml
from pathlib import Path
from typing import Dict, Any

def setup_logging(config_path: str = "config/logging/logging_config.yaml", env: str = "development") -> None:
    """Setup logging configuration from YAML file."""
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
            logging_config = config.get(env, {})
            
            if not logging_config:
                logging.basicConfig(level=logging.INFO)
                return
                
            # Create log directories if they don't exist
            for handler in logging_config.get('handlers', {}).values():
                if 'filename' in handler:
                    log_dir = Path(handler['filename']).parent
                    log_dir.mkdir(parents=True, exist_ok=True)
            
            logging.config.dictConfig(logging_config)
            
    except Exception as e:
        logging.basicConfig(level=logging.INFO)
        logging.error(f"Error loading logging configuration: {e}")

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the specified name."""
    return logging.getLogger(name)

def set_log_level(level: str) -> None:
    """Set log level for root logger."""
    logging.getLogger().setLevel(getattr(logging, level.upper()))
