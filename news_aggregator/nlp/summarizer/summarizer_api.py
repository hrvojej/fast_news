# summarizer_api.py
"""
Module for interacting with the API (Gemini) for article summarization.
"""

import os
import json
import time

from google import genai
from google.genai import types
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch

from summarizer_logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# API Key should be set as an environment variable
API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyAQClE8j_yigCu8DU_1S130KX_f5denga8")
client = genai.Client(api_key=API_KEY)

# Cache for storing recent responses to avoid duplicate API calls
response_cache = {}

def initialize_api():
    """Initialize the API client with proper configuration."""
    try:
        if not API_KEY:
            logger.error("No API key found. Set the GEMINI_API_KEY environment variable.")
            return False
        
        # Test the API connection with a simple request
        response = client.models.list()
        if response:
            logger.info("Successfully connected to Gemini API.")
            return True
        else:
            logger.error("Failed to connect to Gemini API.")
            return False
    except Exception as e:
        logger.error(f"Error initializing API client: {e}", exc_info=True)
        return False

def get_model_for_content_length(content_length):
    # Always use a simpler Gemini model for faster responses
    return 'gemini-2.0-flash-001'

def create_safety_settings():
    """
    Create safety settings for the API request.
    
    Returns:
        list: List of safety settings
    """
    try:
        if hasattr(types, 'HarmCategory') and hasattr(types, 'HarmBlockThreshold'):
            return [
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                )
            ]
        return None
    except Exception as e:
        logger.error(f"Error creating safety settings: {e}")
        return None

def gemini_generate_content(model, prompt, config_kwargs):
    from google.genai import types
    # Create a new client instance for the process using the module-level API_KEY.
    client = genai.Client(api_key=API_KEY)
    # Reconstruct the config object from the configuration keyword arguments.
    config = types.GenerateContentConfig(**config_kwargs)
    return client.models.generate_content(
         model=model,
         contents=[{"role": "user", "parts": [{"text": prompt}]}],
         config=config
    )

def call_gemini_api(prompt, article_id, content_length, retries=2, timeout_seconds=180):
    """
    Call the Gemini API to generate a summary.
    
    Args:
        prompt (str): The prompt to send to the API.
        article_id (str): The ID of the article being summarized.
        content_length (int): The length of the article content.
        retries (int): Number of retry attempts for each model.
        timeout_seconds (int): Timeout in seconds for each API call.
        
    Returns:
        tuple: (summary_text, raw_response_text) or (None, None) if failed.
    """
    if not prompt:
        logger.error(f"Empty prompt for article ID {article_id}")
        return None, None

    # Check cache
    cache_key = f"{article_id}_{hash(prompt)}"
    if cache_key in response_cache:
        logger.info(f"Using cached response for article ID {article_id}")
        return response_cache[cache_key]

    # Initialize API if needed
    if not initialize_api():
        logger.error("API initialization failed")
        return None, None

    # Define the list of models to try in order
    models = [
        'gemini-2.5-pro-preview-03-25',
        'gemini-2.5-pro-exp-03-25',
        'gemini-2.0-pro-exp-02-05',
        'gemini-2.0-flash-001',
        'gemini-2.0-flash-thinking-exp-01-21',
        'gemini-2.0-flash-thinking-exp-1219',
        'gemini-2.0-flash-exp'
    ]
    
    # Configure request
    config_kwargs = {
        "max_output_tokens": 16384,
        "temperature": 0.7,
        "top_p": 0.9,
        # Removed generation_config because it is not permitted in the current GenerateContentConfig
    }

    # Add safety settings if available
    safety_settings = create_safety_settings()
    if safety_settings:
        config_kwargs["safety_settings"] = safety_settings

    # Create config object for local use (for logging errors if needed)
    try:
        config = types.GenerateContentConfig(**config_kwargs)
    except Exception as e:
        logger.error(f"Error creating config: {e}", exc_info=True)
        return None, None

    from concurrent.futures import ThreadPoolExecutor, TimeoutError


    # Loop through models and attempt retries on each
    for model in models:
        logger.info(f"Trying model {model} for article ID {article_id}")
        for attempt in range(retries + 1):
            try:
                logger.info(f"Calling Gemini API with model {model} for article ID {article_id} (attempt {attempt+1}/{retries+1})")
                start_time = time.time()
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(gemini_generate_content, model, prompt, config_kwargs)
                    try:
                        response = future.result(timeout=timeout_seconds)
                    except TimeoutError:
                        raise TimeoutError("API call timed out")

                elapsed_time = time.time() - start_time
                logger.info(f"API call completed in {elapsed_time:.2f} seconds")

                if response:
                    try:
                        summary_text = response.text.strip()
                    except AttributeError:
                        summary_text = response.candidates[0].content.parts[0].text.strip()
                    raw_response_text = str(response)

                    # Cache the response
                    response_cache[cache_key] = (summary_text, raw_response_text)

                    # Clean cache if it gets too large (keep last 50 entries)
                    if len(response_cache) > 50:
                        keys = list(response_cache.keys())
                        for old_key in keys[:-50]:
                            del response_cache[old_key]

                    return summary_text, raw_response_text
                else:
                    logger.error(f"Invalid response format for article ID {article_id} with model {model}")

            except TimeoutError as te:
                logger.error(f"Timeout error for article ID {article_id} using model {model} on attempt {attempt+1}: {te}", exc_info=True)
            except KeyboardInterrupt:
                logger.error("Execution interrupted by user (Ctrl+C). Exiting.")
                raise
            except Exception as e:
                logger.error(f"API call failed for article ID {article_id} using model {model} on attempt {attempt+1}: {e}", exc_info=True)

            if attempt < retries:
                wait_time = (attempt + 1) * 5  # Exponential backoff: 5s, 10s, etc.
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

        logger.info(f"Switching to next model after {retries+1} attempts for article ID {article_id} with model {model}")

    logger.error(f"Failed to get summary after trying all models for article ID {article_id}")
    return None, None

# Test function
def test_api_call():
    """Test the API call with a simple prompt."""
    sample_prompt = "Summarize the following text in 3 short paragraphs: 'This is a test article about AI technology.'"
    summary_text, raw_response = call_gemini_api(sample_prompt, "test_article_123", 100)
    
    if summary_text:
        logger.info(f"Test API call successful. Summary: {summary_text}")
        return True
    else:
        logger.error("Test API call failed.")
        return False

if __name__ == "__main__":
    try:
        test_api_call()
    except KeyboardInterrupt:
        logger.info("Script execution terminated by user (Ctrl+C).")
