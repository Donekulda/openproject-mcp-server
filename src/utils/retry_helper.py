"""
Retry helper utilities with exponential backoff for handling transient failures.

This module provides retry decorators and utilities for automatically retrying
failed async operations with exponential backoff strategy, particularly useful
for handling network timeouts and transient errors in bulk operations.

Based on code from haunguyendev (https://github.com/haunguyendev)
Fork: https://github.com/haunguyendev/openproject-mcp-server/tree/main (commit 28f097a)
"""


import asyncio
import logging
from typing import Callable, Tuple, Type, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


async def retry_with_exponential_backoff(
    func: Callable,
    *args,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 16.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    **kwargs
) -> Any:
    """Execute async function with exponential backoff retry strategy.
    
    This function automatically retries failed async operations with increasing
    delays between attempts. Only retries for specified exception types (typically
    network/timeout errors), avoiding unnecessary retries for client errors (4xx).
    
    Retry delays follow exponential backoff:
    - Attempt 1: initial_delay (default 1s)
    - Attempt 2: initial_delay * base (default 2s)
    - Attempt 3: initial_delay * base^2 (default 4s)
    - Attempt 4: initial_delay * base^3 (default 8s)
    - Maximum delay is capped at max_delay
    
    Args:
        func: Async function to retry
        *args: Positional arguments to pass to func
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds between retries (default: 1.0)
        max_delay: Maximum delay in seconds (default: 16.0)
        exponential_base: Base for exponential backoff calculation (default: 2.0)
        retryable_exceptions: Tuple of exception types to retry. If None, defaults to
                            common network/timeout exceptions
        **kwargs: Keyword arguments to pass to func
        
    Returns:
        Result from successful function execution
        
    Raises:
        Exception: The last exception if all retry attempts are exhausted
        
    Example:
        >>> async def fetch_data():
        ...     # May fail with network error
        ...     return await client.get("/api/data")
        >>> result = await retry_with_exponential_backoff(
        ...     fetch_data,
        ...     max_retries=3,
        ...     initial_delay=1.0
        ... )
    """

    # Import here to avoid circular dependencies
    import aiohttp
    
    # Default retryable exceptions: network and timeout errors
    if retryable_exceptions is None:
        retryable_exceptions = (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            ConnectionError,
            OSError,  # Covers network-related OS errors
        )
    
    last_exception = None
    
    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Log success if this was a retry
            if attempt > 0:
                logger.info(
                    f"✅ Retry successful on attempt {attempt + 1}/{max_retries + 1}"
                )
            
            return result
            
        except Exception as e:
            last_exception = e
            
            # Check if this exception is retryable
            if not isinstance(e, retryable_exceptions):
                # Non-retryable exception (e.g., 4xx client errors)
                logger.debug(f"Non-retryable exception: {type(e).__name__}: {str(e)}")
                raise
            
            # Check if we have retries left
            if attempt >= max_retries:
                # Out of retries
                logger.warning(
                    f"❌ All {max_retries} retry attempts exhausted. "
                    f"Final error: {type(e).__name__}: {str(e)}"
                )
                raise
            
            # Calculate delay with exponential backoff
            delay = min(initial_delay * (exponential_base ** attempt), max_delay)
            
            logger.info(
                f"🔄 Attempt {attempt + 1}/{max_retries + 1} failed: {type(e).__name__}: {str(e)}"
            )
            logger.info(f"   Retrying in {delay:.1f}s...")
            
            # Wait before retry
            await asyncio.sleep(delay)
    
    # Should never reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry logic error: no result and no exception")


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 16.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
):
    """Decorator to add retry logic with exponential backoff to async functions.
    
    This is a convenience decorator wrapper around retry_with_exponential_backoff.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds between retries (default: 1.0)
        max_delay: Maximum delay in seconds (default: 16.0)
        exponential_base: Base for exponential backoff calculation (default: 2.0)
        retryable_exceptions: Tuple of exception types to retry
        
    Returns:
        Decorated function with retry logic
        
    Example:
        >>> @with_retry(max_retries=3, initial_delay=1.0)
        ... async def fetch_user(user_id: int):
        ...     return await client.get_user(user_id)
    """



    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_with_exponential_backoff(
                func,
                *args,
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                retryable_exceptions=retryable_exceptions,
                **kwargs
            )
        return wrapper
    return decorator


def is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable (network/timeout related).
    
    This helper function identifies transient errors that are safe to retry,
    excluding client errors (400-499) which indicate bad requests.
    
    Args:
        error: Exception to check
        
    Returns:
        True if error is retryable, False otherwise
        
    Example:
        >>> if is_retryable_error(exception):
        ...     # Retry the operation
        ...     pass
    """



    import aiohttp
    
    # Network/timeout errors are retryable
    retryable_types = (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        ConnectionError,
        OSError,
    )
    
    if isinstance(error, retryable_types):
        # Additional check: Don't retry 4xx client errors
        error_str = str(error).lower()
        if any(code in error_str for code in ["400", "401", "403", "404", "422"]):
            return False
        return True
    
    return False
