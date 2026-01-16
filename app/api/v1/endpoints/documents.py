from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_operator_id, get_document_service
from app.schemas.document import DocumentAccessResponse, DocumentResponse
from app.services.operator_service import OperatorService
from app.services.document_service import DocumentService
from app.services.audit_service import AuditService
from app.models.document import DocumentType
from app.models.audit_log import ActionType, UserType
from app.core.acl import require_resource_permission
from app.core.exceptions import AccessLinkInvalidException

router = APIRouter()


@router.get("/{access_token}", response_model=DocumentAccessResponse)
async def view_submission(
    access_token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    operator_id: int = Depends(get_current_operator_id),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    View form submission details and documents.
    Requires Google SSO authentication + access token validation + ACL permission.
    """
    # Validate access token
    try:
        access_link, form_submission = await OperatorService.get_access_link_with_submission(
            db, access_token
        )
    except AccessLinkInvalidException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired access link"
        )

    # Check ACL permission
    await require_resource_permission(
        db=db,
        user_id=operator_id,
        permission_name="view_document",
        resource_type="form_submission",
        resource_id=form_submission.id
    )

    # Get documents
    documents = await document_service.get_documents_by_submission(
        db, form_submission.id
    )

    # Log access
    await AuditService.log_action_background(
        background_tasks=background_tasks,
        db=db,
        action_type=ActionType.ACCESS_LINK_ACCESSED,
        user_type=UserType.OPERATOR,
        user_id=operator_id,
        resource_type="form_submission",
        resource_id=form_submission.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )

    return DocumentAccessResponse(
        form_submission_id=form_submission.id,
        cbu=form_submission.cbu,
        cuit=form_submission.cuit,
        email=form_submission.email,
        submitted_at=form_submission.submitted_at,
        status=form_submission.status,
        documents=[DocumentResponse.model_validate(doc) for doc in documents]
    )


@router.get("/{access_token}/documents/{document_id}/invoice/download")
async def download_invoice(
    access_token: str,
    document_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    operator_id: int = Depends(get_current_operator_id),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Download invoice document.
    Requires Google SSO + access token + ACL permission.
    Only invoice can be downloaded.
    """
    # Validate access token and get submission
    access_link, form_submission = await OperatorService.get_access_link_with_submission(
        db, access_token
    )

    # Get document
    document = await document_service.get_document(db, document_id)
    if not document or document.form_submission_id != form_submission.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Only invoice can be downloaded
    if document.document_type != DocumentType.INVOICE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only invoice documents can be downloaded. Use the view endpoint for other document types."
        )

    # Check ACL permission
    await require_resource_permission(
        db=db,
        user_id=operator_id,
        permission_name="download_document",
        resource_type="document",
        resource_id=document_id
    )

    # Get file path
    file_path = await document_service.get_document_file_path(db, document_id)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Log download
    await AuditService.log_action_background(
        background_tasks=background_tasks,
        db=db,
        action_type=ActionType.DOCUMENT_DOWNLOADED,
        user_type=UserType.OPERATOR,
        user_id=operator_id,
        resource_type="document",
        resource_id=document_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )

    return FileResponse(
        path=str(file_path),
        filename=document.file_name,
        media_type=document.mime_type
    )


@router.get("/{access_token}/documents/{document_id}/view")
async def view_document(
    access_token: str,
    document_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    operator_id: int = Depends(get_current_operator_id),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    View document (read-only, not invoice).
    Requires Google SSO + access token + ACL permission.
    """
    # Validate access token and get submission
    access_link, form_submission = await OperatorService.get_access_link_with_submission(
        db, access_token
    )

    # Get document
    document = await document_service.get_document(db, document_id)
    if not document or document.form_submission_id != form_submission.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Invoice should use download endpoint
    if document.document_type == DocumentType.INVOICE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use download endpoint for invoice"
        )

    # Check ACL permission
    await require_resource_permission(
        db=db,
        user_id=operator_id,
        permission_name="view_document",
        resource_type="document",
        resource_id=document_id
    )

    # Get file path
    file_path = await document_service.get_document_file_path(db, document_id)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Log view
    await AuditService.log_action_background(
        background_tasks=background_tasks,
        db=db,
        action_type=ActionType.DOCUMENT_VIEWED,
        user_type=UserType.OPERATOR,
        user_id=operator_id,
        resource_type="document",
        resource_id=document_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )

    return FileResponse(
        path=str(file_path),
        filename=document.file_name,
        media_type=document.mime_type
    )

