import uuid
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.operator import Operator
from app.models.api_key import ApiKey
from app.core.api_key import validate_api_key
from app.core.security import decode_access_token
from app.services.operator_service import OperatorService
from app.services.audit_service import AuditService
from app.services.form_service import FormService
from app.services.document_service import DocumentService
from app.services.acl_service import ACLService
from app.models.audit_log import ActionType, UserType


# HTTP Bearer scheme for JWT authentication
bearer_scheme = HTTPBearer(auto_error=False)
bearer_scheme_required = HTTPBearer(auto_error=True)


async def get_current_operator(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme_required),
    db: AsyncSession = Depends(get_db)
) -> Operator:
    """
    Get current operator from JWT token.
    Dependency for endpoints requiring operator authentication.

    Raises:
        HTTPException: 401 if token is missing/invalid, 403 if operator inactive
    """
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    operator_id = payload.get("sub")
    if not operator_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        operator = await OperatorService.get_operator_by_id(db, int(operator_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid operator ID in token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not operator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operator not found"
        )

    if not operator.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator account is inactive"
        )

    return operator


async def get_current_operator_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[Operator]:
    """
    Get current operator from JWT token (optional).
    Returns None if not authenticated or token is invalid.
    """
    if not credentials:
        return None

    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None

    operator_id = payload.get("sub")
    if not operator_id:
        return None

    try:
        operator = await OperatorService.get_operator_by_id(db, int(operator_id))
        if operator and operator.is_active:
            return operator
    except (ValueError, AttributeError):
        pass

    return None


async def get_current_operator_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme_required),
) -> int:
    """
    Get current operator ID from JWT token without database lookup.
    Use when you only need the ID, not the full operator object.

    Raises:
        HTTPException: 401 if token is missing/invalid
    """
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    operator_id = payload.get("sub")
    if not operator_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        return int(operator_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid operator ID in token",
            headers={"WWW-Authenticate": "Bearer"}
        )


# Service Dependencies for Dependency Injection
def get_form_service() -> FormService:
    """Get FormService instance."""
    return FormService()


def get_document_service() -> DocumentService:
    """Get DocumentService instance."""
    return DocumentService()


def get_acl_service() -> ACLService:
    """Get ACLService instance."""
    return ACLService()


class AuditContext:
    """Request-scoped audit logging context with automatic user detection and request ID."""
    
    def __init__(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        db: AsyncSession,
        user_id: Optional[int] = None,
        user_type: Optional[UserType] = None
    ):
        """
        Initialize audit context with request-scoped information.
        
        Args:
            request: FastAPI Request object
            background_tasks: FastAPI BackgroundTasks instance
            db: Database session
            user_id: User ID (operator_id or api_key_id)
            user_type: User type (OPERATOR, API_KEY, or SYSTEM)
        """
        # Get or generate request ID from request state
        if not hasattr(request.state, "request_id"):
            request.state.request_id = str(uuid.uuid4())
        
        self.request_id = request.state.request_id
        self.request = request
        self.background_tasks = background_tasks
        self.db = db
        self.user_id = user_id
        self.user_type = user_type or UserType.SYSTEM
        self.ip_address = request.client.host if request.client else None
        self.user_agent = request.headers.get("user-agent")
    
    async def log_action(
        self,
        action_type: ActionType,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> None:
        """
        Log an action with automatic context and request ID.
        
        Args:
            action_type: Type of action
            resource_type: Type of resource affected
            resource_id: ID of the resource
            request_data: Request payload (JSON)
            response_data: Response payload (JSON)
            status: Status of the action (success/error)
            error_message: Error message if status is error
        """
        await AuditService.log_action_background(
            background_tasks=self.background_tasks,
            db=self.db,
            action_type=action_type,
            user_type=self.user_type,
            user_id=self.user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=self.ip_address,
            user_agent=self.user_agent,
            request_data=request_data,
            response_data=response_data,
            status=status,
            error_message=error_message,
            request_id=self.request_id
        )


async def get_audit_context(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    api_key: Optional[ApiKey] = Depends(lambda: None)  # Optional API key dependency
) -> AuditContext:
    """
    Get request-scoped audit context with automatic user detection.
    
    This dependency automatically detects:
    - API key authentication (from validate_api_key dependency)
    - Operator JWT authentication (from Authorization header)
    - Unauthenticated requests (SYSTEM user type)
    
    Usage:
        @router.post("/endpoint")
        async def endpoint(audit_context: AuditContext = Depends(get_audit_context)):
            await audit_context.log_action(...)
    """
    user_id: Optional[int] = None
    user_type: Optional[UserType] = None
    
    # Try to get API key first (if endpoint uses validate_api_key)
    # Note: This is a workaround - FastAPI doesn't support optional dependencies easily
    # We'll handle API key detection in the endpoint itself if needed
    
    # Try to get operator from JWT token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        if payload:
            operator_id = payload.get("sub")
            if operator_id:
                try:
                    operator = await OperatorService.get_operator_by_id(db, int(operator_id))
                    if operator and operator.is_active:
                        user_id = operator.id
                        user_type = UserType.OPERATOR
                except (ValueError, AttributeError):
                    pass
    
    # If no user detected, use SYSTEM
    if user_type is None:
        user_type = UserType.SYSTEM
    
    return AuditContext(
        request=request,
        background_tasks=background_tasks,
        db=db,
        user_id=user_id,
        user_type=user_type
    )


async def get_audit_context_with_api_key(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(validate_api_key)
) -> AuditContext:
    """
    Get request-scoped audit context with API key authentication.
    
    Use this dependency when the endpoint requires API key authentication.
    
    Usage:
        @router.post("/endpoint")
        async def endpoint(audit_context: AuditContext = Depends(get_audit_context_with_api_key)):
            await audit_context.log_action(...)
    """
    return AuditContext(
        request=request,
        background_tasks=background_tasks,
        db=db,
        user_id=api_key.id,
        user_type=UserType.API_KEY
    )

