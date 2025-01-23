from typing import Dict, Any, Optional
import os
import yaml
from pathlib import Path

class EnvironmentConfigManager:
    """Manages environment-specific configurations for news aggregator."""
    
    def __init__(self, config_path: str = "config/environment/env_config.yaml"):
        self.config_path = Path(config_path)
        self.env = os.getenv("NEWS_ENV", "development")
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load environment configuration from YAML file."""
        try:
            with open(self.config_path) as f:
                all_configs = yaml.safe_load(f)
                self._config = all_configs.get(self.env, {})
        except FileNotFoundError:
            self._config = {}

    def get_database_config(self) -> Dict[str, str]:
        """Get database configuration for current environment."""
        db_config = self._config.get("database", {})
        return {
            "dbname": db_config.get("name", "news_aggregator_dev"),
            "user": db_config.get("user", "news_admin_dev"),
            "password": db_config.get("password", ""),
            "host": db_config.get("host", "localhost"),
            "port": db_config.get("port", "5432")
        }

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration for current environment."""
        return self._config.get("logging", {})

    def get_api_keys(self) -> Dict[str, str]:
        """Get API keys for current environment."""
        return self._config.get("api_keys", {})

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get specific configuration value."""
        return self._config.get(key, default)

# Singleton instance
config_manager = EnvironmentConfigManager()
