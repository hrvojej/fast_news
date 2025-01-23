from typing import Callable, Any, Optional, Type, Union, List
import time
from functools import wraps
import random
from etl.common.logging.logging_manager import logging_manager

logger = logging_manager.get_logger(__name__)

class RetryManager:
    """Handles retry logic for failed operations."""
    
    def __init__(self, 
                 max_attempts: int = 3,
                 delay: float = 1.0,
                 backoff: float = 2.0,
                 exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception):
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions if isinstance(exceptions, (list, tuple)) else [exceptions]

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 1
            current_delay = self.delay

            while attempt <= self.max_attempts:
                try:
                    return func(*args, **kwargs)
                except tuple(self.exceptions) as e:
                    if attempt == self.max_attempts:
                        logger.error(f"Final retry attempt failed: {str(e)}")
                        raise
                    
                    logger.warning(f"Attempt {attempt} failed: {str(e)}")
                    jitter = random.uniform(0, 0.1 * current_delay)
                    time.sleep(current_delay + jitter)
                    current_delay *= self.backoff
                    attempt += 1
                    
        return wrapper

retry_manager = RetryManager()
