from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.models.document import DocumentType


class DocumentResponse(BaseModel):
    """Response schema for document."""
    id: int
    document_type: DocumentType
    file_name: str
    file_size: int
    mime_type: str
    uploaded_at: datetime
    
    class Config:
        from_attributes = True


class DocumentAccessResponse(BaseModel):
    """Response schema for document access (view submission)."""
    form_submission_id: int
    cbu: Optional[str] = None
    cuit: Optional[str] = None
    email: str
    submitted_at: datetime
    status: Optional[str] = None
    documents: list[DocumentResponse]
    
    class Config:
        from_attributes = True

