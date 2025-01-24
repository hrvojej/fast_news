from typing import Optional, Dict, Any
import requests
import random
from urllib.parse import urlparse
from .rate_limiter import rate_limiter 
from .retry_manager import retry_manager
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class RequestManager:
    """Manages HTTP requests with rate limiting and retries."""
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
    ]

    def __init__(self):
        self._session = requests.Session()
        self.retry_decorator = retry_manager(max_attempts=3, delay=2.0, backoff=2.0)

    def _get_random_headers(self) -> Dict[str, str]:
        """Generate random headers for requests."""
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }

    @retry_manager()
    def get(self, url: str, **kwargs) -> requests.Response:
        """Perform GET request with rate limiting and retries."""
        domain = urlparse(url).netloc
        rate_limiter.wait_if_needed(domain)
        
        headers = self._get_random_headers()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))
        
        response = self._session.get(url, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    @retry_manager()
    def post(self, url: str, **kwargs) -> requests.Response:
        """Perform POST request with rate limiting and retries."""
        domain = urlparse(url).netloc
        rate_limiter.wait_if_needed(domain)
        
        headers = self._get_random_headers()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))
        
        response = self._session.post(url, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    def close(self) -> None:
        """Close the session."""
        self._session.close()

request_manager = RequestManager()
