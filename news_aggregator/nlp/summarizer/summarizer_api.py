# summarizer_api.py
"""
Module for interacting with GitHub Models CLI (gh models run) for article summarization.
Replaces the previous Google Gemini API integration.
"""

import os
import json
import time
import subprocess
import tempfile
import shutil

from summarizer_logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Default model configuration - can be overridden via set_model_config()
_model_config = {
    "model": "openai/gpt-4o-mini",
    "max_tokens": 16384,
    "temperature": 0.7,
    "top_p": 0.9,
    "system_prompt": None,
}

# Fallback models to try if the primary model fails
_fallback_models = [
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "meta/llama-4-scout-17b-16e-instruct",
    "mistral/mistral-small-2503",
]

# Cache for storing recent responses to avoid duplicate API calls
response_cache = {}

# Path to gh CLI
_gh_path = None


def _find_gh():
    """Find the gh CLI executable path."""
    global _gh_path
    if _gh_path:
        return _gh_path
    _gh_path = shutil.which("gh")
    if not _gh_path:
        # Common Windows install location
        candidate = r"C:\Program Files\GitHub CLI\gh.exe"
        if os.path.isfile(candidate):
            _gh_path = candidate
    return _gh_path


def set_model_config(model=None, max_tokens=None, temperature=None, top_p=None, system_prompt=None):
    """
    Set model configuration parameters.

    Args:
        model (str): Model name (e.g. 'openai/gpt-4o-mini', 'openai/gpt-4o').
        max_tokens (int): Maximum output tokens.
        temperature (float): Sampling temperature (0.0-2.0).
        top_p (float): Top-p sampling parameter (0.0-1.0).
        system_prompt (str): Optional system prompt.
    """
    if model is not None:
        _model_config["model"] = model
        # Update fallback list so the chosen model is tried first
        if model in _fallback_models:
            _fallback_models.remove(model)
        _fallback_models.insert(0, model)
    if max_tokens is not None:
        _model_config["max_tokens"] = int(max_tokens)
    if temperature is not None:
        _model_config["temperature"] = float(temperature)
    if top_p is not None:
        _model_config["top_p"] = float(top_p)
    if system_prompt is not None:
        _model_config["system_prompt"] = system_prompt
    logger.info(f"Model config updated: {_model_config}")


def get_model_config():
    """Return a copy of the current model configuration."""
    return dict(_model_config)


def initialize_api():
    """Verify that gh CLI is available and authenticated."""
    try:
        gh = _find_gh()
        if not gh:
            logger.error("GitHub CLI (gh) not found. Install from https://cli.github.com/")
            return False

        result = subprocess.run(
            [gh, "auth", "status"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            logger.error(f"gh auth not valid. Run 'gh auth login'. stderr: {result.stderr.strip()}")
            return False

        logger.info("GitHub CLI authenticated successfully.")
        return True
    except Exception as e:
        logger.error(f"Error initializing GitHub CLI: {e}", exc_info=True)
        return False


def _run_gh_models(model, prompt, max_tokens, temperature, top_p, system_prompt=None, timeout_seconds=180):
    """
    Execute 'gh models run' and return stdout.

    Args:
        model (str): Model identifier (e.g. 'openai/gpt-4o-mini').
        prompt (str): The user prompt text.
        max_tokens (int): Max output tokens.
        temperature (float): Temperature parameter.
        top_p (float): Top-p parameter.
        system_prompt (str): Optional system prompt.
        timeout_seconds (int): Subprocess timeout.

    Returns:
        str: The model's response text.

    Raises:
        subprocess.TimeoutExpired: If the call times out.
        RuntimeError: If the call fails.
    """
    gh = _find_gh()
    if not gh:
        raise RuntimeError("GitHub CLI (gh) not found")

    # Write prompt to a temp file to avoid shell escaping / argument length issues
    tmp_file = None
    try:
        tmp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        tmp_file.write(prompt)
        tmp_file.close()

        # Read prompt from stdin via file to avoid arg length limits
        cmd = [gh, "models", "run", model]
        cmd += ["--max-tokens", str(max_tokens)]
        cmd += ["--temperature", str(temperature)]
        cmd += ["--top-p", str(top_p)]
        if system_prompt:
            cmd += ["--system-prompt", system_prompt]

        logger.debug(f"Running: {' '.join(cmd[:6])}... (prompt in stdin from file)")

        with open(tmp_file.name, 'r', encoding='utf-8') as f:
            result = subprocess.run(
                cmd,
                stdin=f,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                encoding='utf-8',
            )

        if result.returncode != 0:
            raise RuntimeError(f"gh models run failed (exit {result.returncode}): {result.stderr.strip()}")

        return result.stdout.strip()

    finally:
        if tmp_file and os.path.isfile(tmp_file.name):
            os.unlink(tmp_file.name)


def call_llm_api(prompt, article_id, content_length, retries=2, timeout_seconds=180):
    """
    Call the LLM via GitHub Models CLI to generate a summary.

    Args:
        prompt (str): The prompt to send to the model.
        article_id (str): The ID of the article being summarized.
        content_length (int): The length of the article content.
        retries (int): Number of retry attempts per model.
        timeout_seconds (int): Timeout in seconds for each call.

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

    # Verify gh is authenticated
    if not initialize_api():
        logger.error("GitHub CLI authentication check failed")
        return None, None

    models = list(_fallback_models)
    max_tokens = _model_config["max_tokens"]
    temperature = _model_config["temperature"]
    top_p = _model_config["top_p"]
    system_prompt = _model_config.get("system_prompt")

    for model in models:
        logger.info(f"Trying model {model} for article ID {article_id}")
        for attempt in range(retries + 1):
            try:
                logger.info(f"Calling gh models run with {model} for article ID {article_id} (attempt {attempt+1}/{retries+1})")
                start_time = time.time()

                summary_text = _run_gh_models(
                    model, prompt, max_tokens, temperature, top_p,
                    system_prompt=system_prompt,
                    timeout_seconds=timeout_seconds,
                )

                elapsed_time = time.time() - start_time
                logger.info(f"API call completed in {elapsed_time:.2f} seconds")

                if summary_text:
                    raw_response_text = f"model={model}, elapsed={elapsed_time:.2f}s, length={len(summary_text)}"

                    # Cache the response
                    response_cache[cache_key] = (summary_text, raw_response_text)

                    # Clean cache if it gets too large (keep last 50 entries)
                    if len(response_cache) > 50:
                        keys = list(response_cache.keys())
                        for old_key in keys[:-50]:
                            del response_cache[old_key]

                    return summary_text, raw_response_text
                else:
                    logger.error(f"Empty response for article ID {article_id} with model {model}")

            except subprocess.TimeoutExpired as te:
                logger.error(f"Timeout for article ID {article_id} using model {model} on attempt {attempt+1}: {te}")
            except KeyboardInterrupt:
                logger.error("Execution interrupted by user (Ctrl+C). Exiting.")
                raise
            except Exception as e:
                logger.error(f"API call failed for article ID {article_id} using model {model} on attempt {attempt+1}: {e}", exc_info=True)

            if attempt < retries:
                wait_time = (attempt + 1) * 5
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

        logger.info(f"Switching to next model after {retries+1} attempts for article ID {article_id} with model {model}")

    logger.error(f"Failed to get summary after trying all models for article ID {article_id}")
    return None, None


# Backward-compatible alias so existing imports keep working
call_gemini_api = call_llm_api


# Test function
def test_api_call():
    """Test the API call with a simple prompt."""
    sample_prompt = "Summarize the following text in 3 short paragraphs: 'This is a test article about AI technology.'"
    summary_text, raw_response = call_llm_api(sample_prompt, "test_article_123", 100)

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
