from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class DocumentType(str, enum.Enum):
    """Document type enumeration."""
    INVOICE = "invoice"  # factura
    PRESCRIPTION = "prescription"  # receta médica
    DIAGNOSIS = "diagnosis"  # diagnóstico e indicaciones terapéuticas


class Document(Base):
    """Document model - stores uploaded files metadata."""
    
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    form_submission_id = Column(Integer, ForeignKey("form_submissions.id"), nullable=False, index=True)
    document_type = Column(SQLEnum(DocumentType), nullable=False)
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    mime_type = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    form_submission = relationship("FormSubmission", back_populates="documents")

