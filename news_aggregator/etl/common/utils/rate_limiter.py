from typing import Dict, Optional
import time
from collections import deque
from datetime import datetime
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class RateLimiter:
    """Controls request rates for different domains."""
    
    def __init__(self):
        self.requests: Dict[str, deque] = {}
        self.limits: Dict[str, int] = {
            'default': {'requests': 60, 'period': 60},  # 60 requests per minute
            'nytimes.com': {'requests': 4000, 'period': 86400},  # 4000 per day
            'api.bbc.com': {'requests': 30, 'period': 60},  # 30 per minute
            'api.cnn.com': {'requests': 100, 'period': 60},  # 100 per minute
            'api.theguardian.com': {'requests': 500, 'period': 60}  # 500 per minute
        }
        
    def wait_if_needed(self, domain: str) -> None:
        """Wait if rate limit would be exceeded."""
        current_time = time.time()
        limit_config = self.limits.get(domain, self.limits['default'])
        period = limit_config['period']
        max_requests = limit_config['requests']
        
        if domain not in self.requests:
            self.requests[domain] = deque()
            
        # Remove old requests
        while self.requests[domain] and current_time - self.requests[domain][0] > period:
            self.requests[domain].popleft()
            
        # If we've reached the limit, wait
        if len(self.requests[domain]) >= max_requests:
            wait_time = self.requests[domain][0] + period - current_time
            if wait_time > 0:
                logger.info(f"Rate limit reached for {domain}. Waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                
        # Add current request
        self.requests[domain].append(current_time)

    def set_limit(self, domain: str, requests: int, period: int) -> None:
        """Set custom rate limit for a domain."""
        self.limits[domain] = {'requests': requests, 'period': period}

# Singleton instance
rate_limiter = RateLimiter()
