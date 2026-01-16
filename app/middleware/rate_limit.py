"""
Rate limiting middleware using slowapi.
"""
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import FastAPI, Request
from app.config import settings

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.
    Handles X-Forwarded-For header for proxied requests.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain (original client)
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
    enabled=settings.RATE_LIMIT_ENABLED
)


def setup_rate_limiting(app: FastAPI) -> None:
    """
    Configure rate limiting for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    if not settings.RATE_LIMIT_ENABLED:
        logger.info("Rate limiting is disabled")
        return

    # Add limiter to app state
    app.state.limiter = limiter

    # Add rate limit exceeded handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add middleware
    app.add_middleware(SlowAPIMiddleware)

    logger.info(
        f"Rate limiting enabled: default={settings.RATE_LIMIT_DEFAULT}, "
        f"auth={settings.RATE_LIMIT_AUTH}, forms={settings.RATE_LIMIT_FORMS}"
    )


# Decorators for specific rate limits
def rate_limit_auth():
    """Rate limit decorator for auth endpoints."""
    return limiter.limit(settings.RATE_LIMIT_AUTH)


def rate_limit_forms():
    """Rate limit decorator for form creation endpoints."""
    return limiter.limit(settings.RATE_LIMIT_FORMS)


def rate_limit_default():
    """Rate limit decorator using default limit."""
    return limiter.limit(settings.RATE_LIMIT_DEFAULT)
