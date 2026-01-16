from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from app.models.audit_log import ActionType, UserType


class AuditLogResponse(BaseModel):
    """Response schema for audit log."""
    id: int
    action_type: ActionType
    user_type: UserType
    user_id: Optional[int] = None
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogQueryParams(BaseModel):
    """Query parameters for audit log filtering."""
    action_type: Optional[ActionType] = None
    user_type: Optional[UserType] = None
    user_id: Optional[int] = None
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


class AuditLogListResponse(BaseModel):
    """Response schema for audit log list."""
    logs: list[AuditLogResponse]
    total: int
    limit: int
    offset: int

