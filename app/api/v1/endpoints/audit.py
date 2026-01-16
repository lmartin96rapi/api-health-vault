from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.audit import AuditLogResponse, AuditLogListResponse
from app.services.audit_service import AuditService
from app.models.audit_log import ActionType, UserType
from app.core.acl import require_endpoint_permission
from app.core.security import decode_access_token
from fastapi import Request, HTTPException, status

router = APIRouter()


async def get_current_operator_id(request: Request, db: AsyncSession) -> int:
    """Get current operator ID from JWT token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    from app.core.security import decode_access_token
    
    token = auth_header.split(" ")[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    return int(payload.get("sub"))


@router.get("", response_model=AuditLogListResponse)
async def get_audit_logs(
    action_type: Optional[ActionType] = Query(None),
    user_type: Optional[UserType] = Query(None),
    user_id: Optional[int] = Query(None),
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Query audit logs with filters.
    Requires authentication and ACL permission.
    """
    # Get current operator
    operator_id = await get_current_operator_id(request, db)
    
    # Check permission
    await require_endpoint_permission(
        db=db,
        user_id=operator_id,
        permission_name="view_audit_logs"
    )
    
    # Get logs
    logs = await AuditService.get_audit_logs(
        db=db,
        action_type=action_type,
        user_type=user_type,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status_filter,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    
    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=len(logs),
        limit=limit,
        offset=offset
    )

