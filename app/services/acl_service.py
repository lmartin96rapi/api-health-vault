from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.acl import Role, Permission, UserRole, ResourcePermission
from app.models.operator import Operator


class ACLService:
    """Service for managing ACL (Access Control List) operations."""
    
    @staticmethod
    async def get_user_roles(
        db: AsyncSession,
        user_id: int
    ) -> List[Role]:
        """Get all roles for a user."""
        result = await db.execute(
            select(UserRole)
            .where(UserRole.user_id == user_id)
            .options(selectinload(UserRole.role))
        )
        user_roles = result.scalars().all()
        return [user_role.role for user_role in user_roles if user_role.role.is_active]
    
    @staticmethod
    async def get_role_permissions(
        db: AsyncSession,
        role_id: int
    ) -> List[Permission]:
        """Get all permissions for a role."""
        result = await db.execute(
            select(Role)
            .where(Role.id == role_id)
            .options(selectinload(Role.permissions))
        )
        role = result.scalar_one_or_none()
        if not role:
            return []
        return [p for p in role.permissions if p.is_active]
    
    @staticmethod
    async def assign_role_to_user(
        db: AsyncSession,
        user_id: int,
        role_id: int
    ) -> UserRole:
        """Assign a role to a user."""
        # Check if already assigned
        result = await db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        
        user_role = UserRole(user_id=user_id, role_id=role_id)
        db.add(user_role)
        await db.commit()
        await db.refresh(user_role)
        return user_role
    
    @staticmethod
    async def create_resource_permission(
        db: AsyncSession,
        permission_id: int,
        resource_type: str,
        resource_id: int,
        user_id: int
    ) -> ResourcePermission:
        """Create a resource-level permission."""
        resource_permission = ResourcePermission(
            permission_id=permission_id,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id
        )
        db.add(resource_permission)
        await db.commit()
        await db.refresh(resource_permission)
        return resource_permission
    
    @staticmethod
    async def get_resource_permissions(
        db: AsyncSession,
        resource_type: str,
        resource_id: int
    ) -> List[ResourcePermission]:
        """Get all permissions for a specific resource."""
        result = await db.execute(
            select(ResourcePermission)
            .where(
                ResourcePermission.resource_type == resource_type,
                ResourcePermission.resource_id == resource_id
            )
            .options(selectinload(ResourcePermission.permission))
        )
        return result.scalars().all()
    
    @staticmethod
    async def create_role(
        db: AsyncSession,
        name: str,
        description: Optional[str] = None
    ) -> Role:
        """Create a new role."""
        role = Role(name=name, description=description)
        db.add(role)
        await db.commit()
        await db.refresh(role)
        return role
    
    @staticmethod
    async def create_permission(
        db: AsyncSession,
        name: str,
        description: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> Permission:
        """Create a new permission."""
        permission = Permission(
            name=name,
            description=description,
            resource_type=resource_type
        )
        db.add(permission)
        await db.commit()
        await db.refresh(permission)
        return permission
    
    @staticmethod
    async def assign_permission_to_role(
        db: AsyncSession,
        role_id: int,
        permission_id: int
    ) -> None:
        """Assign a permission to a role."""
        result = await db.execute(
            select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
        )
        role = result.scalar_one_or_none()
        if not role:
            raise ValueError(f"Role {role_id} not found")
        
        result = await db.execute(
            select(Permission).where(Permission.id == permission_id)
        )
        permission = result.scalar_one_or_none()
        if not permission:
            raise ValueError(f"Permission {permission_id} not found")
        
        if permission not in role.permissions:
            role.permissions.append(permission)
            await db.commit()

