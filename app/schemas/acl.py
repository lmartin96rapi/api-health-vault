from typing import Optional, List
from pydantic import BaseModel


class RoleResponse(BaseModel):
    """Response schema for role."""
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    
    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    """Response schema for permission."""
    id: int
    name: str
    description: Optional[str] = None
    resource_type: Optional[str] = None
    is_active: bool
    
    class Config:
        from_attributes = True


class RoleCreateRequest(BaseModel):
    """Request schema for creating a role."""
    name: str
    description: Optional[str] = None


class PermissionCreateRequest(BaseModel):
    """Request schema for creating a permission."""
    name: str
    description: Optional[str] = None
    resource_type: Optional[str] = None


class UserRoleAssignRequest(BaseModel):
    """Request schema for assigning a role to a user."""
    user_id: int
    role_id: int


class ResourcePermissionCreateRequest(BaseModel):
    """Request schema for creating a resource permission."""
    permission_id: int
    resource_type: str
    resource_id: int
    user_id: int

