from typing import Optional
from pydantic import BaseModel


class GoogleAuthRequest(BaseModel):
    """Request schema for Google SSO authentication."""
    token: str


class GoogleAuthResponse(BaseModel):
    """Response schema for Google SSO authentication."""
    access_token: str
    token_type: str = "bearer"
    operator_id: int
    email: str
    name: str


class CurrentUserResponse(BaseModel):
    """Response schema for current user info."""
    id: int
    email: str
    name: str
    is_active: bool
    
    class Config:
        from_attributes = True

