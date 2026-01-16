import secrets
from typing import Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.operator import Operator
from app.models.document_access_link import DocumentAccessLink
from app.models.form import FormSubmission
from app.config import settings
from app.core.security import verify_google_token
from app.core.exceptions import AccessLinkExpiredException, AccessLinkInvalidException


class OperatorService:
    """Service for operator management, Google SSO validation, and access link generation."""
    
    @staticmethod
    async def get_operator_by_email(
        db: AsyncSession,
        email: str
    ) -> Optional[Operator]:
        """
        Get operator by Google email.
        
        Args:
            db: Database session
            email: Google email address
            
        Returns:
            Operator record or None
        """
        result = await db.execute(
            select(Operator).where(Operator.google_email == email)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_operator_by_id(
        db: AsyncSession,
        operator_id: int
    ) -> Optional[Operator]:
        """
        Get operator by ID.
        
        Args:
            db: Database session
            operator_id: Operator ID
            
        Returns:
            Operator record or None
        """
        result = await db.execute(
            select(Operator).where(Operator.id == operator_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def validate_google_sso(
        db: AsyncSession,
        google_token: str
    ) -> Optional[Operator]:
        """
        Validate Google SSO token and return operator if authorized.
        
        Args:
            db: Database session
            google_token: Google ID token
            
        Returns:
            Operator record if valid and authorized, None otherwise
        """
        # Verify Google token
        user_info = await verify_google_token(google_token)
        if not user_info:
            return None
        
        email = user_info.get("email")
        if not email:
            return None
        
        # Check if operator exists and is active
        operator = await OperatorService.get_operator_by_email(db, email)
        if not operator or not operator.is_active:
            return None
        
        return operator
    
    @staticmethod
    def _generate_access_token() -> str:
        """
        Generate a secure random access token (long random hash).
        
        Returns:
            Secure random token string
        """
        # Generate 64-byte random token (512 bits)
        return secrets.token_urlsafe(64)
    
    @staticmethod
    async def create_access_link(
        db: AsyncSession,
        form_submission_id: int,
        order_id: Optional[str] = None,
        created_by: Optional[int] = None
    ) -> DocumentAccessLink:
        """
        Create an access link for a form submission.
        Automatically called when form is submitted.
        Access tokens are permanent (no expiration) for operator access.
        
        Args:
            db: Database session
            form_submission_id: ID of the form submission
            order_id: pedido_id from backend API (links access token to order)
            created_by: ID of the operator who created it (None for auto-generated)
            
        Returns:
            Created DocumentAccessLink record
        """
        # Generate secure access token
        access_token = OperatorService._generate_access_token()
        
        # Permanent access for operators (no expiration)
        expires_at = None
        
        access_link = DocumentAccessLink(
            form_submission_id=form_submission_id,
            access_token=access_token,
            order_id=order_id,
            created_by=created_by,
            expires_at=expires_at,
            is_active=True
        )
        
        db.add(access_link)
        await db.commit()
        await db.refresh(access_link)
        
        return access_link
    
    @staticmethod
    async def validate_access_link(
        db: AsyncSession,
        access_token: str
    ) -> DocumentAccessLink:
        """
        Validate an access link token.
        
        Args:
            db: Database session
            access_token: Access token to validate
            
        Returns:
            DocumentAccessLink record if valid
            
        Raises:
            AccessLinkInvalidException if token is invalid
            AccessLinkExpiredException if token has expired
        """
        result = await db.execute(
            select(DocumentAccessLink).where(DocumentAccessLink.access_token == access_token)
        )
        access_link = result.scalar_one_or_none()
        
        if not access_link:
            raise AccessLinkInvalidException()
        
        if not access_link.is_active:
            raise AccessLinkInvalidException(detail="Access link is inactive")
        
        # Check expiration (only if expires_at is set - permanent tokens have expires_at = None)
        if access_link.expires_at is not None and access_link.expires_at < datetime.utcnow():
            raise AccessLinkExpiredException()
        
        return access_link
    
    @staticmethod
    async def get_access_link_with_submission(
        db: AsyncSession,
        access_token: str
    ) -> Tuple[DocumentAccessLink, FormSubmission]:
        """
        Get access link with its associated form submission.
        
        Args:
            db: Database session
            access_token: Access token
            
        Returns:
            Tuple of (DocumentAccessLink, FormSubmission)
            
        Raises:
            AccessLinkInvalidException if token is invalid
        """
        access_link = await OperatorService.validate_access_link(db, access_token)
        
        result = await db.execute(
            select(FormSubmission).where(FormSubmission.id == access_link.form_submission_id)
        )
        form_submission = result.scalar_one_or_none()
        
        if not form_submission:
            raise AccessLinkInvalidException(detail="Form submission not found")
        
        return access_link, form_submission
    
    @staticmethod
    async def create_operator(
        db: AsyncSession,
        google_email: str,
        name: str
    ) -> Operator:
        """
        Create a new operator.
        
        Args:
            db: Database session
            google_email: Google email address
            name: Operator name
            
        Returns:
            Created Operator record
        """
        operator = Operator(
            google_email=google_email,
            name=name,
            is_active=True
        )
        
        db.add(operator)
        await db.commit()
        await db.refresh(operator)
        
        return operator

