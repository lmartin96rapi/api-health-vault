import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.router import api_router
from app.config import settings
from app.core.exceptions import (
    FormExpiredException,
    FormAlreadySubmittedException,
    InvalidFormTokenException,
    DocumentUploadException,
    AccessLinkExpiredException,
    AccessLinkInvalidException,
    ExternalAPIException,
    PermissionDeniedException,
)
from app.core.circuit_breaker import CircuitBreakerOpenException
from app.core.logging_config import setup_logging, cleanup_old_logs
from app.core.logging_utils import sanitize_log_message
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.rate_limit import setup_rate_limiting
from app.middleware.csrf import setup_csrf_protection
from app.middleware.security import setup_security_middleware

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Initialize logging on startup
@app.on_event("startup")
async def startup_event():
    """Initialize logging and cleanup old logs on application startup."""
    setup_logging()
    cleanup_old_logs()
    logger.info("Application startup complete")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-CSRF-Token", "X-Request-ID", "Idempotency-Key", "Accept", "Origin"],
)

# Security middleware (request size limit + security headers)
setup_security_middleware(app, max_request_size=settings.MAX_REQUEST_SIZE)

# Logging middleware (after CORS, before routes)
if settings.LOG_ENABLE_REQUEST_LOGGING:
    app.add_middleware(LoggingMiddleware)

# CSRF protection middleware
setup_csrf_protection(app)

# Rate limiting
setup_rate_limiting(app)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Exception handlers with logging
@app.exception_handler(FormExpiredException)
async def form_expired_handler(request: Request, exc: FormExpiredException):
    logger.warning(
        sanitize_log_message(
            "Form expired",
            Path=request.url.path,
            Method=request.method,
            IP=request.client.host if request.client else None,
            Detail=exc.detail
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(FormAlreadySubmittedException)
async def form_already_submitted_handler(request: Request, exc: FormAlreadySubmittedException):
    logger.warning(
        sanitize_log_message(
            "Form already submitted",
            Path=request.url.path,
            Method=request.method,
            IP=request.client.host if request.client else None,
            Detail=exc.detail
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(InvalidFormTokenException)
async def invalid_form_token_handler(request: Request, exc: InvalidFormTokenException):
    logger.warning(
        sanitize_log_message(
            "Invalid form token",
            Path=request.url.path,
            Method=request.method,
            IP=request.client.host if request.client else None,
            Detail=exc.detail
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(DocumentUploadException)
async def document_upload_handler(request: Request, exc: DocumentUploadException):
    logger.error(
        sanitize_log_message(
            "Document upload failed",
            Path=request.url.path,
            Method=request.method,
            IP=request.client.host if request.client else None,
            Detail=exc.detail
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(AccessLinkExpiredException)
async def access_link_expired_handler(request: Request, exc: AccessLinkExpiredException):
    logger.warning(
        sanitize_log_message(
            "Access link expired",
            Path=request.url.path,
            Method=request.method,
            IP=request.client.host if request.client else None,
            Detail=exc.detail
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(AccessLinkInvalidException)
async def access_link_invalid_handler(request: Request, exc: AccessLinkInvalidException):
    logger.warning(
        sanitize_log_message(
            "Invalid access link",
            Path=request.url.path,
            Method=request.method,
            IP=request.client.host if request.client else None,
            Detail=exc.detail
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(ExternalAPIException)
async def external_api_handler(request: Request, exc: ExternalAPIException):
    logger.error(
        sanitize_log_message(
            "External API error",
            Path=request.url.path,
            Method=request.method,
            IP=request.client.host if request.client else None,
            StatusCode=exc.status_code,
            Detail=exc.detail
        ),
        exc_info=True
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(PermissionDeniedException)
async def permission_denied_handler(request: Request, exc: PermissionDeniedException):
    logger.warning(
        sanitize_log_message(
            "Permission denied",
            Path=request.url.path,
            Method=request.method,
            IP=request.client.host if request.client else None,
            Detail=exc.detail
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(CircuitBreakerOpenException)
async def circuit_breaker_handler(request: Request, exc: CircuitBreakerOpenException):
    logger.warning(
        sanitize_log_message(
            "Circuit breaker open",
            Path=request.url.path,
            Method=request.method,
            IP=request.client.host if request.client else None,
            Message=exc.message
        )
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Service temporarily unavailable. Please try again later."}
    )


# Generic exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception(
        sanitize_log_message(
            f"Unhandled exception: {type(exc).__name__}",
            Path=request.url.path,
            Method=request.method,
            IP=request.client.host if request.client else None,
            ExceptionType=type(exc).__name__,
            ExceptionMessage=str(exc)
        )
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error" if settings.ENVIRONMENT == "production" else str(exc)
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.VERSION}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Health Insurance API",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs"
    }

