# summarizer_api.py
"""
Module for interacting with LLM backends for article summarization.
Supports two backends:
  - 'copilot'  : GitHub Copilot CLI (copilot -p) — default
  - 'gh_models': GitHub Models CLI (gh models run)
"""

import os
import json
import time
import subprocess
import shutil
import tempfile

from summarizer_logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Active backend: 'copilot' or 'gh_models'
_backend = "copilot"

# Default model configuration - can be overridden via set_model_config()
_model_config = {
    "model": "gpt-5-mini",
    "max_tokens": 16384,
    "temperature": 0.7,
    "top_p": 0.9,
    "system_prompt": None,
}

# Fallback models per backend
_fallback_models_copilot = [
    "gpt-5-mini",
    "gpt-5.2",
    "claude-sonnet-4.6",
    "claude-haiku-4.5",
]

_fallback_models_gh = [
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "meta/llama-4-scout-17b-16e-instruct",
    "mistral/mistral-small-2503",
]

# Active fallback list (set by set_backend)
_fallback_models = list(_fallback_models_copilot)

# Cache for storing recent responses to avoid duplicate API calls
response_cache = {}

# Path to gh CLI
_gh_path = None

# Path to copilot CLI
_copilot_path = None


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


def set_backend(backend):
    """
    Set the LLM backend to use.

    Args:
        backend (str): 'copilot' for GitHub Copilot CLI, 'gh_models' for GitHub Models CLI.
    """
    global _backend, _fallback_models
    if backend not in ("copilot", "gh_models"):
        raise ValueError(f"Unknown backend '{backend}'. Use 'copilot' or 'gh_models'.")
    _backend = backend
    if backend == "copilot":
        _fallback_models[:] = list(_fallback_models_copilot)
        if _model_config["model"] not in _fallback_models:
            _model_config["model"] = _fallback_models[0]
    else:
        _fallback_models[:] = list(_fallback_models_gh)
        if _model_config["model"] not in _fallback_models:
            _model_config["model"] = _fallback_models[0]
    logger.info(f"Backend set to '{_backend}', default model: {_model_config['model']}")


def get_backend():
    """Return the current backend name."""
    return _backend


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


def _find_copilot():
    """Find the copilot CLI executable path."""
    global _copilot_path
    if _copilot_path:
        return _copilot_path
    _copilot_path = shutil.which("copilot")
    if not _copilot_path:
        # VS Code bundled location
        candidate = os.path.expandvars(
            r"%APPDATA%\Code\User\globalStorage\github.copilot-chat\copilotCli\copilot.bat"
        )
        if os.path.isfile(candidate):
            _copilot_path = candidate
    return _copilot_path


def initialize_api():
    """Verify that the configured backend CLI is available and authenticated."""
    try:
        if _backend == "copilot":
            cop = _find_copilot()
            if not cop:
                logger.error("GitHub Copilot CLI (copilot) not found. Install via: winget install GitHub.Copilot")
                return False
            result = subprocess.run(
                [cop, "--version"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                logger.error(f"Copilot CLI check failed: {result.stderr.strip()}")
                return False
            logger.info(f"Copilot CLI found: {result.stdout.strip()}")
            return True
        else:
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
        logger.error(f"Error initializing API backend: {e}", exc_info=True)
        return False


def _run_copilot_cli(model, prompt, timeout_seconds=300):
    """
    Execute 'copilot -p' with a file-based prompt and return the response.

    The prompt is written to a temp file because Copilot CLI prompts are passed
    as command-line arguments (-p) and our prompts can exceed shell limits (~24KB).
    Copilot CLI reads the temp file and follows the instructions in it.

    Uses --output-format json for reliable parsing: we look for the JSONL event
    with type 'assistant.message' which contains the clean response in data.content.

    Args:
        model (str): Model name (e.g. 'gpt-5-mini', 'claude-sonnet-4.6').
        prompt (str): The full prompt text.
        timeout_seconds (int): Subprocess timeout.

    Returns:
        str: The model's response text.

    Raises:
        subprocess.TimeoutExpired: If the call times out.
        RuntimeError: If the call fails or no response is found.
    """
    cop = _find_copilot()
    if not cop:
        raise RuntimeError("Copilot CLI (copilot) not found")

    # Write prompt to temp file
    tmp_file = None
    try:
        tmp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', prefix='copilot_prompt_',
            delete=False, encoding='utf-8'
        )
        tmp_file.write(prompt)
        tmp_file.close()
        tmp_path = tmp_file.name

        meta_prompt = (
            f"Read the file '{tmp_path}' and follow the instructions in it EXACTLY. "
            "You MUST output ONLY the raw HTML that the instructions ask for — nothing else. "
            "No commentary, no markdown fences, no explanation before or after the HTML. "
            "Do NOT edit any files. Do NOT run any shell commands. Do NOT create any files."
        )

        cmd = [
            cop, "-p", meta_prompt,
            "--model", model,
            "--silent",
            "--output-format", "json",
            "--deny-tool=write",
            "--deny-tool=shell",
        ]

        logger.debug(f"Running copilot CLI: model={model}, prompt file={tmp_path} ({len(prompt)} chars)")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            encoding='utf-8',
        )

        if result.returncode != 0:
            stderr_msg = result.stderr.strip() if result.stderr else "(no stderr)"
            raise RuntimeError(f"copilot CLI failed (exit {result.returncode}): {stderr_msg}")

        # Parse JSONL output — find the LAST 'assistant.message' event with content.
        # Copilot CLI works in multi-turn: first turn is "Reading the file...",
        # subsequent turns contain the actual response. We want the last one.
        response_text = None
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if event.get("type") == "assistant.message":
                    content = event.get("data", {}).get("content", "")
                    if content:
                        response_text = content  # keep overwriting — last one wins
            except json.JSONDecodeError:
                continue

        if response_text is None:
            # Fallback: try to find the last non-empty content from message_delta events
            chunks = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if event.get("type") == "assistant.message_delta":
                        delta = event.get("data", {}).get("deltaContent", "")
                        if delta:
                            chunks.append(delta)
                except json.JSONDecodeError:
                    continue
            if chunks:
                response_text = "".join(chunks)

        if response_text is None:
            raise RuntimeError("No response found in copilot CLI output")

        return response_text.strip()

    finally:
        # Clean up temp file
        if tmp_file and os.path.exists(tmp_file.name):
            try:
                os.unlink(tmp_file.name)
            except OSError:
                pass


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

    cmd = [gh, "models", "run", model]
    # GPT-5+ and o-series models don't support max_tokens, temperature, or top_p
    _is_restricted_model = any(tag in model for tag in ["gpt-5", "/o3", "/o4"])
    if not _is_restricted_model:
        cmd += ["--max-tokens", str(max_tokens)]
        cmd += ["--temperature", str(temperature)]
        cmd += ["--top-p", str(top_p)]
    if system_prompt:
        cmd += ["--system-prompt", system_prompt]

    logger.debug(f"Running: {' '.join(cmd[:6])}... (prompt via input pipe, {len(prompt)} chars)")

    # Pass prompt via subprocess input= parameter (PIPE).
    # Note: stdin from file does NOT work with gh models run — it enters interactive mode
    # and returns just ">>> " instead of a real response. The input= parameter
    # properly pipes the prompt and closes stdin, triggering single-shot mode.
    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        encoding='utf-8',
    )

    if result.returncode != 0:
        raise RuntimeError(f"gh models run failed (exit {result.returncode}): {result.stderr.strip()}")

    return result.stdout.strip()


def call_llm_api(prompt, article_id, content_length, retries=2, timeout_seconds=180):
    """
    Call the LLM to generate a summary using the configured backend.

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

    # Verify backend is available
    if not initialize_api():
        logger.error(f"Backend '{_backend}' initialization check failed")
        return None, None

    models = list(_fallback_models)
    max_tokens = _model_config["max_tokens"]
    temperature = _model_config["temperature"]
    top_p = _model_config["top_p"]
    system_prompt = _model_config.get("system_prompt")

    # Copilot CLI needs more time for file-based prompts
    if _backend == "copilot":
        timeout_seconds = max(timeout_seconds, 300)

    for model in models:
        logger.info(f"[{_backend}] Trying model {model} for article ID {article_id}")
        for attempt in range(retries + 1):
            try:
                logger.info(f"[{_backend}] Calling {model} for article ID {article_id} (attempt {attempt+1}/{retries+1})")
                start_time = time.time()

                if _backend == "copilot":
                    summary_text = _run_copilot_cli(
                        model, prompt,
                        timeout_seconds=timeout_seconds,
                    )
                else:
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
