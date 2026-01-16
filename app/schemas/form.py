from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr


class FormCreateRequest(BaseModel):
    """Request schema for creating a form."""
    client_id: str
    policy_id: str  # Required for backend API
    service_id: int  # Required for backend API
    name: str
    dni: str
    cbu: Optional[str] = None
    cuit: Optional[str] = None
    email: EmailStr
    order_id: Optional[str] = None


class FormCreateResponse(BaseModel):
    """Response schema for form creation."""
    form_url: str
    form_token: str
    expires_at: datetime
    
    class Config:
        from_attributes = True


class FormStatusResponse(BaseModel):
    """Response schema for form status."""
    form_token: str
    status: str
    is_submitted: bool
    is_expired: bool
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None


class FormSubmitRequest(BaseModel):
    """Request schema for submitting a form."""
    cbu: Optional[str] = None
    cuit: Optional[str] = None
    email: Optional[EmailStr] = None


class FormSubmitResponse(BaseModel):
    """Response schema for form submission."""
    submission_id: int
    access_token: str
    message: str = "Form submitted successfully"
    
    class Config:
        from_attributes = True


class FormDetailResponse(BaseModel):
    """Response schema for form details."""
    form_token: str
    name: str
    dni: str
    cbu: Optional[str] = None
    cuit: Optional[str] = None
    email: str
    status: str
    is_submitted: bool
    expires_at: datetime
    
    class Config:
        from_attributes = True

