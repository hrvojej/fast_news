from typing import Optional, Dict, Any
import requests
import random
from urllib.parse import urlparse
from .rate_limiter import rate_limiter
from .retry_manager import retry_manager
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class RequestManager:
    def __init__(self):
        self._session = requests.Session()

    def _get_random_headers(self) -> Dict[str, str]:
        return {
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36'
            ]),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        }

    def get(self, url: str, **kwargs) -> requests.Response:
        @retry_manager(max_attempts=3, delay=2.0, backoff=2.0)
        def _get():
            domain = urlparse(url).netloc
            rate_limiter.wait_if_needed(domain)
            headers = self._get_random_headers()
            if 'headers' in kwargs:
                headers.update(kwargs.pop('headers'))
            response = self._session.get(url, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        return _get()

    def post(self, url: str, **kwargs) -> requests.Response:
        @retry_manager(max_attempts=3, delay=2.0, backoff=2.0)
        def _post():
            domain = urlparse(url).netloc
            rate_limiter.wait_if_needed(domain)
            headers = self._get_random_headers()
            if 'headers' in kwargs:
                headers.update(kwargs.pop('headers'))
            response = self._session.post(url, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        return _post()

    def close(self) -> None:
        self._session.close()

request_manager = RequestManager()