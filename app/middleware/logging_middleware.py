import logging
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.config import settings
from app.core.logging_utils import mask_headers, mask_request_body, sanitize_log_message

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses with sensitive data masking."""
    
    # Endpoints to skip logging (reduce noise)
    SKIP_PATHS = ["/health", "/", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next):
        # Skip logging for health checks and docs
        if any(request.url.path.startswith(path) for path in self.SKIP_PATHS):
            return await call_next(request)
        
        if not settings.LOG_ENABLE_REQUEST_LOGGING:
            return await call_next(request)
        
        # Generate or retrieve request ID
        if not hasattr(request.state, "request_id"):
            request.state.request_id = str(uuid.uuid4())
        
        request_id = request.state.request_id
        start_time = time.time()
        
        # Extract request information
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Mask sensitive headers
        masked_headers = mask_headers(dict(request.headers))
        
        # Log incoming request with request ID
        logger.debug(
            sanitize_log_message(
                f"Request: {method} {path}",
                RequestID=request_id,
                IP=client_ip,
                UserAgent=user_agent,
                QueryParams=query_params,
                Headers=masked_headers
            )
        )
        
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add X-Request-ID header to response
            response.headers["X-Request-ID"] = request_id
            
            # Log response with request ID
            logger.info(
                sanitize_log_message(
                    f"Response: {method} {path}",
                    RequestID=request_id,
                    Status=response.status_code,
                    ProcessTime=f"{process_time:.3f}s",
                    IP=client_ip
                )
            )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.exception(
                sanitize_log_message(
                    f"Exception in request: {method} {path}",
                    RequestID=request_id,
                    ProcessTime=f"{process_time:.3f}s",
                    IP=client_ip,
                    Error=str(e)
                )
            )
            raise

