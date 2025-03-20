Below is an updated version of your README with the necessary changes. In this version, we explicitly state that the summarization is done via the Gemini API while image retrieval is now handled using the Wikimedia Commons API. We removed any misleading references to image fetching via Gemini API and adjusted the key features and documentation accordingly.

# Remove all items in curret folder:
Remove-Item -Path * -Recurse -Force


---
# venv
C:\Users\Korisnik\Desktop\TLDR\venv\Scripts\Activate.ps1
cd C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\nlp\summarizer
python main.py --schema pt_nyt --env dev --article-id "0078e4d3-5782-4c73-a6ae-d791e7d8e914"
python main.py --schema pt_nyt --env dev --limit 200


# Update change in local frontend to CloudFlare
cd C:\Users\Korisnik\Desktop\TLDR\fast_news\news_aggregator\frontend
pwsh -ExecutionPolicy Bypass -File update-site.ps1

```markdown
# Article Summarization System

```bash
python main.py --schema pt_nyt --env dev --article-id "0078e4d3-5782-4c73-a6ae-d791e7d8e914"
```

A modular system for summarizing articles using the Gemini API for generating summaries and the Wikimedia Commons API for retrieving images.

## Overview

This system processes articles from a database, generates summaries using the Gemini API, and enriches the output with relevant images fetched from the Wikimedia Commons API. It features a modular architecture with clear separation of concerns and robust error handling.

## Key Features

- Modular design with separate components for summarization, image retrieval, HTML generation, and database interactions.
- Robust error handling and logging.
- Support for batch and continuous processing.
- HTML output generation that integrates text summaries (via Gemini API) and images (via Wikimedia Commons).
- Process monitoring and statistics.
- Unit tests for reliability.

## Installation and Setup

### Prerequisites

- Python 3.8 or later
- PostgreSQL database with article data
- Gemini API key (for generating summaries)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/article-summarizer.git
cd article-summarizer
```

### Step 2: Install Dependencies

Install the package and its dependencies in development mode:

```bash
pip install -e .
```

### Step 3: Configure Environment Variables

Create a `.env` file in the project root or set environment variables directly:

```bash
# Create .env file
echo "GEMINI_API_KEY=your_api_key_here" > .env
echo "LOG_LEVEL=INFO" >> .env

# Or set environment variables directly
export GEMINI_API_KEY="your_api_key_here"
export LOG_LEVEL="INFO"  # Use DEBUG for verbose logging
```

### Step 4: Verify Database Connection

Ensure your database connection is properly configured:

```bash
# Check database connection
python -c "from db_scripts.db_context import DatabaseContext; print(DatabaseContext.get_instance('dev').test_connection())"
```

## Complete Usage Guide

### Basic Operations

#### 1. Checking System Status and Database Statistics

Before running any summarization tasks, check the current status:

```bash
# View summarization statistics
python main.py --schema pt_nyt --env dev --stats

# Expected output:
# === Article Summarization Statistics ===
# Schema: pt_nyt
# Environment: dev
# Total articles: 3379
# Summarized articles: 479
# Remaining articles: 2900
# Completion: 14.18%
# =========================================
```

#### 2. Running a Test in Debug Mode

Run a small test with debug mode to ensure everything works without making actual API calls:

```bash
# Process 2 articles in debug mode
python main.py --schema pt_nyt --env dev --limit 2 --debug --verbose

# This will:
# - Load 2 articles from the database
# - Generate mock summaries without calling the API
# - Save HTML output files
# - Log detailed information about the process
```

#### 3. Processing a Single Article

Process a specific article by its ID:

```bash
# Process a single article
python main.py --schema pt_nyt --env dev --article-id "3b9c8262-8578-4db6-bff3-de2232df22e5"

# This will:
# - Retrieve the specific article from the database
# - Generate a summary using the Gemini API
# - Update the article's record in the database
# - Save an HTML file with the summary and associated images from Wikimedia Commons
```

### Batch Processing

#### 4. Processing a Batch of Articles

Process a specified number of articles in a single run:

```bash
# Process 20 articles
python main.py --schema pt_nyt --env dev --limit 20
python main.py --schema pt_nyt --env dev --limit 100


# This will:
# - Retrieve up to 20 articles from the database
# - Generate summaries using the Gemini API
# - Update the database with the summaries
# - Save HTML files enriched with images fetched from Wikimedia Commons
# - Display progress information
```

#### 5. Customizing Batch Size

Control how many articles are processed in each batch:

```bash
# Process 50 articles with a batch size of 10
python main.py --schema pt_nyt --env dev --limit 50 --batch-size 10

# This will process 50 articles in 5 batches of 10 articles each
```

### Continuous Processing

#### 6. Running in Continuous Mode

Process articles continuously at regular intervals:

```bash
# Run continuously with 1-hour intervals
python main.py --schema pt_nyt --env dev --continuous --interval 3600

# This will:
# - Process a batch of articles (default batch size: 10)
# - Wait for 1 hour (3600 seconds)
# - Process the next batch
# - Continue indefinitely until interrupted (Ctrl+C)
```

#### 7. Continuous Processing with Custom Settings

Customize the continuous processing behavior:

```bash
# Run continuously with custom batch size and interval
python main.py --schema pt_nyt --env dev --continuous --batch-size 5 --interval 1800

# This will process 5 articles every 30 minutes (1800 seconds)
```

### Advanced Options

#### 8. Customizing Output

Specify a custom output directory for HTML files:

```bash
# Save HTML files to a custom directory
python main.py --schema pt_nyt --env dev --limit 10 --output-dir "/path/to/custom/directory"
```

Skip HTML generation if you only need database updates:

```bash
# Skip HTML file generation
python main.py --schema pt_nyt --env dev --limit 10 --skip-html
```

#### 9. Dry Run Mode

Test the process without making any changes to the database:

```bash
# Perform a dry run
python main.py --schema pt_nyt --env dev --limit 10 --dry-run

# This will process articles but won't update the database
```

#### 10. Force Regeneration

Force regeneration of summaries even if they already exist:

```bash
# Force regeneration of summaries
python main.py --schema pt_nyt --env dev --limit 10 --force
```

#### 11. Running with Verbose Logging

Enable detailed logging for troubleshooting:

```bash
# Enable verbose logging
python main.py --schema pt_nyt --env dev --limit 10 --verbose

# This will:
# - Set logging level to DEBUG
# - Show detailed information about each processing step
# - Log API request and response details
```

### Monitoring and Maintenance

#### 12. Checking Processing Metrics

After processing articles, review the metrics:

```bash
# View process metrics
python -c "from summarizer_monitoring import process_metrics; print(process_metrics.get_progress())"
```

#### 13. Running Tests

Run the test suite to ensure everything is working:

```bash
# Run all tests
python -m unittest summarizer_tests.py

# Run specific test modules
python -m unittest summarizer_tests.TestPromptModule
python -m unittest summarizer_tests.TestHtmlModule
```

### Using Individual Modules

#### 14. Using the HTML Processing Module

For standalone HTML processing:

```bash
# Clean and normalize HTML content from a file
python -c "from summarizer_html import clean_and_normalize_html; with open('sample.html', 'r') as f: print(clean_and_normalize_html(f.read()))"
```

#### 15. Testing API Connectivity

Test your connection to the Gemini API:

```bash
# Test API connection
python -c "from summarizer_api import test_api_call; print(test_api_call())"
```

## Module Structure

- **summarizer_core.py**: Main orchestration logic
- **summarizer_prompt.py**: Prompt creation for the language model (text summaries only)
- **summarizer_api.py**: API interaction with Gemini (for summarization)
- **summarizer_html.py**: HTML processing and output
- **summarizer_db.py**: Database interactions
- **summarizer_logging.py**: Logging configuration
- **summarizer_config.py**: Configuration management
- **summarizer_error.py**: Error handling
- **summarizer_monitoring.py**: Process monitoring
- **summarizer_tests.py**: Unit tests
- **summarizer_cli.py**: Command-line interface
- **main.py**: Main entry point

## Image Handling

Image retrieval is now managed by a dedicated module that uses the Wikimedia Commons API. This module:
- Searches for freely usable images based on article keywords or title.
- Determines the number of images to fetch based on the article's content length.
- Downloads images and integrates them into the HTML output.
  
The image-related functionality is fully decoupled from the text summarization prompt, ensuring Gemini API is used solely for generating summaries.

## Troubleshooting

### Common Issues and Solutions

1. **API Key Issues**:
   ```bash
   # Check if your API key is properly set
   python -c "import os; print(os.environ.get('GEMINI_API_KEY'))"
   ```

2. **Database Connection Problems**:
   ```bash
   # Test database connection with detailed error information
   python -c "from db_scripts.db_context import DatabaseContext; DatabaseContext.get_instance('dev').test_connection(verbose=True)"
   ```

3. **Error Log Review**:
   ```bash
   # View recent errors
   python -c "from summarizer_error import error_handler; print(error_handler.get_errors(limit=5))"
   ```

4. **Reset Metrics**:
   ```bash
   # Reset processing metrics
   python -c "from summarizer_monitoring import process_metrics; process_metrics.reset(); process_metrics.save_metrics()"
   ```

---

This updated README clarifies that text summarization is handled by the Gemini API while image retrieval is now performed via the Wikimedia Commons API. Let me know if you need further changes or additional sections!


#### 14. Skip Recently Processed Articles

To avoid re‑processing articles that have been summarized recently, you can specify a timeout (in hours):

```bash
python main.py --schema pt_nyt --env dev --limit 20 --recent-timeout 6
