# ============================================================
# utils/rate_limiter.py — Adaptive rate limiting with backoff
# ============================================================

import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token-bucket rate limiter. Thread-safe for single-threaded use."""

    def __init__(self, requests_per_second: float):
        self.min_interval = 1.0 / requests_per_second
        self._last_call = 0.0

    def wait(self):
        now = time.monotonic()
        elapsed = now - self._last_call
        if elapsed < self.min_interval:
            sleep_for = self.min_interval - elapsed
            logger.debug(f"Rate limiter sleeping {sleep_for:.2f}s")
            time.sleep(sleep_for)
        self._last_call = time.monotonic()


def with_backoff(max_retries: int = 3, base_delay: float = 5.0):
    """
    Decorator for retrying failed requests with exponential backoff.
    Raises after max_retries consecutive failures.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed after {max_retries} attempts: {exc}")
                        raise
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed: {exc}. Retrying in {delay:.0f}s")
                    time.sleep(delay)
        return wrapper
    return decorator
