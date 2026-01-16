import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.form import (
    FormCreateRequest,
    FormCreateResponse,
    FormStatusResponse,
    FormSubmitRequest,
    FormSubmitResponse,
    FormDetailResponse,
)
from app.schemas.document import DocumentResponse
from app.services.form_service import FormService
from app.services.document_service import DocumentService
from app.models.document import DocumentType
from app.models.audit_log import ActionType
from fastapi import UploadFile, File, Form
from app.core.api_key import validate_api_key
from app.models.api_key import ApiKey
from app.core.logging_utils import sanitize_log_message, get_request_id
from app.api.deps import AuditContext, get_audit_context, get_audit_context_with_api_key

logger = logging.getLogger(__name__)

router = APIRouter()
form_service = FormService()
document_service = DocumentService()


@router.post("", response_model=FormCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_form(
    request: FormCreateRequest,
    audit_context: AuditContext = Depends(get_audit_context_with_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new form and return form URL.
    Requires API key authentication.
    """
    form = await FormService.create_form(
        db=db,
        client_id=request.client_id,
        policy_id=request.policy_id,
        service_id=request.service_id,
        name=request.name,
        dni=request.dni,
        cbu=request.cbu,
        cuit=request.cuit,
        email=request.email,
        order_id=request.order_id,
        request_id=audit_context.request_id
    )
    
    # Generate form URL (adjust base URL as needed)
    form_url = f"/forms/{form.form_token}"
    
    # Log action using audit context
    await audit_context.log_action(
        action_type=ActionType.FORM_CREATED,
        resource_type="form",
        resource_id=form.id,
        request_data=request.dict()
    )
    
    return FormCreateResponse(
        form_url=form_url,
        form_token=form.form_token,
        expires_at=form.expires_at
    )


@router.get("/{form_token}", response_model=FormDetailResponse)
async def get_form(
    form_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get form details by token.
    Public endpoint for form validation.
    """
    form = await FormService.get_form_by_token(db, form_token)
    
    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found"
        )
    
    return FormDetailResponse(
        form_token=form.form_token,
        name=form.name,
        dni=form.dni,
        cbu=form.cbu,
        cuit=form.cuit,
        email=form.email,
        status=form.status.value,
        is_submitted=form.is_submitted,
        expires_at=form.expires_at
    )


@router.get("/{form_token}/status", response_model=FormStatusResponse)
async def get_form_status(
    form_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get form status.
    Public endpoint.
    """
    return await FormService.get_form_status(db, form_token)


@router.post("/{form_token}/submit", response_model=FormSubmitResponse, status_code=status.HTTP_201_CREATED)
async def submit_form(
    form_token: str,
    invoice: UploadFile = File(...),
    prescription: UploadFile = File(...),
    diagnosis: List[UploadFile] = File(default=[]),
    cbu: Optional[str] = Form(None),
    cuit: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    audit_context: AuditContext = Depends(get_audit_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a form with documents.
    Public endpoint (no authentication required for form submission).
    """
    # Create form submission first (without backend API call)
    form_submission, access_token = await form_service.submit_form(
        db=db,
        form_token=form_token,
        cbu=cbu,
        cuit=cuit,
        email=email
    )
    
    # Capture IDs before try block to avoid session issues in exception handler
    form_submission_id = form_submission.id if form_submission else None
    request_id = audit_context.request_id
    
    uploaded_documents = []
    
    try:
        # Upload invoice (required)
        invoice_doc = await document_service.upload_document(
            db=db,
            form_submission_id=form_submission.id,
            document_type=DocumentType.INVOICE,
            file=invoice
        )
        uploaded_documents.append(invoice_doc)
        
        # Upload prescription (required)
        prescription_doc = await document_service.upload_document(
            db=db,
            form_submission_id=form_submission.id,
            document_type=DocumentType.PRESCRIPTION,
            file=prescription
        )
        uploaded_documents.append(prescription_doc)
        
        # Upload diagnosis documents (optional, up to 3)
        for i, diag_file in enumerate(diagnosis[:3]):
            diag_doc = await document_service.upload_document(
                db=db,
                form_submission_id=form_submission.id,
                document_type=DocumentType.DIAGNOSIS,
                file=diag_file
            )
            uploaded_documents.append(diag_doc)
        
        # Now call backend API with invoice URL (after documents are uploaded)
        await form_service.call_backend_api(
            db=db,
            form_submission_id=form_submission.id,
            invoice_document_id=invoice_doc.id,
            access_token=access_token
        )
        
        # Log actions using audit context
        await audit_context.log_action(
            action_type=ActionType.FORM_SUBMITTED,
            resource_type="form_submission",
            resource_id=form_submission.id,
            request_data={"form_token": form_token}
        )
        
        for doc in uploaded_documents:
            await audit_context.log_action(
                action_type=ActionType.DOCUMENT_UPLOADED,
                resource_type="document",
                resource_id=doc.id
            )
        
        return FormSubmitResponse(
            submission_id=form_submission.id,
            access_token=access_token
        )
        
    except Exception as e:
        # Log the exception with full traceback and request ID
        logger.exception(
            sanitize_log_message(
                "Form submission failed",
                RequestID=request_id,
                FormToken=form_token,
                FormSubmissionID=form_submission_id,
                IP=audit_context.ip_address,
                ErrorType=type(e).__name__,
                ErrorMessage=str(e) or repr(e)
            )
        )
        
        # Clean up on failure
        if form_submission_id:
            try:
                await document_service.cleanup_failed_uploads(db, form_submission_id)
            except Exception as cleanup_error:
                logger.error(
                    sanitize_log_message(
                        "Failed to cleanup documents after form submission error",
                        RequestID=request_id,
                        FormSubmissionID=form_submission_id,
                        CleanupError=str(cleanup_error)
                    )
                )
        
        # Raise HTTP exception with error message
        error_message = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Form submission failed: {error_message}"
        )

