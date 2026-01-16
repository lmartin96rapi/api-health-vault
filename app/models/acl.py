from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# Association table for many-to-many relationship between roles and permissions
role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)


class Role(Base):
    """Role model - stores user roles."""
    
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    permissions = relationship("Permission", secondary=role_permission, back_populates="roles")
    user_roles = relationship("UserRole", back_populates="role")


class Permission(Base):
    """Permission model - stores endpoint and resource permissions."""
    
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)  # e.g., "create_form", "view_document"
    description = Column(String, nullable=True)
    resource_type = Column(String, nullable=True)  # e.g., "form", "document", "form_submission"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    roles = relationship("Role", secondary=role_permission, back_populates="permissions")
    resource_permissions = relationship("ResourcePermission", back_populates="permission")


class UserRole(Base):
    """UserRole model - assigns roles to users (operators)."""
    
    __tablename__ = "user_roles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("operators.id"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("Operator", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")


class ResourcePermission(Base):
    """ResourcePermission model - stores resource-level permissions."""
    
    __tablename__ = "resource_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False, index=True)
    resource_type = Column(String, nullable=False, index=True)  # e.g., "form_submission"
    resource_id = Column(Integer, nullable=False, index=True)  # ID of the specific resource
    user_id = Column(Integer, ForeignKey("operators.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    permission = relationship("Permission", back_populates="resource_permissions")

