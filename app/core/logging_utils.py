import re
from typing import Any, Dict, List, Union, Optional
from copy import deepcopy
from fastapi import Request


def mask_sensitive_data(data: Any, mask_string: str = "***MASKED***") -> Any:
    """
    Recursively mask sensitive data in dictionaries, lists, and strings.
    
    Args:
        data: Data structure to mask (dict, list, str, or other)
        mask_string: String to use for masking
        
    Returns:
        Masked data structure
    """
    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            key_lower = str(key).lower()
            
            # NEVER mask request_id - it's needed for traceability
            if key_lower == "requestid" or key_lower == "request_id":
                masked[key] = value
            # Mask API keys
            elif any(term in key_lower for term in ["api_key", "apikey", "x-api-key", "api-key"]):
                masked[key] = mask_string
            # Mask tokens (but not request_id)
            elif any(term in key_lower for term in ["token", "access_token", "jwt", "authorization", "bearer"]):
                masked[key] = mask_string
            # Mask passwords and secrets
            elif any(term in key_lower for term in ["password", "secret", "secret_key", "private_key"]):
                masked[key] = mask_string
            # Partial mask for financial data (show last 4 digits)
            elif key_lower in ["cbu", "cuit", "dni"]:
                if isinstance(value, str) and len(value) > 4:
                    masked[key] = "*" * (len(value) - 4) + value[-4:]
                else:
                    masked[key] = mask_string
            # Partial mask for email (show first 3 chars + domain)
            elif key_lower == "email" and isinstance(value, str):
                if "@" in value:
                    parts = value.split("@")
                    if len(parts) == 2 and len(parts[0]) > 3:
                        masked[key] = parts[0][:3] + "***@" + parts[1]
                    else:
                        masked[key] = mask_string
                else:
                    masked[key] = mask_string
            # Recursively process nested structures
            else:
                masked[key] = mask_sensitive_data(value, mask_string)
        
        return masked
    
    elif isinstance(data, list):
        return [mask_sensitive_data(item, mask_string) for item in data]
    
    elif isinstance(data, str):
        # Check if string contains sensitive patterns
        # Mask JWT tokens (starts with eyJ)
        if data.startswith("eyJ") and len(data) > 50:
            return mask_string
        # Don't mask UUIDs (request IDs) - they're 36 chars with hyphens
        # Mask API keys (long alphanumeric strings without hyphens, > 32 chars)
        if len(data) > 32 and re.match(r'^[A-Za-z0-9_-]+$', data) and '-' not in data:
            return mask_string
        
        return data
    
    return data


def mask_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Mask sensitive HTTP headers.
    
    Args:
        headers: Dictionary of HTTP headers
        
    Returns:
        Dictionary with sensitive headers masked
    """
    masked = {}
    sensitive_headers = [
        "authorization",
        "x-api-key",
        "api-key",
        "x-auth-token",
        "cookie",
        "set-cookie"
    ]
    
    for key, value in headers.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_headers):
            masked[key] = "***MASKED***"
        else:
            masked[key] = value
    
    return masked


def mask_request_body(body: Any) -> Any:
    """
    Mask sensitive data in request body.
    
    Args:
        body: Request body (dict, list, str, or other)
        
    Returns:
        Masked request body
    """
    return mask_sensitive_data(body)


def get_request_id(request: Optional[Request]) -> Optional[str]:
    """
    Extract request ID from request state.
    
    Args:
        request: FastAPI Request object (can be None)
        
    Returns:
        Request ID (UUID string) or None if not available
    """
    if request and hasattr(request.state, "request_id"):
        return request.state.request_id
    return None


def sanitize_log_message(message: str, **kwargs: Any) -> str:
    """
    Sanitize log message by masking sensitive data in keyword arguments.
    RequestID is extracted and passed via logger extra, not included in message.
    
    Args:
        message: Base log message
        **kwargs: Additional context to include (will be masked)
                  RequestID will be extracted and passed via logger extra
        
    Returns:
        Sanitized log message with context (RequestID removed from message, added to extra)
    """
    # Extract RequestID before masking (it won't be masked anyway)
    request_id = kwargs.pop('RequestID', None) or kwargs.pop('request_id', None)
    
    if not kwargs:
        # If only RequestID was provided, return message as-is
        # RequestID will be added via logger extra in the calling code
        return message
    
    # Mask sensitive data in remaining kwargs
    masked_kwargs = mask_sensitive_data(kwargs)
    
    # Format context as key-value pairs (RequestID not included here)
    context_parts = []
    for key, value in masked_kwargs.items():
        if isinstance(value, (dict, list)):
            # Convert complex structures to string representation
            value_str = str(value)[:200]  # Limit length
            context_parts.append(f"{key}: {value_str}")
        else:
            context_parts.append(f"{key}: {value}")
    
    if context_parts:
        formatted_message = f"{message} | {' | '.join(context_parts)}"
    else:
        formatted_message = message
    
    # Store RequestID in the formatted message for formatter to extract
    # Format: "message | context | RequestID: <uuid>"
    if request_id:
        formatted_message = f"{formatted_message} | RequestID: {request_id}"
    
    return formatted_message

