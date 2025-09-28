"""
Retry utilities using tenacity for resilient operations
"""
import logging
from typing import Any, Callable, Optional, Type, Union
from tenacity import (
    retry,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential,
    wait_fixed,
    retry_if_exception_type,
    before_log,
    after_log,
    retry_if_result
)

logger = logging.getLogger(__name__)


def retry_on_failure(
    max_attempts: int = 3,
    wait_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
    max_wait: float = 60.0,
    exceptions: tuple = (Exception,),
    logger: Optional[logging.Logger] = None
) -> Callable:
    """
    Decorator for retrying operations on failure

    Args:
        max_attempts: Maximum number of retry attempts
        wait_seconds: Initial wait time between retries
        backoff_multiplier: Exponential backoff multiplier
        max_wait: Maximum wait time between retries
        exceptions: Tuple of exception types to retry on
        logger: Logger instance for retry logging
    """
    log = logger or logging.getLogger(__name__)

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=wait_seconds,
            max=max_wait,
            exp_base=backoff_multiplier
        ),
        retry=retry_if_exception_type(exceptions),
        before=before_log(log, logging.DEBUG),
        after=after_log(log, logging.DEBUG),
        reraise=True
    )


def retry_on_condition(
    condition_func: Callable[[Any], bool],
    max_attempts: int = 3,
    wait_seconds: float = 1.0,
    exceptions: tuple = (Exception,),
    logger: Optional[logging.Logger] = None
) -> Callable:
    """
    Decorator for retrying operations based on result condition

    Args:
        condition_func: Function that returns True if retry should happen
        max_attempts: Maximum number of retry attempts
        wait_seconds: Wait time between retries
        exceptions: Tuple of exception types to retry on
        logger: Logger instance for retry logging
    """
    log = logger or logging.getLogger(__name__)

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_fixed(wait_seconds),
        retry=retry_if_result(condition_func) | retry_if_exception_type(exceptions),
        before=before_log(log, logging.DEBUG),
        after=after_log(log, logging.DEBUG),
        reraise=True
    )


def retry_with_timeout(
    max_attempts: int = 3,
    timeout_seconds: float = 30.0,
    wait_seconds: float = 1.0,
    exceptions: tuple = (Exception,),
    logger: Optional[logging.Logger] = None
) -> Callable:
    """
    Decorator for retrying operations with overall timeout

    Args:
        max_attempts: Maximum number of retry attempts
        timeout_seconds: Overall timeout for all attempts
        wait_seconds: Wait time between retries
        exceptions: Tuple of exception types to retry on
        logger: Logger instance for retry logging
    """
    log = logger or logging.getLogger(__name__)

    return retry(
        stop=stop_after_delay(timeout_seconds),
        wait=wait_fixed(wait_seconds),
        retry=retry_if_exception_type(exceptions),
        before=before_log(log, logging.DEBUG),
        after=after_log(log, logging.DEBUG),
        reraise=True
    )


# Pre-configured retry decorators for common use cases
db_retry = retry_on_failure(
    max_attempts=3,
    wait_seconds=0.5,
    backoff_multiplier=2.0,
    max_wait=10.0,
    exceptions=(Exception,),  # Could be more specific for DB exceptions
    logger=logger
)

api_retry = retry_on_failure(
    max_attempts=3,
    wait_seconds=1.0,
    backoff_multiplier=1.5,
    max_wait=30.0,
    exceptions=(Exception,),  # Could be more specific for API exceptions
    logger=logger
)

search_retry = retry_on_failure(
    max_attempts=2,
    wait_seconds=0.5,
    backoff_multiplier=2.0,
    max_wait=5.0,
    exceptions=(Exception,),  # Could be more specific for search exceptions
    logger=logger
)

cache_retry = retry_on_failure(
    max_attempts=2,
    wait_seconds=0.1,
    backoff_multiplier=1.5,
    max_wait=2.0,
    exceptions=(Exception,),  # Could be more specific for cache exceptions
    logger=logger
)


class RetryableOperation:
    """Context manager for retryable operations"""

    def __init__(
        self,
        operation_name: str,
        max_attempts: int = 3,
        wait_seconds: float = 1.0,
        exceptions: tuple = (Exception,),
        logger: Optional[logging.Logger] = None
    ):
        self.operation_name = operation_name
        self.max_attempts = max_attempts
        self.wait_seconds = wait_seconds
        self.exceptions = exceptions
        self.logger = logger or logging.getLogger(__name__)
        self.attempt = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type and issubclass(exc_type, self.exceptions):
            self.attempt += 1
            if self.attempt < self.max_attempts:
                self.logger.warning(
                    f"Operation '{self.operation_name}' failed (attempt {self.attempt}/{self.max_attempts}), "
                    f"retrying in {self.wait_seconds}s: {exc_val}"
                )
                import asyncio
                await asyncio.sleep(self.wait_seconds)
                # Return False to propagate the exception and retry
                return False

            self.logger.error(
                f"Operation '{self.operation_name}' failed after {self.max_attempts} attempts: {exc_val}"
            )

        return False  # Don't suppress the exception


# Utility functions for common retry patterns
async def with_retry(
    func: Callable,
    *args,
    max_attempts: int = 3,
    wait_seconds: float = 1.0,
    exceptions: tuple = (Exception,),
    **kwargs
) -> Any:
    """
    Execute a function with retry logic

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        max_attempts: Maximum number of retry attempts
        wait_seconds: Wait time between retries
        exceptions: Tuple of exception types to retry on
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function call
    """
    import asyncio

    for attempt in range(max_attempts):
        try:
            return await func(*args, **kwargs)
        except exceptions as e:
            if attempt == max_attempts - 1:
                raise

            logger.warning(
                f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                f"Retrying in {wait_seconds}s..."
            )
            await asyncio.sleep(wait_seconds)
            # Exponential backoff
            wait_seconds *= 2


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable

    Args:
        error: The exception that occurred

    Returns:
        True if the error is retryable, False otherwise
    """
    # Define retryable error patterns
    retryable_errors = (
        ConnectionError,
        TimeoutError,
        OSError,  # Includes network-related OS errors
    )

    # Check for specific error types
    if isinstance(error, retryable_errors):
        return True

    # Check for specific error messages (could be expanded)
    error_msg = str(error).lower()
    retryable_messages = [
        'connection refused',
        'connection reset',
        'timeout',
        'temporary failure',
        'service unavailable',
        'too many requests',
        'rate limit'
    ]

    return any(msg in error_msg for msg in retryable_messages)