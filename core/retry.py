"""Retry decorator for handling transient failures."""

import logging
import time
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: tuple = (Exception,),
):
    """Decorator for retrying failed operations with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3).
        delay: Initial delay in seconds between retries (default: 1.0).
        exceptions: Tuple of exception types to catch and retry.

    Returns:
        Decorated function with retry logic.

    Example:
        @retry_on_failure(max_attempts=3, delay=1.0)
        def fetch_data():
            # operation that might fail
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        # Last attempt failed, re-raise the exception
                        logger.error(
                            f"All {max_attempts} attempts failed for "
                            f"{func.__name__}: {e}"
                        )
                        raise

                    # Calculate exponential backoff delay
                    wait_time = delay * (2**attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for "
                        f"{func.__name__}: {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)

            return None

        return wrapper

    return decorator
