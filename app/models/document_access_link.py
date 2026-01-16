from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class DocumentAccessLink(Base):
    """Document access link model - stores unique access links for operators."""
    
    __tablename__ = "document_access_links"
    
    id = Column(Integer, primary_key=True, index=True)
    form_submission_id = Column(Integer, ForeignKey("form_submissions.id"), nullable=False, index=True)
    access_token = Column(String, unique=True, nullable=False, index=True)  # Secure random hash
    order_id = Column(String, nullable=True, index=True)  # pedido_id from backend API
    created_by = Column(Integer, ForeignKey("operators.id"), nullable=True)  # Operator who generated it (auto-generated on submission)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # None = permanent access for operators
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    form_submission = relationship("FormSubmission", back_populates="access_links")
    created_by_operator = relationship("Operator", back_populates="created_access_links")

