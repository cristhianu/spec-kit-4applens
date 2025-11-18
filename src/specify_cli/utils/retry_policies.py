"""
Retry policies for resilient operations.

Implements exponential backoff with jitter and circuit breaker pattern
for handling transient failures in Azure operations and HTTP requests.
"""

import asyncio
import random
import time
from typing import Callable, TypeVar, Any, Optional, Awaitable
from functools import wraps
from enum import Enum
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures exceeded threshold, reject requests
    HALF_OPEN = "half_open"  # Testing if system recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted"""
    def __init__(self, attempts: int, last_error: Exception):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Retry exhausted after {attempts} attempts: {last_error}")


class ExponentialBackoff:
    """
    Implements exponential backoff with jitter.
    
    Retry delay increases exponentially with each attempt:
    delay = base_delay * (2 ^ attempt) + random_jitter
    """
    
    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        max_attempts: int = 3,
        jitter: bool = True
    ):
        """
        Initialize exponential backoff policy.
        
        Args:
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            max_attempts: Maximum retry attempts
            jitter: Whether to add random jitter to delay
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_attempts = max_attempts
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number.
        
        Args:
            attempt: Attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        # Exponential calculation: base * 2^attempt
        delay = self.base_delay * (2 ** attempt)
        
        # Cap at max delay
        delay = min(delay, self.max_delay)
        
        # Add jitter (±25% of delay)
        if self.jitter:
            jitter_amount = delay * 0.25
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(0, delay)  # Ensure non-negative
    
    async def execute_async(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Execute async function with exponential backoff retry.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of successful function call
            
        Raises:
            RetryExhaustedError: If all attempts fail
        """
        last_error = None
        
        for attempt in range(self.max_attempts):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.max_attempts}")
                result = await func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"Succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
                # If not last attempt, wait before retry
                if attempt < self.max_attempts - 1:
                    delay = self.get_delay(attempt)
                    logger.debug(f"Waiting {delay:.2f}s before retry")
                    await asyncio.sleep(delay)
        
        # All attempts exhausted
        if last_error is None:
            raise RuntimeError("All retry attempts failed with no error captured")
        raise RetryExhaustedError(self.max_attempts, last_error)
    
    def execute_sync(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Execute synchronous function with exponential backoff retry.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of successful function call
            
        Raises:
            RetryExhaustedError: If all attempts fail
        """
        last_error = None
        
        for attempt in range(self.max_attempts):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.max_attempts}")
                result = func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"Succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
                # If not last attempt, wait before retry
                if attempt < self.max_attempts - 1:
                    delay = self.get_delay(attempt)
                    logger.debug(f"Waiting {delay:.2f}s before retry")
                    time.sleep(delay)
        
        # All attempts exhausted
        if last_error is None:
            raise RuntimeError("All retry attempts failed with no error captured")
        raise RetryExhaustedError(self.max_attempts, last_error)


class CircuitBreaker:
    """
    Implements circuit breaker pattern.
    
    Prevents cascading failures by stopping requests when failure
    threshold is exceeded. Allows periodic test requests to check
    if system has recovered.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before trying recovery
            success_threshold: Successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
    
    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        # Check circuit state
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.recovery_timeout:
                    logger.info("Circuit breaker entering HALF_OPEN state")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker is OPEN. Try again in {self.recovery_timeout - elapsed:.1f}s"
                    )
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise
    
    async def call_async(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """
        Execute async function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        # Check circuit state
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.recovery_timeout:
                    logger.info("Circuit breaker entering HALF_OPEN state")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker is OPEN. Try again in {self.recovery_timeout - elapsed:.1f}s"
                    )
        
        # Execute function
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logger.info("Circuit breaker recovered, moving to CLOSED state")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # Failed recovery attempt, back to open
            logger.warning("Circuit breaker recovery failed, moving back to OPEN state")
            self.state = CircuitState.OPEN
            self.success_count = 0
            
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                logger.error(f"Circuit breaker threshold exceeded ({self.failure_count} failures), moving to OPEN state")
                self.state = CircuitState.OPEN
    
    def reset(self) -> None:
        """Manually reset circuit breaker to closed state"""
        logger.info("Circuit breaker manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0
):
    """
    Decorator to add retry logic to async functions.
    
    Args:
        max_attempts: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        
    Example:
        @with_retry(max_attempts=5, base_delay=2.0)
        async def fetch_data():
            # Function with retry logic
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            backoff = ExponentialBackoff(
                base_delay=base_delay,
                max_delay=max_delay,
                max_attempts=max_attempts
            )
            return await backoff.execute_async(func, *args, **kwargs)
        return wrapper
    return decorator
