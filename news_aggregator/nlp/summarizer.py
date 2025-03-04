import sys
import os
import argparse
import time
import random
import re
import traceback
from datetime import datetime, timezone
from sqlalchemy import text
import html
import json
from bs4 import BeautifulSoup  # Added for HTML validation and cleaning

# Add package root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(current_dir, "../"))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

# Set up shared logging with increased verbosity
from portals.modules.logging_config import setup_script_logging
logger = setup_script_logging(__file__, log_level='DEBUG')  # Increase to DEBUG level

# Import database models and context
from db_scripts.models.models import create_portal_article_model, create_portal_category_model
from db_scripts.db_context import DatabaseContext

# Import Gemini API client from the new SDK
from google import genai
from google.genai import types

# Configure your API key.
API_KEY = "AIzaSyAQClE8j_yigCu8DU_1S130KX_f5denga8"
client = genai.Client(api_key=API_KEY)

NYTCategory = create_portal_category_model("pt_nyt")
NYTArticle = create_portal_article_model("pt_nyt")

# Define the output HTML directory
OUTPUT_HTML_DIR = os.path.join(current_dir, "data", "output_html")

def is_valid_html(text):
    """Improved HTML validation using BeautifulSoup"""
    if not text or not isinstance(text, str):
        return False
    try:
        # Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(text, 'html.parser')
        # Check if there's actual content after parsing
        return bool(soup.find())
    except Exception:
        return False

def clean_and_normalize_html(text):
    """Clean and normalize HTML content to ensure it's valid"""
    if not text or not isinstance(text, str):
        return f"<div>No content available</div>"
    
    # Check for code blocks in markdown format
    if "```html" in text:
        try:
            # Extract HTML from code block
            text = text.split('```html')[1].split('```')[0].strip()
        except Exception as e:
            logger.warning(f"Error extracting HTML from code block: {e}")
    
    # Remove markdown headings if present (# Title)
    text = re.sub(r'^#\s+', '', text, flags=re.MULTILINE)
    
    try:
        # Parse and clean with BeautifulSoup
        soup = BeautifulSoup(text, 'html.parser')
        cleaned_html = str(soup)
        
        # If parsing stripped all content, the HTML was invalid
        if not soup.find() or cleaned_html.strip() == "":
            # Escape and wrap in div
            return f"<div>{html.escape(text)}</div>"
        
        return cleaned_html
    except Exception as e:
        logger.warning(f"Error cleaning HTML: {e}")
        # Fallback: escape and wrap in div
        return f"<div>{html.escape(text)}</div>"

def ensure_output_directory():
    """Ensure the output directory exists and is writable"""
    if not os.path.exists(OUTPUT_HTML_DIR):
        try:
            os.makedirs(OUTPUT_HTML_DIR)
            logger.info(f"Created output directory: {OUTPUT_HTML_DIR}")
            # Test if directory is writable
            test_file = os.path.join(OUTPUT_HTML_DIR, "test_write.txt")
            with open(test_file, 'w') as f:
                f.write("Test")
            os.remove(test_file)
            logger.info(f"Output directory is writable: {OUTPUT_HTML_DIR}")
        except Exception as e:
            logger.error(f"Failed to create or write to output directory: {e}")
            raise
    else:
        logger.info(f"Output directory already exists: {OUTPUT_HTML_DIR}")
        # Test if directory is writable
        try:
            test_file = os.path.join(OUTPUT_HTML_DIR, "test_write.txt")
            with open(test_file, 'w') as f:
                f.write("Test")
            os.remove(test_file)
            logger.info(f"Output directory is writable: {OUTPUT_HTML_DIR}")
        except Exception as e:
            logger.error(f"Cannot write to output directory: {e}")
            raise

def rate_limit_sleep():
    sleep_time = random.uniform(6.0, 9.0)  # Random sleep between 6-9 seconds
    print(f"Sleeping for {sleep_time:.2f} seconds to respect rate limits.")
    time.sleep(sleep_time)

def create_filename_from_title(title, url, article_id):
    """Create a filename from the title, URL, or article_id"""
    if not title or title.strip() == '':
        # Extract the last part of URL if available
        if url:
            url_parts = url.strip('/').split('/')
            return f"{url_parts[-1][:50]}.html"
        else:
            # Use article_id if no title or URL
            return f"article_{article_id}.html"
    
    # Clean the title for a filename
    filename = re.sub(r'[^\w\s-]', '', title)  # Remove non-alphanumeric chars except spaces and hyphens
    filename = re.sub(r'\s+', '_', filename)   # Replace spaces with underscores
    filename = filename[:50]  # Limit length
    return f"{filename}.html"

def save_as_html(article_id, title, url, content, summary, response_text):
    """Save the API response as an HTML file with enhanced error handling"""
    try:
        # Clean and validate the summary HTML
        processed_summary = clean_and_normalize_html(summary)
        logger.debug(f"Processed summary (first 100 chars): {processed_summary[:100]}...")
        
        # Generate filename with fallback to article_id
        filename = create_filename_from_title(title, url, article_id)
        filepath = os.path.join(OUTPUT_HTML_DIR, filename)
        
        logger.debug(f"Preparing to save HTML to: {filepath}")
        
        # Create HTML content
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title or f'NYT Article {article_id}')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .article-meta {{ color: #777; margin-bottom: 20px; }}
        .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 30px; }}
        .api-response {{ background-color: #eef; padding: 15px; border-radius: 5px; white-space: pre-wrap; }}
        .article-content {{ border-top: 1px solid #ddd; margin-top: 30px; padding-top: 20px; }}
        .footer {{ margin-top: 30px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 0.8em; color: #777; }}
        
        /* Additional styles for colored entities */
        .named-individual {{ color: #D55E00; font-weight: bold; text-decoration: underline; }}
        .roles-categories {{ color: #0072B2; font-weight: bold; }}
        .orgs-products {{ color: #009E73; font-weight: bold; }}
        .key-actions {{ color: #CC79A7; font-weight: bold; }}
        
        /* Fix for horizontal lines */
        hr {{ border: 0; height: 1px; background-color: #ddd; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>{html.escape(title or f'NYT Article {article_id}')}</h1>
    <div class="article-meta">
        <p>Article ID: {article_id}</p>
        <p>URL: <a href="{html.escape(url or '#')}">{html.escape(url or 'N/A')}</a></p>
        <p>Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <h2>Summary</h2>
    <div class="summary">
        {processed_summary}
    </div>
    
    <h2>Raw API Response</h2>
    <div class="api-response">
        {html.escape(response_text if response_text else 'No API response available')}
    </div>
    
    <div class="article-content">
        <h2>Original Article Content</h2>
        <div>
            {html.escape(content).replace('\n', '<br>') if content else 'No content available'}
        </div>
    </div>
    
    <div class="footer">
        <p>Generated by NYT Article Summarizer using Gemini API</p>
    </div>
</body>
</html>"""
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
            f.flush()  # Ensure content is written to disk
            
        # Verify file was created
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            logger.info(f"Successfully saved HTML output to {filepath} (size: {file_size} bytes)")
            return True
        else:
            logger.error(f"File wasn't created despite no errors: {filepath}")
            return False
            
    except Exception as e:
        logger.error(f"Error saving HTML file {filepath if 'filepath' in locals() else 'unknown'}:")
        logger.error(traceback.format_exc())  # Print full traceback
        return False


class NYTArticleSummarizer:
    def __init__(self, env='dev', debug_mode=False):
        self.env = env
        self.debug_mode = debug_mode
        self.logger = logger
        self.db_context = DatabaseContext.get_instance(env)
        self.NYTArticle = NYTArticle
        self.processed_count = 0
        self.failed_count = 0
        # Ensure output directory exists and is writable
        ensure_output_directory()

    def create_prompt(self, content, article_length):
        """Create a prompt with specific instructions based on article length"""
        base_prompt = (
            "Create a focused, visually enhanced summary of the main topic from the following text using these guidelines:\n\n"
            
            "MAIN TOPIC IDENTIFICATION:\n"
            "1. Determine the central topic by analyzing the article title, introductory paragraphs, and recurring themes or keywords.\n"
            "2. Focus exclusively on the main narrative thread of the article, ignoring unrelated content that appears later.\n"
            "3. Pay attention to structural indicators that signal the end of the main article content.\n\n"
        )
        
        # For longer articles, add explicit instructions about HTML validity
        if article_length > 5000:
            base_prompt += (
                "CRITICAL FOR LONGER ARTICLES - FORMAT RESTRICTIONS:\n"
                "1. Return ONLY valid, complete HTML content with no markdown formatting.\n"
                "2. DO NOT start your response with titles or headings outside HTML tags.\n"
                "3. Ensure ALL formatting is done using HTML, not markdown formatting.\n"
                "4. Wrap your entire response in a single <div> element.\n"
                "5. Do not include ```html code blocks or any other markdown syntax.\n\n"
            )
        
        base_prompt += (
            "ENGAGING TITLE:\n"
            "1. Create an intriguing title as an H1 HTML element.\n"
            "2. The title should directly relate to the central issue or conflict in the article.\n" 
            "3. Make it compelling - it can be longer if needed and does not need to be in question format.\n"
            "4. Focus on being truly intriguing by highlighting surprising or compelling elements.\n\n"
            
            "KEYWORDS SECTION:\n"
            "1. After the title, create a section with the heading '<strong>Keywords:</strong>' (must be bold).\n"
            "2. List the 5-10 most frequently appearing significant words or phrases from the article.\n"
            "3. Present these as a comma-separated inline list in black color without bullets.\n"
            "4. End this section with a horizontal line (<hr>).\n\n"
            
            "ENTITY EXTRACTION AND CLASSIFICATION:\n"
            "1. Identify and classify all key entities in the text into these categories:\n"
            "   - NAMED INDIVIDUALS: Specific people mentioned by name\n"
            "   - ROLES & CATEGORIES: Occupations, types of people, or classifications\n"
            "   - ORGANIZATIONS & PRODUCTS: Companies, brands, product types, and services\n"
            "   - KEY ACTIONS & RELATIONSHIPS: Verbs that show important actions or relationships\n"
            "2. Track the frequency and prominence of each entity throughout the text.\n"
            "3. Rank entities within each category based on importance (determined by frequency, prominence in headlines, early mentions, etc.).\n\n"
            
            "ENTITY OVERVIEW SECTION:\n"
            "1. Create a section with heading '<strong>Entity Overview:</strong>' (must be bold)\n"
            "2. List all identified entities, organized by the four categories. Each type of entities are listed in a single row, bolded and in proper color, followed by a colon and the list of entities.\n"
            "    Example: '<strong style=\"color:#D55E00\">Named Individuals:</strong> John Smith, Jane Doe, Robert Johnson'\n"
            "3. Within each category, list entities as comma-separated values in descending order of importance/frequency.\n"
            "4. Use the same color-coding for each category in the main summary.\n"
            "5. Format as an easily scannable list with clear visual separation between categories.\n"
            "6. DO NOT use bullet points for any lists.\n"
            "7. End this section with a horizontal line (<hr>).\n\n"
            
            "SUMMARY CREATION:\n"
            "1. Create a section with heading '<strong>Summary:</strong>' (must be bold)\n"
            "2. Create a focused, engaging summary that addresses ONLY the central topic identified.\n"
            "3. Structure your summary in clear paragraphs that present key facts logically.\n"
            "4. Include important details related to the main topic: names, numbers, dates, organizations, and relationships.\n"
            "5. Format all named individuals as bold AND underlined in their designated color.\n"
            "    Example: '<strong style=\"color:#D55E00\"><u>John Smith</u></strong>'\n"
            "6. Format all other entities (roles, organizations, actions) as bold only in their designated colors.\n"
            "    Example for roles: '<strong style=\"color:#0072B2\">journalist</strong>'\n"
            "7. Use simple English terminology and avoid long, complex sentences.\n"
            "8. Keep the summary concise - no more than 300 words.\n"
            "9. End this section with a horizontal line (<hr>).\n\n"
            
            "INTERESTING FACTS SECTION:\n"
            "1. Create a section with heading '<strong>Interesting Facts:</strong>' (must be bold)\n"
            "2. List 5-10 interesting facts in bullets related to the core story that are not covered in the summary.\n"
            "3. Present each fact as a concise, simple statement on a new line.\n"
            "4. Apply the same entity formatting as in the summary section.\n"
            "5. End this section with a horizontal line (<hr>).\n\n"
            
            "LEGEND SECTION:\n"
            "1. Create a section with heading '<strong>Legend:</strong>' (must be bold)\n"
            "2. List the four entity types, each in their respective color and without any explanations in brackets:\n"
            "    - '<strong style=\"color:#D55E00\">Named Individuals</strong>'\n"
            "    - '<strong style=\"color:#0072B2\">Roles & Categories</strong>'\n"
            "    - '<strong style=\"color:#009E73\">Organizations & Products</strong>'\n"
            "    - '<strong style=\"color:#CC79A7\">Key Actions & Relationships</strong>'\n"
            "3. Present as a comma-separated inline list.\n\n"
            
            "HTML FORMATTING RULES - CRITICAL:\n"
            "1. DO NOT DOUBLE TAG ENTITIES. This is a critical error in the current output.\n"
            "2. For named individuals: Use EXACTLY '<strong style=\"color:#D55E00\"><u>Name</u></strong>' (not '<u><strong><u>').\n"
            "3. For all other entities: Use EXACTLY '<strong style=\"color:#COLOR_CODE\">entity</strong>' (no underline).\n"
            "4. Make sure there are no nested or duplicate tags (e.g., no '<u><u>' or '<strong><strong>').\n"
            "5. All HTML tags must be properly closed and nested.\n"
            "6. Present your summary as simple HTML with CSS styling that implements the color-coding system.\n"
            "7. Use these specific colors: Named Individuals (#D55E00), Roles & Categories (#0072B2), Organizations & Products (#009E73), and Actions (#CC79A7).\n"
            "8. Include horizontal lines (<hr>) between each section as specified.\n"
            "9. DO NOT include any relationship diagrams or cognitive science explanations.\n"
            "10. Keep the HTML structure simple and compact.\n\n"
            
            "FORMATTING ENFORCEMENT - CRITICAL:\n"
            "1. The formatting requirements specified above MUST be followed exactly - no exceptions.\n"
            "2. All section headings MUST be bold exactly as specified (Keywords:, Entity Overview:, Summary:, Interesting Facts:, Legend:).\n"
            "3. Entity lists MUST be comma-separated without bullets or numbering.\n"
            "4. Named individuals MUST be both bold AND underlined in their color (#D55E00) using EXACTLY this format: '<strong style=\"color:#D55E00\"><u>Name</u></strong>'.\n"
            "5. Other entities MUST be bold only (not underlined) in their respective colors using EXACTLY this format: '<strong style=\"color:#COLOR_CODE\">entity</strong>'.\n"
            "6. The summary MUST use proper paragraph structure, not lists or bullet points.\n"
            "7. Horizontal lines MUST be placed between sections as specified.\n"
            "8. There MUST NOT be any nested or duplicate HTML tags that cause rendering issues.\n"
            "9. Any deviation from these formatting requirements is unacceptable.\n\n"
            
            f"ARTICLE CONTENT:\n{content}"
        )
        
        return base_prompt

    def summarize_article(self, article_info):
        content = article_info.get('content', '').strip()
        article_id = article_info.get('article_id')
        title = article_info.get('title', '')
        url = article_info.get('url', '')
        
        if not content:
            self.logger.info("No content to summarize for article ID: %s.", article_id)
            return False
        
        # Log start marker and article content length
        self.logger.info("=== START ARTICLE ID: %s ===", article_id)
        self.logger.info(f"ARTICLE CONTENT LENGTH: {len(content)} characters")
        self.logger.debug(f"ARTICLE CONTENT PREVIEW:\n{content[:500]}...")

        # Create the prompt using the article length-aware prompt function
        prompt = self.create_prompt(content, len(content))
        self.logger.debug(f"PROMPT PREVIEW:\n{prompt[:1000]}...")

        # Debug mode option - skip API call and use demo response
        if self.debug_mode:
            self.logger.info("DEBUG MODE: Using demo response instead of API call")
            summary_text = """<div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
    <!-- Demo summary content -->
    </div>"""
            raw_response_text = "DEBUG MODE: Demo response used instead of actual API call"
        else:
            # Try to call the API with extra error handling
            try:
                self.logger.info("Calling Gemini API for article ID: %s", article_id)
                
                # Adjust model based on article length
                model = 'gemini-2.0-flash'
                if len(content) > 15000:
                    model = 'gemini-2.0-pro'  # Use Pro model for very long content
                
                # Create basic generation config
                generation_config = types.GenerateContentConfig(
                    max_output_tokens=8192 if len(content) > 10000 else 5120,
                    temperature=0.7,
                    top_p=0.9,
                )
                
                # Check if the safety_settings parameter is supported
                try:
                    # First try creating a generation request with safety settings
                    # to see if this version of the API supports it
                    test_config = {
                        "model": model,
                        "contents": "test",
                        "generation_config": generation_config,
                    }
                    
                    # Try to add safety settings only if this version supports it
                    if hasattr(types, 'HarmCategory') and hasattr(types, 'HarmBlockThreshold'):
                        if len(content) > 10000:
                            safety_settings = {
                                types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: types.HarmBlockThreshold.BLOCK_NONE,
                                types.HarmCategory.HARM_CATEGORY_HARASSMENT: types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                                types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                                types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                            }
                            test_config["safety_settings"] = safety_settings
                    
                    # If we reach here, it means we can use safety_settings
                    response = client.generate_content(
                        model=model,
                        contents=[{"role": "user", "parts": [{"text": prompt}]}],
                        generation_config=generation_config,
                        safety_settings=safety_settings if 'safety_settings' in test_config else None,
                        stream=False,
                        request_options={
                            "timeout": 60,
                            "retry": {
                                "initial_delay": 1.0,
                                "maximum_delay": 10.0,
                                "multiplier": 1.5,
                                "total_timeout": 120.0
                            }
                        }
                    )
                    
                except TypeError as e:
                    # If we get a TypeError about safety_settings, we'll try again without it
                    if 'safety_settings' in str(e):
                        self.logger.warning("API doesn't support safety_settings parameter. Using without it.")
                        response = client.models.generate_content(
                            model=model,
                            contents=prompt,
                            generation_config=generation_config
                        )
                    else:
                        # If it's some other TypeError, re-raise it
                        raise
                
                self.logger.info(f"API Response received for article ID: {article_id}")
                self.logger.debug(f"Raw API response type: {type(response)}")
                
                # Extract the summary text from the response
                summary_text = response.text.strip() if response and hasattr(response, 'text') else None
                self.logger.debug(f"Summary text extracted: {summary_text[:200]}..." if summary_text else "None")
                
                raw_response_text = str(response)  # Save full response object as string
                
            except Exception as api_error:
                self.logger.error(f"API call failed for article ID {article_id}: {api_error}")
                self.logger.error(traceback.format_exc())
                return False

        if not summary_text:
            self.logger.error("Failed to generate summary for article ID: %s.", article_id)
            return False

        # Update the article record with the new summary
        if not self.debug_mode:  # Skip DB update in debug mode
            with self.db_context.session() as session:
                try:
                    # Use UUID for lookup if article_id is a string
                    if isinstance(article_id, str):
                        from uuid import UUID
                        article_id = UUID(article_id)
                    
                    # Get the article using the ORM
                    article_obj = session.query(self.NYTArticle).filter(
                        self.NYTArticle.article_id == article_id
                    ).first()
                    
                    if article_obj:
                        # Clean the summary before storing in database
                        cleaned_summary = clean_and_normalize_html(summary_text)
                        
                        # Update the summary field
                        article_obj.summary = cleaned_summary
                        # Also update the nlp_updated_at timestamp
                        article_obj.nlp_updated_at = datetime.now(timezone.utc)
                        # Get the title from the article object if not provided
                        if not title and hasattr(article_obj, 'title'):
                            title = article_obj.title
                        # Get the URL from the article object if not provided
                        if not url and hasattr(article_obj, 'url'):
                            url = article_obj.url
                        # Commit the transaction
                        session.commit()
                        self.logger.info("Article ID %s summary updated in the database.", article_id)
                    else:
                        self.logger.error("Article ID %s not found in the database.", article_id)
                        return False
                        
                except Exception as db_error:
                    session.rollback()
                    self.logger.error("Database error updating article ID %s: %s", article_id, db_error)
                    self.logger.error(traceback.format_exc())
                    return False

        # Save the response as an HTML file
        html_saved = save_as_html(article_id, title, url, content, summary_text, raw_response_text)
        if not html_saved:
            self.logger.error(f"Failed to save HTML output for article ID: {article_id}")
            return False

        # Log the summary with clear markers
        self.logger.info("ARTICLE SUMMARY for ID %s (first 500 chars):\n%s", article_id, 
                        summary_text[:500] + "..." if len(summary_text) > 500 else summary_text)
        self.logger.info("=== END ARTICLE ID: %s ===", article_id)
        return True


    def run(self, limit=None):
        self.logger.info("Starting NYT Article Summarizer for pt_nyt schema (debug_mode=%s).", self.debug_mode)
        
        try:
            with self.db_context.session() as session:
                query = "SELECT article_id, title, url, content FROM pt_nyt.articles"
                if limit:
                    query += f" LIMIT {limit}"
                articles = session.execute(text(query)).fetchall()

            self.logger.info("Found %d articles to process.", len(articles))

            for idx, article in enumerate(articles):
                article_info = dict(article._mapping)
                article_id = article_info.get('article_id')
                self.logger.info("[%d/%d] Processing article ID: %s.", idx+1, len(articles), article_id)
                
                try:
                    success = self.summarize_article(article_info)
                    if success:
                        self.processed_count += 1
                        self.logger.info(f"Successfully processed article {idx+1}/{len(articles)}")
                    else:
                        self.failed_count += 1
                        self.logger.error(f"Failed to process article {idx+1}/{len(articles)}")
                    
                    if not self.debug_mode:
                        rate_limit_sleep()
                    
                except Exception as e:
                    self.failed_count += 1
                    self.logger.error(f"Exception processing article ID {article_id}: {e}")
                    self.logger.error(traceback.format_exc())
                    continue
        
        except Exception as e:
            self.logger.error(f"Error in run method: {e}")
            self.logger.error(traceback.format_exc())
            raise

        self.logger.info("Summarization completed. Processed: %d, Failed: %d", self.processed_count, self.failed_count)

    parser.add_argument(
        '--debug',
        action='store_true',
        help="Run in debug mode (uses sample response instead of API call)"
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help="Limit the number of articles to process"
    )
    args = parser.parse_args()
    
    try:
        summarizer = NYTArticleSummarizer(env=args.env, debug_mode=args.debug)
        summarizer.run(limit=args.limit)
        logger.info("Article summarization completed successfully.")
    except Exception as e:
        logger.error("Script execution failed: %s", e)
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()
