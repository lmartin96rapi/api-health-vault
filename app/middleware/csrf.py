"""
CSRF protection middleware using double-submit cookie pattern.
"""
import secrets
import logging
from typing import Set, Optional
from urllib.parse import urlparse
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.config import settings

logger = logging.getLogger(__name__)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware using double-submit cookie pattern.

    For state-changing requests (POST, PUT, DELETE, PATCH), validates that:
    1. A CSRF token cookie exists
    2. A matching X-CSRF-Token header is present
    3. Both values match

    Safe methods (GET, HEAD, OPTIONS, TRACE) are exempt.
    Certain paths can be exempted (e.g., public form submission, OAuth callbacks).
    """

    SAFE_METHODS: Set[str] = {"GET", "HEAD", "OPTIONS", "TRACE"}

    # Paths that are exempt from CSRF protection
    EXEMPT_PATHS: Set[str] = {
        "/api/v1/forms",  # Form submission is public
        "/api/v1/auth/google",  # OAuth callback
        "/health",  # Health check
        "/docs",  # Swagger UI
        "/redoc",  # ReDoc
        "/openapi.json",  # OpenAPI spec
    }

    # Path prefixes that are exempt
    EXEMPT_PATH_PREFIXES: tuple = (
        "/api/v1/forms/",  # All form-related endpoints (public)
    )

    COOKIE_NAME: str = "csrf_token"
    HEADER_NAME: str = "X-CSRF-Token"
    TOKEN_LENGTH: int = 32

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request with CSRF validation."""
        # Skip if CSRF is disabled
        if not settings.CSRF_ENABLED:
            return await call_next(request)

        # Skip safe methods
        if request.method in self.SAFE_METHODS:
            response = await call_next(request)
            # Ensure CSRF cookie is set for subsequent requests
            return self._ensure_csrf_cookie(request, response)

        # Skip exempt paths (but still validate origin for state-changing methods)
        if self._is_exempt_path(request.url.path):
            # Still validate origin for exempt paths to prevent cross-origin attacks
            origin_error = self._validate_origin(request)
            if origin_error:
                logger.warning(
                    f"CSRF origin validation failed for exempt path: {origin_error} for {request.method} {request.url.path}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid request origin"
                )
            return await call_next(request)

        # Validate CSRF token
        csrf_cookie = request.cookies.get(self.COOKIE_NAME)
        csrf_header = request.headers.get(self.HEADER_NAME)

        if not csrf_cookie:
            logger.warning(
                f"CSRF validation failed: missing cookie for {request.method} {request.url.path}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token cookie missing"
            )

        if not csrf_header:
            logger.warning(
                f"CSRF validation failed: missing header for {request.method} {request.url.path}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token header missing"
            )

        if not secrets.compare_digest(csrf_cookie, csrf_header):
            logger.warning(
                f"CSRF validation failed: token mismatch for {request.method} {request.url.path}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token mismatch"
            )

        return await call_next(request)

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from CSRF protection."""
        # Exact match
        if path in self.EXEMPT_PATHS:
            return True

        # Prefix match
        if path.startswith(self.EXEMPT_PATH_PREFIXES):
            return True

        return False

    def _validate_origin(self, request: Request) -> Optional[str]:
        """
        Validate Origin/Referer header against allowed origins.

        Returns:
            None if valid, error message if invalid
        """
        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")

        # If no Origin or Referer, allow (same-origin requests may not include these)
        if not origin and not referer:
            return None

        # Get allowed origins from settings
        allowed_origins = settings.BACKEND_CORS_ORIGINS

        # Check Origin header
        if origin:
            if origin not in allowed_origins:
                return f"Origin '{origin}' not allowed"

        # Check Referer header if Origin is not present
        if not origin and referer:
            parsed = urlparse(referer)
            referer_origin = f"{parsed.scheme}://{parsed.netloc}"
            if referer_origin not in allowed_origins:
                return f"Referer origin '{referer_origin}' not allowed"

        return None

    def _ensure_csrf_cookie(self, request: Request, response: Response) -> Response:
        """Ensure CSRF cookie is set on response."""
        if self.COOKIE_NAME not in request.cookies:
            token = secrets.token_urlsafe(self.TOKEN_LENGTH)
            response.set_cookie(
                key=self.COOKIE_NAME,
                value=token,
                httponly=False,  # Must be readable by JavaScript
                samesite="strict",
                secure=settings.ENVIRONMENT == "production",
                max_age=3600 * 24  # 24 hours
            )
        return response


def setup_csrf_protection(app) -> None:
    """
    Configure CSRF protection for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    if not settings.CSRF_ENABLED:
        logger.info("CSRF protection is disabled")
        return

    app.add_middleware(CSRFMiddleware)
    logger.info("CSRF protection enabled")
