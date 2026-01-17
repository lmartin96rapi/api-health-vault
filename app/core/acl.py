import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from app.models.acl import Role, Permission, UserRole, ResourcePermission
from app.models.operator import Operator
from app.core.exceptions import PermissionDeniedException

logger = logging.getLogger(__name__)


async def check_endpoint_permission(
    db: AsyncSession,
    user_id: int,
    permission_name: str
) -> bool:
    """
    Check if user has endpoint-level permission.
    
    Args:
        db: Database session
        user_id: Operator ID
        permission_name: Name of the permission (e.g., "create_form", "view_document")
        
    Returns:
        True if user has permission, False otherwise
    """
    # Check if user is superadmin - bypass all ACL checks
    result = await db.execute(
        select(Operator).where(Operator.id == user_id)
    )
    operator = result.scalar_one_or_none()
    if operator and operator.is_superadmin:
        logger.warning(
            f"SUPERADMIN_BYPASS | user_id={user_id} | permission={permission_name} | email={operator.google_email}"
        )
        return True  # Superadmin bypasses all ACL checks

    # Get user's roles
    result = await db.execute(
        select(UserRole)
        .where(UserRole.user_id == user_id)
        .options(selectinload(UserRole.role).selectinload(Role.permissions))
    )
    user_roles = result.scalars().all()
    
    # Check if any role has the permission
    for user_role in user_roles:
        role = user_role.role
        if not role.is_active:
            continue
        
        for permission in role.permissions:
            if permission.is_active and permission.name == permission_name:
                return True
    
    return False


async def check_resource_permission(
    db: AsyncSession,
    user_id: int,
    permission_name: str,
    resource_type: str,
    resource_id: int
) -> bool:
    """
    Check if user has resource-level permission.
    
    Args:
        db: Database session
        user_id: Operator ID
        permission_name: Name of the permission
        resource_type: Type of resource (e.g., "form_submission", "document")
        resource_id: ID of the specific resource
        
    Returns:
        True if user has permission, False otherwise
    """
    # Check if user is superadmin - bypass all ACL checks
    result = await db.execute(
        select(Operator).where(Operator.id == user_id)
    )
    operator = result.scalar_one_or_none()
    if operator and operator.is_superadmin:
        logger.warning(
            f"SUPERADMIN_BYPASS | user_id={user_id} | permission={permission_name} | "
            f"resource={resource_type}:{resource_id} | email={operator.google_email}"
        )
        return True  # Superadmin bypasses all ACL checks

    # First check endpoint permission
    has_endpoint_permission = await check_endpoint_permission(db, user_id, permission_name)
    if has_endpoint_permission:
        return True
    
    # Then check resource-specific permission
    result = await db.execute(
        select(ResourcePermission)
        .where(
            and_(
                ResourcePermission.user_id == user_id,
                ResourcePermission.permission_id.in_(
                    select(Permission.id).where(Permission.name == permission_name)
                ),
                ResourcePermission.resource_type == resource_type,
                ResourcePermission.resource_id == resource_id
            )
        )
        .options(selectinload(ResourcePermission.permission))
    )
    resource_permission = result.scalar_one_or_none()
    
    if resource_permission:
        permission = resource_permission.permission
        if permission.is_active:
            return True
    
    return False


async def require_endpoint_permission(
    db: AsyncSession,
    user_id: int,
    permission_name: str
) -> None:
    """
    Require endpoint permission or raise exception.
    
    Args:
        db: Database session
        user_id: Operator ID
        permission_name: Name of the permission
        
    Raises:
        PermissionDeniedException if user doesn't have permission
    """
    has_permission = await check_endpoint_permission(db, user_id, permission_name)
    if not has_permission:
        raise PermissionDeniedException(
            detail=f"User does not have permission: {permission_name}"
        )


async def require_resource_permission(
    db: AsyncSession,
    user_id: int,
    permission_name: str,
    resource_type: str,
    resource_id: int
) -> None:
    """
    Require resource permission or raise exception.
    
    Args:
        db: Database session
        user_id: Operator ID
        permission_name: Name of the permission
        resource_type: Type of resource
        resource_id: ID of the specific resource
        
    Raises:
        PermissionDeniedException if user doesn't have permission
    """
    has_permission = await check_resource_permission(
        db, user_id, permission_name, resource_type, resource_id
    )
    if not has_permission:
        raise PermissionDeniedException(
            detail=f"User does not have permission: {permission_name} for {resource_type}:{resource_id}"
        )

