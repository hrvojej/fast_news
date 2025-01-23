import os
from pathlib import Path
import sys

def create_project_structure():
    # Base project directory
    base_dir = Path('/home/opc/news_aggregator')
    
    # Main project directories
    directories = {
        'etl': {
            'portals': {
                'nyt': ['categories', 'articles'],
                'bbc': ['categories', 'articles'],
                'cnn': ['categories', 'articles'],
                'guardian': ['categories', 'articles'],
                'reuters': ['categories', 'articles'],
                'wapo': ['categories', 'articles']
            },
            'events': ['detection', 'analysis', 'management'],
            'topics': ['detection', 'classification', 'analysis'],
            'common': ['utils', 'database', 'logging']
        },
        'dagster_orchestration': {
            'jobs': ['portal_jobs', 'event_jobs', 'topic_jobs'],
            'ops': ['portal_ops', 'event_ops', 'topic_ops'],
            'resources': ['config', 'connections'],
            'schedules': ['daily', 'hourly'],
            'sensors': ['portal_sensors', 'event_sensors']
        },
        'tests': {
            'unit': ['portals', 'events', 'topics'],
            'integration': ['etl', 'dagster'],
            'e2e': []
        },
        'db_scripts': {
            'schemas': [],
            'migrations': [],
            'functions': []
        },
        'config': {
            'portals': [],
            'logging': [],
            'database': []
        },
        'logs': {
            'etl': [],
            'dagster': [],
            'errors': []
        }
    }
    
    # Initial files to create
    files = {
        'etl/common/database/db_manager.py': '',
        'etl/common/utils/helpers.py': '',
        'etl/common/logging/log_config.py': '',
        'config/portals/portal_configs.yaml': '',
        'config/logging/logging_config.yaml': '',
        'config/database/database_config.yaml': '',
        'db_scripts/schemas/create_schemas.sql': '',
        'db_scripts/schemas/events_schema.sql': '',
        'db_scripts/schemas/topics_schema.sql': '',
        'requirements.txt': '',
        '.env.example': '',
        'README.md': '',
    }

    print(f"Creating project structure in: {base_dir}")

    # Create directories
    def create_nested_dirs(parent_path, structure):
        for key, value in structure.items():
            current_path = parent_path / key
            current_path.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {current_path}")
            
            if isinstance(value, dict):
                create_nested_dirs(current_path, value)
            elif isinstance(value, list):
                for subdir in value:
                    subdir_path = current_path / subdir
                    subdir_path.mkdir(parents=True, exist_ok=True)
                    print(f"Created directory: {subdir_path}")

    # Create base directory
    base_dir.mkdir(parents=True, exist_ok=True)

    # Create directory structure
    create_nested_dirs(base_dir, directories)

    # Create files
    for file_path, content in files.items():
        full_path = base_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.touch()
        print(f"Created file: {full_path}")

if __name__ == "__main__":
    create_project_structure()