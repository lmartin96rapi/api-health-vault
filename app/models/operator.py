from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Operator(Base):
    """Operator model - stores authorized operators for Google SSO."""
    
    __tablename__ = "operators"
    
    id = Column(Integer, primary_key=True, index=True)
    google_email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superadmin = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    created_access_links = relationship("DocumentAccessLink", back_populates="created_by_operator")
    user_roles = relationship("UserRole", back_populates="user")

