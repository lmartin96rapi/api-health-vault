import secrets
import json
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.form import Form, FormSubmission, FormStatus
from app.config import settings
from app.core.exceptions import (
    FormExpiredException,
    FormAlreadySubmittedException,
    InvalidFormTokenException,
    ExternalAPIException
)
from app.external.backend_client import BackendAPIClient
from app.external.wsp_api_client import WspAPIClient
from app.services.operator_service import OperatorService
from app.services.document_service import DocumentService, generate_document_url
from app.models.document import DocumentType
from app.core.logging_utils import mask_sensitive_data, sanitize_log_message

logger = logging.getLogger(__name__)


class FormService:
    """Service for form creation, validation, submission, expiration handling, and duplicate prevention."""
    
    def __init__(self):
        self.backend_client = BackendAPIClient()
        self.wsp_client = WspAPIClient()
        self.document_service = DocumentService()
    
    @staticmethod
    def _generate_form_token() -> str:
        """
        Generate a unique form token.
        
        Returns:
            Secure random token string
        """
        return secrets.token_urlsafe(32)
    
    @staticmethod
    async def create_form(
        db: AsyncSession,
        client_id: str,
        policy_id: str,
        service_id: int,
        name: str,
        dni: str,
        cbu: Optional[str] = None,
        cuit: Optional[str] = None,
        email: str = "",
        order_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Form:
        """
        Create a new form with unique token.
        
        Args:
            db: Database session
            client_id: Client ID
            policy_id: Policy ID (required for backend API)
            service_id: Service ID (required for backend API)
            name: Client name
            dni: Client DNI
            cbu: Client CBU (optional)
            cuit: Client CUIT (optional)
            email: Client email
            order_id: Order ID (optional)
            request_id: Request ID (UUID) for request tracing
            
        Returns:
            Created Form record
        """
        # Generate unique form token
        form_token = FormService._generate_form_token()
        
        # Calculate expiration (24h)
        expires_at = datetime.utcnow() + timedelta(hours=settings.FORM_EXPIRATION_HOURS)
        
        form = Form(
            form_token=form_token,
            client_id=client_id,
            policy_id=policy_id,
            service_id=service_id,
            name=name,
            dni=dni,
            cbu=cbu,
            cuit=cuit,
            email=email,
            order_id=order_id,
            status=FormStatus.PENDING,
            expires_at=expires_at
        )
        
        db.add(form)
        await db.commit()
        await db.refresh(form)
        
        # Log form creation with masked sensitive data
        masked_data = mask_sensitive_data({
            "client_id": client_id,
            "policy_id": policy_id,
            "service_id": service_id,
            "name": name,
            "dni": dni,
            "cbu": cbu,
            "cuit": cuit,
            "email": email,
            "order_id": order_id
        })
        
        logger.info(
            sanitize_log_message(
                "Form created",
                RequestID=request_id,
                FormID=form.id,
                FormToken=form.form_token,
                ExpiresAt=form.expires_at.isoformat(),
                Data=masked_data
            )
        )
        
        return form
    
    @staticmethod
    async def get_form_by_token(
        db: AsyncSession,
        form_token: str
    ) -> Optional[Form]:
        """
        Get form by token.
        
        Args:
            db: Database session
            form_token: Form token
            
        Returns:
            Form record or None
        """
        result = await db.execute(
            select(Form).where(Form.form_token == form_token)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def validate_form(
        db: AsyncSession,
        form_token: str
    ) -> Form:
        """
        Validate form token and expiration.
        
        Args:
            db: Database session
            form_token: Form token
            
        Returns:
            Form record if valid
            
        Raises:
            InvalidFormTokenException if token is invalid
            FormExpiredException if form has expired
            FormAlreadySubmittedException if form already submitted
        """
        form = await FormService.get_form_by_token(db, form_token)
        
        if not form:
            raise InvalidFormTokenException()
        
        # Check if already submitted
        if form.is_submitted:
            raise FormAlreadySubmittedException()
        
        # Check expiration
        if form.expires_at < datetime.utcnow():
            # Update status
            form.status = FormStatus.EXPIRED
            await db.commit()
            raise FormExpiredException()
        
        return form
    
    async def submit_form(
        self,
        db: AsyncSession,
        form_token: str,
        cbu: Optional[str] = None,
        cuit: Optional[str] = None,
        email: Optional[str] = None
    ) -> Tuple[FormSubmission, str]:
        """
        Submit a form with updated data.
        
        Args:
            db: Database session
            form_token: Form token
            cbu: Updated CBU (optional)
            cuit: Updated CUIT (optional)
            email: Updated email (optional)
            
        Returns:
            Tuple of (FormSubmission, access_token)
            
        Raises:
            FormExpiredException if form expired
            FormAlreadySubmittedException if already submitted
            ExternalAPIException if external API call fails
        """
        # Validate form
        form = await FormService.validate_form(db, form_token)
        
        # Use provided values or fall back to form defaults
        final_cbu = cbu if cbu is not None else form.cbu
        final_cuit = cuit if cuit is not None else form.cuit
        final_email = email if email is not None else form.email
        
        # Create form submission
        form_submission = FormSubmission(
            form_id=form.id,
            cbu=final_cbu,
            cuit=final_cuit,
            email=final_email
        )
        
        db.add(form_submission)
        await db.flush()  # Get ID without committing
        
        # Generate access link (needed for comment and invoice URL)
        access_link = await OperatorService.create_access_link(
            db=db,
            form_submission_id=form_submission.id,
            order_id=None  # Will be updated after backend API call
        )
        
        await db.commit()
        await db.refresh(form_submission)
        
        logger.info(
            sanitize_log_message(
                "Form submission created",
                FormSubmissionID=form_submission.id,
                FormID=form.id,
                AccessToken=access_link.access_token[:20] + "..." if access_link.access_token else None
            )
        )
        
        return form_submission, access_link.access_token
    
    async def call_backend_api(
        self,
        db: AsyncSession,
        form_submission_id: int,
        invoice_document_id: int,
        access_token: str
    ) -> None:
        """
        Call backend API to create/update order after documents are uploaded.
        
        Args:
            db: Database session
            form_submission_id: Form submission ID
            invoice_document_id: Invoice document ID
            access_token: Access token for generating URLs
        """
        # Get form submission and form
        from sqlalchemy import select
        from app.models.document import Document
        from app.models.document_access_link import DocumentAccessLink
        
        result = await db.execute(
            select(FormSubmission).where(FormSubmission.id == form_submission_id)
        )
        form_submission = result.scalar_one()
        
        result = await db.execute(
            select(Form).where(Form.id == form_submission.form_id)
        )
        form = result.scalar_one()
        
        # Get access link
        result = await db.execute(
            select(DocumentAccessLink).where(
                DocumentAccessLink.form_submission_id == form_submission_id
            )
        )
        access_link = result.scalar_one()
        
        # Get invoice document
        result = await db.execute(
            select(Document).where(Document.id == invoice_document_id)
        )
        invoice_document = result.scalar_one()
        
        try:
            logger.info(
                sanitize_log_message(
                    "Calling backend API for form submission",
                    FormSubmissionID=form_submission_id,
                    InvoiceDocumentID=invoice_document_id,
                    HasOrderID=form.order_id is not None,
                    OrderID=form.order_id
                )
            )
            
            # Generate invoice URL for backend API
            invoice_url = generate_document_url(
                access_token=access_token,
                document_id=invoice_document.id,
                document_type=DocumentType.INVOICE
            )
            
            # Generate comment with access link for operators
            access_link_url = f"{settings.API_BASE_URL.rstrip('/')}/api/v1/document-access/{access_token}"
            comment = f"Formulario enviado. Acceso: {access_link_url}"
            
            # Prepare backend API payload (matching backend API format)
            # Safely convert client_id and policy_id to int (handle string values)
            try:
                client_id_int = int(form.client_id) if form.client_id else None
            except (ValueError, TypeError):
                logger.warning(
                    sanitize_log_message(
                        "client_id is not a valid integer, using as string",
                        FormSubmissionID=form_submission_id,
                        ClientID=form.client_id
                    )
                )
                client_id_int = form.client_id  # Keep as string if conversion fails
            
            try:
                policy_id_int = int(form.policy_id) if form.policy_id else None
            except (ValueError, TypeError):
                logger.warning(
                    sanitize_log_message(
                        "policy_id is not a valid integer, using as string",
                        FormSubmissionID=form_submission_id,
                        PolicyID=form.policy_id
                    )
                )
                policy_id_int = form.policy_id  # Keep as string if conversion fails
            
            order_data = {
                "client_id": client_id_int,  # Backend expects integer (or string if conversion fails)
                "policy_id": policy_id_int,  # Backend expects integer (or string if conversion fails)
                "form_type": "REINTEGRO",
                "service_id": form.service_id,
                "factura": invoice_url,
                "request_origin": 13,  # Default for bot
                "organization_id": settings.ORGANIZATION_ID,
                "comment": comment
            }
            
            # Add optional fields if provided
            if form_submission.email:
                order_data["email_asegurado"] = form_submission.email
            if form_submission.cuit:
                order_data["cuit_cuil_asegurado"] = form_submission.cuit
            if form_submission.cbu:
                order_data["cbu_asegurado"] = form_submission.cbu
            
            # Mask sensitive data for logging
            masked_order_data = mask_sensitive_data(order_data)
            logger.debug(
                sanitize_log_message(
                    "Backend API payload prepared",
                    FormSubmissionID=form_submission_id,
                    Payload=masked_order_data
                )
            )
            
            # Determine if we need to create or update
            if form.order_id:
                # Update existing order (skip for now as per requirements)
                logger.info(
                    sanitize_log_message(
                        "Updating existing order in backend",
                        FormSubmissionID=form_submission_id,
                        OrderID=form.order_id
                    )
                )
                external_response = await self.backend_client.update_reintegro(
                    reintegro_id=form.order_id,
                    update_data=order_data
                )
                final_order_id = form.order_id  # Keep existing order_id
            else:
                # Create new order
                logger.info(
                    sanitize_log_message(
                        "Creating new order in backend",
                        FormSubmissionID=form_submission_id
                    )
                )
                external_response = await self.backend_client.create_reintegro(order_data)
                # Extract pedido_id from response "id" field
                final_order_id = str(external_response.get("id"))  # Backend returns "id" as pedido_id
                
                # Update form with the new order_id
                if final_order_id:
                    form.order_id = final_order_id
                    logger.info(
                        sanitize_log_message(
                            "Order created in backend",
                            FormSubmissionID=form_submission_id,
                            OrderID=final_order_id
                        )
                    )
            
            # Update access link with order_id
            access_link.order_id = final_order_id
            
            # Store external API response
            form_submission.external_ws_response = json.dumps(external_response)
            form_submission.status = external_response.get("status_request", "pending")
            
            # Update form
            form.is_submitted = True
            form.submitted_at = datetime.utcnow()
            form.status = FormStatus.SUBMITTED
            
            await db.commit()
            await db.refresh(form_submission)
            
            logger.info(
                sanitize_log_message(
                    "Backend API call completed successfully",
                    FormSubmissionID=form_submission_id,
                    OrderID=final_order_id,
                    Status=form_submission.status
                )
            )
            
            # Send WhatsApp notification (non-blocking, don't fail if it fails)
            #try:
            #    await self.wsp_client.send_submission_confirmation(
            #        phone_number=form.email,  # Adjust based on actual phone field
            #        client_name=form.name,
            #        access_link=f"{access_link.access_token}"
            #    )
            #except Exception:
            #    # Log error but don't fail the submission
            #    pass
            
            return form_submission, access_link.access_token
            
        except ExternalAPIException as e:
            # Log external API exception
            logger.error(
                sanitize_log_message(
                    "Backend API call failed (ExternalAPIException)",
                    FormSubmissionID=form_submission_id,
                    Error=str(e),
                    Detail=e.detail if hasattr(e, 'detail') else None
                ),
                exc_info=True
            )
            # Rollback on external API failure
            await db.rollback()
            raise e
        except Exception as e:
            # Log unexpected exception with full traceback
            logger.exception(
                sanitize_log_message(
                    "Unexpected error in backend API call",
                    FormSubmissionID=form_submission_id,
                    ErrorType=type(e).__name__,
                    ErrorMessage=str(e) or repr(e)
                )
            )
            # Rollback on any other error
            await db.rollback()
            # Clean up any uploaded documents (use form_submission_id parameter, not form_submission.id)
            try:
                await self.document_service.cleanup_failed_uploads(db, form_submission_id)
            except Exception as cleanup_error:
                logger.error(
                    sanitize_log_message(
                        "Failed to cleanup documents after backend API error",
                        FormSubmissionID=form_submission_id,
                        CleanupError=str(cleanup_error)
                    )
                )
            error_message = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
            raise ExternalAPIException(detail=f"Form submission failed: {error_message}")
    
    @staticmethod
    async def get_form_status(
        db: AsyncSession,
        form_token: str
    ) -> Dict[str, Any]:
        """
        Get form status and details.
        
        Args:
            db: Database session
            form_token: Form token
            
        Returns:
            Dictionary with form status information
        """
        form = await FormService.get_form_by_token(db, form_token)
        
        if not form:
            raise InvalidFormTokenException()
        
        is_expired = form.expires_at < datetime.utcnow()
        
        return {
            "form_token": form.form_token,
            "status": form.status.value,
            "is_submitted": form.is_submitted,
            "is_expired": is_expired,
            "created_at": form.created_at.isoformat() if form.created_at else None,
            "expires_at": form.expires_at.isoformat() if form.expires_at else None,
            "submitted_at": form.submitted_at.isoformat() if form.submitted_at else None,
        }

