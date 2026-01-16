from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class FormStatus(str, enum.Enum):
    """Form status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    EXPIRED = "expired"


class Form(Base):
    """Form model - stores form metadata and initial data."""
    
    __tablename__ = "forms"
    
    id = Column(Integer, primary_key=True, index=True)
    form_token = Column(String, unique=True, index=True, nullable=False)
    client_id = Column(String, nullable=False, index=True)
    policy_id = Column(String, nullable=False)  # Required for backend API
    service_id = Column(Integer, nullable=False)  # Required for backend API
    name = Column(String, nullable=False)
    dni = Column(String, nullable=False)
    cbu = Column(String, nullable=True)
    cuit = Column(String, nullable=True)
    email = Column(String, nullable=False)
    order_id = Column(String, nullable=True, index=True)  # Stores pedido_id from backend response
    
    # Status and timestamps
    status = Column(SQLEnum(FormStatus), default=FormStatus.PENDING, nullable=False)
    is_submitted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    submission = relationship("FormSubmission", back_populates="form", uselist=False)


class FormSubmission(Base):
    """Form submission model - stores submitted form data."""
    
    __tablename__ = "form_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False, unique=True, index=True)
    cbu = Column(String, nullable=True)
    cuit = Column(String, nullable=True)
    email = Column(String, nullable=False)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    external_ws_response = Column(String, nullable=True)  # JSON string
    status = Column(String, nullable=True)  # Status from external WS
    
    # Relationships
    form = relationship("Form", back_populates="submission")
    documents = relationship("Document", back_populates="form_submission", cascade="all, delete-orphan")
    access_links = relationship("DocumentAccessLink", back_populates="form_submission", cascade="all, delete-orphan")

