import os

def create_file(file_path):
    """Creates a file and any missing parent directories."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        pass

def main():
    base_dir = 'news_portal_etl'
    
    structure = [
        # Core module
        'src/core/__init__.py',
        'src/core/base_parser.py',
        'src/core/base_fetcher.py',
        'src/core/base_processor.py',
        'src/core/base_storage.py',

        # Parsers module
        'src/parsers/__init__.py',
        'src/parsers/rss_parser.py',
        'src/parsers/html_parser.py',

        # Fetchers module
        'src/fetchers/__init__.py',
        'src/fetchers/rss_fetcher.py',
        'src/fetchers/html_fetcher.py',

        # Processors module
        'src/processors/__init__.py',
        'src/processors/category_processor.py',
        'src/processors/article_processor.py',

        # Storage module
        'src/storage/__init__.py',
        'src/storage/postgresql.py',
        'src/storage/oracle_bucket.py',

        # Portal handlers module
        'src/portal_handlers/__init__.py',
        'src/portal_handlers/nyt_handler.py',
        'src/portal_handlers/bbc_handler.py',
        'src/portal_handlers/cnn_handler.py',
        'src/portal_handlers/guardian_handler.py',

        # Utils module
        'src/utils/__init__.py',
        'src/utils/config.py',
        'src/utils/logging.py',
        'src/utils/validators.py',

        # Models module
        'src/models/__init__.py',
        'src/models/category.py',
        'src/models/article.py',

        # Scripts
        'scripts/nyt/fetch_categories.py',
        'scripts/nyt/fetch_articles.py',
        'scripts/bbc/fetch_categories.py',
        'scripts/bbc/fetch_articles.py',
        'scripts/cnn/fetch_categories.py',
        'scripts/cnn/fetch_articles.py',
        'scripts/guardian/fetch_categories.py',
        'scripts/guardian/fetch_articles.py',

        # Tests
        'tests/unit/test_parsers.py',
        'tests/unit/test_fetchers.py',
        'tests/unit/test_processors.py',
        'tests/integration/test_nyt_pipeline.py',
        'tests/integration/test_bbc_pipeline.py',

        # Config files
        'config/development.yaml',
        'config/production.yaml',

        # Root files
        'requirements.txt',
        'setup.py',
        'README.md'
    ]

    for relative_path in structure:
        create_file(os.path.join(base_dir, relative_path))

if __name__ == '__main__':
    main()
    print("Folder and file structure created successfully.")
