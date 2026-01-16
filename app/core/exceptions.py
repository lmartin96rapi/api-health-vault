from fastapi import HTTPException, status


class FormExpiredException(HTTPException):
    """Exception raised when a form has expired."""
    
    def __init__(self, detail: str = "Form has expired"):
        super().__init__(
            status_code=status.HTTP_410_GONE,
            detail=detail
        )


class FormAlreadySubmittedException(HTTPException):
    """Exception raised when a form has already been submitted."""
    
    def __init__(self, detail: str = "Form has already been submitted"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class InvalidFormTokenException(HTTPException):
    """Exception raised when form token is invalid."""
    
    def __init__(self, detail: str = "Invalid form token"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class DocumentUploadException(HTTPException):
    """Exception raised when document upload fails."""
    
    def __init__(self, detail: str = "Document upload failed"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class AccessLinkExpiredException(HTTPException):
    """Exception raised when access link has expired."""
    
    def __init__(self, detail: str = "Access link has expired"):
        super().__init__(
            status_code=status.HTTP_410_GONE,
            detail=detail
        )


class AccessLinkInvalidException(HTTPException):
    """Exception raised when access link is invalid."""
    
    def __init__(self, detail: str = "Invalid access link"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class ExternalAPIException(HTTPException):
    """Exception raised when external API call fails."""
    
    def __init__(self, detail: str = "External API call failed"):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail
        )


class PermissionDeniedException(HTTPException):
    """Exception raised when user doesn't have permission."""
    
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

