"""
Circuit breaker pattern implementation for external API calls.
"""
import logging
import time
from enum import Enum
from typing import Callable, Any, Optional
from functools import wraps
from app.config import settings

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Circuit is open, requests fail immediately
    HALF_OPEN = "half_open"  # Testing if service has recovered


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""

    def __init__(self, message: str = "Circuit breaker is open"):
        self.message = message
        super().__init__(self.message)


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting external API calls.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: After failure_threshold failures, circuit opens and requests fail immediately
    - HALF_OPEN: After recovery_timeout, allows limited requests to test recovery

    Usage:
        circuit_breaker = CircuitBreaker(name="backend_api")

        @circuit_breaker
        async def call_external_api():
            ...

        # Or manually:
        result = await circuit_breaker.call(call_external_api, *args, **kwargs)
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: Optional[int] = None,
        recovery_timeout: Optional[int] = None,
        half_open_max_calls: Optional[int] = None,
        excluded_exceptions: tuple = ()
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Name for this circuit breaker (for logging)
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            half_open_max_calls: Max calls allowed in half-open state
            excluded_exceptions: Exceptions that should not count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold or settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        self.recovery_timeout = recovery_timeout or settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT
        self.half_open_max_calls = half_open_max_calls or settings.CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS
        self.excluded_exceptions = excluded_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return True
        return (time.time() - self._last_failure_time) >= self.recovery_timeout

    def _on_success(self) -> None:
        """Handle successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.half_open_max_calls:
                # Enough successful calls, close the circuit
                self._close()
                logger.info(f"Circuit breaker '{self.name}' closed after successful recovery")
        else:
            # Reset failure count on success in closed state
            self._failure_count = 0

    def _on_failure(self, exception: Exception) -> None:
        """Handle failed call."""
        # Check if exception should be excluded
        if isinstance(exception, self.excluded_exceptions):
            return

        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Failure in half-open state, reopen circuit
            self._open()
            logger.warning(
                f"Circuit breaker '{self.name}' reopened after failure in half-open state"
            )
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._open()
                logger.warning(
                    f"Circuit breaker '{self.name}' opened after {self._failure_count} failures"
                )

    def _open(self) -> None:
        """Open the circuit."""
        self._state = CircuitState.OPEN
        self._half_open_calls = 0
        self._success_count = 0

    def _close(self) -> None:
        """Close the circuit."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0

    def _half_open(self) -> None:
        """Set circuit to half-open state."""
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        self._half_open_calls = 0

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result of function call

        Raises:
            CircuitBreakerOpenException: If circuit is open
            Exception: If function raises an exception
        """
        # Check if circuit is open
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._half_open()
                logger.info(
                    f"Circuit breaker '{self.name}' entering half-open state"
                )
            else:
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.name}' is open. "
                    f"Retry after {self.recovery_timeout}s"
                )

        # Check half-open call limit
        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.name}' half-open call limit reached"
                )
            self._half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    def __call__(self, func: Callable) -> Callable:
        """
        Decorator to wrap async function with circuit breaker.

        Usage:
            @circuit_breaker
            async def my_function():
                ...
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        return wrapper

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        self._close()
        self._last_failure_time = None
        logger.info(f"Circuit breaker '{self.name}' manually reset")

    def get_status(self) -> dict:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self._last_failure_time
        }


# Pre-configured circuit breakers for external APIs
backend_api_circuit_breaker = CircuitBreaker(name="backend_api")
wsp_api_circuit_breaker = CircuitBreaker(name="wsp_api")
