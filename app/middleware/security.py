"""
Security middleware for request size limiting and security headers.
"""
import logging
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.config import settings

logger = logging.getLogger(__name__)

# Default max request body size: 50MB (enough for document uploads)
DEFAULT_MAX_REQUEST_SIZE = 50 * 1024 * 1024


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit request body size to prevent DoS attacks.

    Checks Content-Length header and rejects requests exceeding the limit.
    """

    def __init__(self, app, max_size: int = DEFAULT_MAX_REQUEST_SIZE):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check Content-Length header
        content_length = request.headers.get("content-length")

        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size:
                    logger.warning(
                        f"Request body too large: {size} bytes (max: {self.max_size})",
                        extra={
                            "path": request.url.path,
                            "method": request.method,
                            "content_length": size,
                            "max_size": self.max_size,
                            "ip": request.client.host if request.client else None
                        }
                    )
                    return Response(
                        content='{"detail": "Request body too large"}',
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        media_type="application/json"
                    )
            except ValueError:
                # Invalid Content-Length header
                pass

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Adds Content-Security-Policy, X-Content-Type-Options, X-Frame-Options,
    and other security headers.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        path = request.url.path
        is_docs_endpoint = (
            path.endswith("/docs") or
            path.endswith("/redoc") or
            path.endswith("/openapi.json") or
            "/docs" in path or
            "/redoc" in path
        )

        if is_docs_endpoint:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.jsdelivr.net; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'none'; "
                "form-action 'none'"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; "
                "frame-ancestors 'none'; "
                "base-uri 'none'; "
                "form-action 'none'"
            )

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS filter (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy (restrict browser features)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        # Cache control for API responses
        if "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

        return response


def setup_security_middleware(app, max_request_size: int = DEFAULT_MAX_REQUEST_SIZE) -> None:
    """
    Configure security middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
        max_request_size: Maximum allowed request body size in bytes
    """
    # Add security headers middleware (runs on every response)
    app.add_middleware(SecurityHeadersMiddleware)

    # Add request size limit middleware
    app.add_middleware(RequestSizeLimitMiddleware, max_size=max_request_size)

    logger.info(
        f"Security middleware enabled: max_request_size={max_request_size / (1024*1024):.1f}MB"
    )
