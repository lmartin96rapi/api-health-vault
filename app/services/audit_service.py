import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from fastapi import BackgroundTasks
from app.models.audit_log import AuditLog, ActionType, UserType
from app.config import settings

logger = logging.getLogger(__name__)


class AuditService:
    """Service for async audit logging with background task processing."""
    
    @staticmethod
    async def log_action(
        db: AsyncSession,
        action_type: ActionType,
        user_type: UserType,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> AuditLog:
        """
        Log an action to the audit log asynchronously.
        
        Args:
            db: Database session
            action_type: Type of action
            user_type: Type of user (operator, api_key, system)
            user_id: ID of the user
            resource_type: Type of resource affected
            resource_id: ID of the resource
            ip_address: IP address of the request
            user_agent: User agent string
            request_data: Request payload (JSON)
            response_data: Response payload (JSON)
            status: Status of the action (success/error)
            error_message: Error message if status is error
            request_id: Request ID (UUID) for request tracing
            
        Returns:
            Created AuditLog record
        """
        audit_log = AuditLog(
            action_type=action_type,
            user_type=user_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_data=request_data,
            response_data=response_data,
            status=status,
            error_message=error_message,
            request_id=request_id
        )
        
        try:
            db.add(audit_log)
            await db.commit()
            await db.refresh(audit_log)
            
            # Log to Python logger if it's an error
            if status == "error" and error_message:
                logger.error(
                    f"Audit log error: {action_type.value} - {error_message}",
                    extra={
                        "action_type": action_type.value,
                        "user_type": user_type.value,
                        "user_id": user_id,
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "request_id": request_id
                    }
                )
            else:
                logger.debug(
                    f"Audit log: {action_type.value}",
                    extra={
                        "action_type": action_type.value,
                        "user_type": user_type.value,
                        "user_id": user_id,
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "status": status,
                        "request_id": request_id
                    }
                )
            
            return audit_log
        except Exception as e:
            # Log audit logging failures to Python logger
            logger.exception(
                f"Failed to write audit log: {str(e)}",
                extra={
                    "action_type": action_type.value if action_type else None,
                    "user_type": user_type.value if user_type else None,
                    "error": str(e)
                }
            )
            raise
    
    @staticmethod
    async def log_action_background(
        background_tasks: BackgroundTasks,
        db: AsyncSession,
        action_type: ActionType,
        user_type: UserType,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> None:
        """
        Schedule audit logging as a background task (non-blocking).
        
        Args:
            background_tasks: FastAPI BackgroundTasks instance
            db: Database session
            action_type: Type of action
            user_type: Type of user
            user_id: ID of the user
            resource_type: Type of resource affected
            resource_id: ID of the resource
            ip_address: IP address of the request
            user_agent: User agent string
            request_data: Request payload (JSON)
            response_data: Response payload (JSON)
            status: Status of the action (success/error)
            error_message: Error message if status is error
            request_id: Request ID (UUID) for request tracing
        """
        background_tasks.add_task(
            AuditService.log_action,
            db=db,
            action_type=action_type,
            user_type=user_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_data=request_data,
            response_data=response_data,
            status=status,
            error_message=error_message,
            request_id=request_id
        )
    
    @staticmethod
    async def get_audit_logs(
        db: AsyncSession,
        action_type: Optional[ActionType] = None,
        user_type: Optional[UserType] = None,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        status: Optional[str] = None,
        request_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[AuditLog]:
        """
        Query audit logs with filters.
        
        Args:
            db: Database session
            action_type: Filter by action type
            user_type: Filter by user type
            user_id: Filter by user ID
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            status: Filter by status
            request_id: Filter by request ID (UUID)
            start_date: Start date for filtering
            end_date: End date for filtering
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of AuditLog records
        """
        query = select(AuditLog)
        
        conditions = []
        
        if action_type:
            conditions.append(AuditLog.action_type == action_type)
        if user_type:
            conditions.append(AuditLog.user_type == user_type)
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
        if resource_id:
            conditions.append(AuditLog.resource_id == resource_id)
        if status:
            conditions.append(AuditLog.status == status)
        if request_id:
            conditions.append(AuditLog.request_id == request_id)
        if start_date:
            conditions.append(AuditLog.created_at >= start_date)
        if end_date:
            conditions.append(AuditLog.created_at <= end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        return result.scalars().all()

