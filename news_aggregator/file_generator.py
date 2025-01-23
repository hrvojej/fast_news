#!/usr/bin/env python3
import os
import sys
import yaml
from pathlib import Path
import logging
from typing import Dict, Any, Union

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileGenerator:
    def __init__(self, base_dir: str = "/home/opc/news_dagster-etl/news_aggregator"):
        self.base_dir = Path(base_dir)
        
    def create_file(self, file_path: Path, content: str = "") -> None:
        """Create a file with given content."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open('w') as f:
                f.write(content)
            logger.info(f"Created file: {file_path}")
        except Exception as e:
            logger.error(f"Error creating file {file_path}: {e}")
            raise

    def load_file_config(self, config_file: str) -> Dict[str, Any]:
        """Load file configuration from YAML."""
        config_path = self.base_dir / 'config' / 'file_templates' / config_file
        try:
            with open(config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config {config_file}: {e}")
            raise

    def generate_files(self, config_name: str) -> None:
        """Generate files based on configuration."""
        config = self.load_file_config(config_name)
        for file_info in config['files']:
            file_path = self.base_dir / file_info['path']
            content = file_info.get('content', '')
            self.create_file(file_path, content)

def main():
    if len(sys.argv) != 2:
        print("Usage: file_generator.py <config_name>")
        sys.exit(1)
        
    generator = FileGenerator()
    generator.generate_files(sys.argv[1])

if __name__ == "__main__":
    main()