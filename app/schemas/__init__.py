"""Pydantic schemas for request/response contracts."""
from app.schemas.form import (
    FormCreateRequest,
    FormCreateResponse,
    FormStatusResponse,
    FormSubmitRequest,
    FormSubmitResponse,
    FormDetailResponse,
)
from app.schemas.document import (
    DocumentResponse,
    DocumentAccessResponse,
)
from app.schemas.auth import (
    GoogleAuthRequest,
    GoogleAuthResponse,
    CurrentUserResponse,
)
from app.schemas.audit import (
    AuditLogResponse,
    AuditLogQueryParams,
    AuditLogListResponse,
)
from app.schemas.acl import (
    RoleResponse,
    PermissionResponse,
    RoleCreateRequest,
    PermissionCreateRequest,
    UserRoleAssignRequest,
    ResourcePermissionCreateRequest,
)

__all__ = [
    "FormCreateRequest",
    "FormCreateResponse",
    "FormStatusResponse",
    "FormSubmitRequest",
    "FormSubmitResponse",
    "FormDetailResponse",
    "DocumentResponse",
    "DocumentAccessResponse",
    "GoogleAuthRequest",
    "GoogleAuthResponse",
    "CurrentUserResponse",
    "AuditLogResponse",
    "AuditLogQueryParams",
    "AuditLogListResponse",
    "RoleResponse",
    "PermissionResponse",
    "RoleCreateRequest",
    "PermissionCreateRequest",
    "UserRoleAssignRequest",
    "ResourcePermissionCreateRequest",
]

