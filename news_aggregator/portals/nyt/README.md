# NYT Portal Package

This package contains modules for fetching and processing New York Times content as part of the news aggregator system.

## Components

### RSS Categories Parser

The `rss_categories_parser.py` module provides functionality to fetch and store NYT RSS feed categories. It uses SQLAlchemy ORM and integrates with the project's multi-schema architecture.

#### Features

- Fetches RSS feeds from NYT's RSS directory
- Parses feed metadata
- Stores categories in portal-specific schema
- Uses ltree for hierarchical category structure
- Proper error handling and logging
- Database connection management

#### Usage

1. Ensure the NYT portal is configured in the `news_portals` table and note its UUID.

2. Update the `NYT_PORTAL_ID` in the script with the correct UUID.

3. Run the parser:

```python
from news_aggregator.portals.nyt import NYTRSSCategoriesParser

# Initialize parser with portal ID
parser = NYTRSSCategoriesParser(portal_id="your-nyt-portal-uuid")

# Run the parser
parser.run()
```

Or run directly from command line:

```bash
python rss_categories_parser.py
```

#### Configuration

The parser uses the project's database context management and supports different environments:

```python
# Use production environment
parser = NYTRSSCategoriesParser(
    portal_id="your-nyt-portal-uuid",
    env="prod"
)
```

## Development

### Adding New Features

When adding new features:

1. Create a new module in this directory
2. Update `__init__.py` to expose new components
3. Add tests in the `tests` directory
4. Update this README with documentation

### Testing

Setup and run the test suite:

```bash
# From the news_dagster-etl/news_aggregator directory
pip install -r tests/requirements.txt  # Install test dependencies

# Run all tests
python -m unittest tests.test_nyt_rss_parser

# Run specific test cases
python -m unittest tests.test_nyt_rss_parser.TestNYTRSSParser.test_clean_ltree
python -m unittest tests.test_nyt_rss_parser.TestNYTRSSParser.test_fetch_rss_feeds
```

The test suite includes:
- Database setup and teardown
- RSS feed fetching and parsing tests
- Category storage tests
- Full parser integration test

Requirements:
- Python 3.8+
- unittest (built-in)
- SQLAlchemy
- psycopg2-binary
- requests
- beautifulsoup4
- mock (for mocking HTTP requests)

Tests use a separate test database to avoid affecting production data. Make sure your test database is properly configured in the DatabaseContext class.

## Dependencies

- requests
- beautifulsoup4
- sqlalchemy
- psycopg2-binary

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests
4. Submit a pull request

## License

This project is part of the news aggregator system. See the main project's LICENSE file for details.