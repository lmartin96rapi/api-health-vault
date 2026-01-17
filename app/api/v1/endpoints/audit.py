from typing import Optional, Literal
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.api.deps import get_current_operator_id
from app.schemas.audit import AuditLogResponse, AuditLogListResponse
from app.services.audit_service import AuditService
from app.models.audit_log import ActionType, UserType
from app.models.operator import Operator
from app.core.acl import require_endpoint_permission

router = APIRouter()

# Allowed values for query parameters
ALLOWED_RESOURCE_TYPES = Literal["form", "form_submission", "document", "operator", "access_link"]
ALLOWED_STATUS_VALUES = Literal["success", "error"]


@router.get("", response_model=AuditLogListResponse)
async def get_audit_logs(
    action_type: Optional[ActionType] = Query(None),
    user_type: Optional[UserType] = Query(None),
    user_id: Optional[int] = Query(None),
    resource_type: Optional[ALLOWED_RESOURCE_TYPES] = Query(None),
    resource_id: Optional[int] = Query(None),
    status_filter: Optional[ALLOWED_STATUS_VALUES] = Query(None, alias="status"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    operator_id: int = Depends(get_current_operator_id)
):
    """
    Query audit logs with filters.
    Requires authentication and ACL permission.
    Only superadmins can access audit logs.
    """
    # Check permission
    await require_endpoint_permission(
        db=db,
        user_id=operator_id,
        permission_name="view_audit_logs"
    )

    # Only superadmins can access audit logs
    result = await db.execute(
        select(Operator).where(Operator.id == operator_id)
    )
    operator = result.scalar_one_or_none()

    if not (operator and operator.is_superadmin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can access audit logs"
        )

    # Get logs with proper pagination (returns tuple of logs and total count)
    logs, total = await AuditService.get_audit_logs(
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
        total=total,
        limit=limit,
        offset=offset
    )

