from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.sql import func
import enum
from app.database import Base


class ActionType(str, enum.Enum):
    """Action type enumeration for audit logging."""
    FORM_CREATED = "form_created"
    FORM_SUBMITTED = "form_submitted"
    DOCUMENT_UPLOADED = "document_uploaded"
    ACCESS_LINK_GENERATED = "access_link_generated"
    ACCESS_LINK_ACCESSED = "access_link_accessed"
    DOCUMENT_VIEWED = "document_viewed"
    DOCUMENT_DOWNLOADED = "document_downloaded"
    EXTERNAL_WS_CALLED = "external_ws_called"
    OPERATOR_LOGIN = "operator_login"
    PERMISSION_DENIED = "permission_denied"


class UserType(str, enum.Enum):
    """User type enumeration for audit logging."""
    OPERATOR = "operator"
    API_KEY = "api_key"
    SYSTEM = "system"


class AuditLog(Base):
    """Audit log model - comprehensive audit trail for all actions."""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(SQLEnum(ActionType), nullable=False, index=True)
    user_type = Column(SQLEnum(UserType), nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)  # operator_id or api_key_id
    resource_type = Column(String, nullable=True, index=True)  # e.g., "form", "form_submission", "document"
    resource_id = Column(Integer, nullable=True, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    request_data = Column(JSON, nullable=True)  # Request payload
    response_data = Column(JSON, nullable=True)  # Response payload
    status = Column(String, nullable=False, index=True)  # "success" or "error"
    error_message = Column(String, nullable=True)
    request_id = Column(String, nullable=True, index=True)  # UUID for request tracing
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

