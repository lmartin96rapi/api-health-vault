import os
import logging
import aiofiles
import asyncio
import uuid
import re
from datetime import datetime
from typing import List, Optional, Tuple
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import UploadFile
from app.models.document import Document, DocumentType
from app.models.form import FormSubmission
from app.config import settings
from app.core.exceptions import DocumentUploadException
from app.core.logging_utils import sanitize_log_message

# Timeout for file operations (30 seconds)
FILE_OPERATION_TIMEOUT = 30

logger = logging.getLogger(__name__)


def generate_document_url(access_token: str, document_id: int, document_type: DocumentType) -> str:
    """
    Generate public URL for a document to be sent to backend API.
    
    Args:
        access_token: Access token for the form submission
        document_id: ID of the document
        document_type: Type of document (invoice, prescription, diagnosis)
        
    Returns:
        Full URL to access the document
    """
    base_url = settings.API_BASE_URL.rstrip('/')
    
    if document_type == DocumentType.INVOICE:
        # Invoice can be downloaded
        return f"{base_url}/api/v1/document-access/{access_token}/documents/{document_id}/invoice/download"
    else:
        # Other documents are view-only
        return f"{base_url}/api/v1/document-access/{access_token}/documents/{document_id}/view"


class DocumentService:
    """Service for document upload, storage, validation, and retrieval."""

    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.allowed_types = settings.ALLOWED_FILE_TYPES
        self.max_file_size = settings.MAX_FILE_SIZE

    def _sanitize_filename(self, original_filename: str) -> Tuple[str, str]:
        """
        Sanitize filename for secure storage.

        Generates a UUID-based filename for storage while preserving
        the original filename for display purposes.

        Args:
            original_filename: Original filename from upload

        Returns:
            Tuple of (safe_storage_name, sanitized_display_name)
        """
        # Extract extension safely
        if original_filename:
            # Remove any path components (prevent path traversal)
            clean_name = os.path.basename(original_filename)
            # Remove path traversal patterns
            clean_name = re.sub(r'\.\.[\\/]', '', clean_name)
            clean_name = re.sub(r'[\\/]', '', clean_name)
            # Get extension
            ext = Path(clean_name).suffix.lower()
            # Whitelist allowed extensions
            allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png'}
            if ext not in allowed_extensions:
                ext = ''
        else:
            clean_name = 'unnamed'
            ext = ''

        # Generate UUID-based storage name
        safe_storage_name = f"{uuid.uuid4().hex}{ext}"

        # Sanitize display name (remove control characters, limit length)
        display_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', clean_name)
        display_name = display_name[:255]  # Limit length

        return safe_storage_name, display_name

    def _get_document_path(
        self,
        form_submission_id: int,
        document_type: DocumentType,
        storage_filename: str
    ) -> Path:
        """
        Get the file path for a document.
        Structure: {base_path}/{form_submission_id}/{document_type}/{storage_filename}

        Args:
            form_submission_id: ID of the form submission
            document_type: Type of document
            storage_filename: Safe UUID-based filename for storage

        Returns:
            Path object for the file
        """
        doc_dir = self.upload_dir / str(form_submission_id) / document_type.value
        doc_dir.mkdir(parents=True, exist_ok=True)
        return doc_dir / storage_filename
    
    def _validate_file_type(self, mime_type: str) -> bool:
        """
        Validate if file type is allowed.
        
        Args:
            mime_type: MIME type of the file
            
        Returns:
            True if allowed, False otherwise
        """
        return mime_type in self.allowed_types
    
    async def upload_document(
        self,
        db: AsyncSession,
        form_submission_id: int,
        document_type: DocumentType,
        file: UploadFile
    ) -> Document:
        """
        Upload a document and save it to the filesystem.

        Args:
            db: Database session
            form_submission_id: ID of the form submission
            document_type: Type of document
            file: Uploaded file

        Returns:
            Created Document record

        Raises:
            DocumentUploadException if upload fails
        """
        # Validate file type
        if not self._validate_file_type(file.content_type):
            raise DocumentUploadException(
                detail=f"File type {file.content_type} is not allowed. Allowed types: {self.allowed_types}"
            )

        # Read file content first to validate size before writing
        content = await file.read()
        file_size = len(content)

        # Validate file size BEFORE writing to disk
        if file_size > self.max_file_size:
            raise DocumentUploadException(
                detail=f"File size ({file_size} bytes) exceeds maximum allowed size ({self.max_file_size} bytes)"
            )

        if file_size == 0:
            raise DocumentUploadException(
                detail="File is empty"
            )

        # Sanitize filename for secure storage
        storage_filename, display_filename = self._sanitize_filename(file.filename)

        # Get file path with sanitized storage filename
        file_path = self._get_document_path(
            form_submission_id=form_submission_id,
            document_type=document_type,
            storage_filename=storage_filename
        )

        try:
            # Save file to filesystem with timeout protection
            try:
                async with aiofiles.open(file_path, 'wb') as f:
                    await asyncio.wait_for(
                        f.write(content),
                        timeout=FILE_OPERATION_TIMEOUT
                    )
            except asyncio.TimeoutError:
                raise DocumentUploadException(
                    detail=f"File write operation timed out after {FILE_OPERATION_TIMEOUT} seconds"
                )

            # Create document record with sanitized display name
            document = Document(
                form_submission_id=form_submission_id,
                document_type=document_type,
                file_path=str(file_path),
                file_name=display_filename,
                file_size=file_size,
                mime_type=file.content_type
            )

            db.add(document)
            await db.commit()
            await db.refresh(document)

            logger.info(
                sanitize_log_message(
                    "Document uploaded successfully",
                    document_id=document.id,
                    form_submission_id=form_submission_id,
                    document_type=document_type.value,
                    storage_filename=storage_filename,
                    display_filename=display_filename,
                    file_size=file_size
                )
            )

            return document

        except Exception as e:
            # Clean up file if database operation fails
            if file_path.exists():
                os.remove(file_path)
            raise DocumentUploadException(
                detail=f"Failed to upload document: {str(e)}"
            )
    
    async def get_document(
        self,
        db: AsyncSession,
        document_id: int,
        include_deleted: bool = False
    ) -> Optional[Document]:
        """
        Get a document by ID.

        Args:
            db: Database session
            document_id: ID of the document
            include_deleted: If True, include soft-deleted documents

        Returns:
            Document record or None
        """
        query = select(Document).where(Document.id == document_id)
        if not include_deleted:
            query = query.where(Document.is_deleted == False)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_documents_by_submission(
        self,
        db: AsyncSession,
        form_submission_id: int,
        include_deleted: bool = False
    ) -> List[Document]:
        """
        Get all documents for a form submission.

        Args:
            db: Database session
            form_submission_id: ID of the form submission
            include_deleted: If True, include soft-deleted documents

        Returns:
            List of Document records
        """
        query = select(Document).where(Document.form_submission_id == form_submission_id)
        if not include_deleted:
            query = query.where(Document.is_deleted == False)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_document_file_path(
        self,
        db: AsyncSession,
        document_id: int
    ) -> Optional[Path]:
        """
        Get the file path for a document.

        Args:
            db: Database session
            document_id: ID of the document

        Returns:
            Path object or None
        """
        document = await self.get_document(db, document_id)
        if not document:
            return None

        file_path = Path(document.file_path)
        if not file_path.exists():
            return None

        return file_path

    async def delete_document(
        self,
        db: AsyncSession,
        document_id: int,
        hard_delete: bool = False
    ) -> bool:
        """
        Delete a document (soft delete by default).

        Args:
            db: Database session
            document_id: ID of the document
            hard_delete: If True, permanently delete the document and file

        Returns:
            True if deleted, False otherwise
        """
        document = await self.get_document(db, document_id, include_deleted=hard_delete)
        if not document:
            return False

        if hard_delete:
            # Hard delete: remove file and database record
            file_path = Path(document.file_path)
            if file_path.exists():
                os.remove(file_path)
            await db.delete(document)
        else:
            # Soft delete: mark as deleted, keep file for audit/recovery
            document.soft_delete()

        await db.commit()

        logger.info(
            sanitize_log_message(
                "Document deleted",
                document_id=document_id,
                hard_delete=hard_delete
            )
        )

        return True

    async def cleanup_failed_uploads(
        self,
        db: AsyncSession,
        form_submission_id: int,
        hard_delete: bool = True
    ) -> None:
        """
        Clean up files for a form submission if upload fails.

        Args:
            db: Database session
            form_submission_id: ID of the form submission
            hard_delete: If True, permanently delete (default for failed uploads)
        """
        # For failed uploads, include all documents (even soft-deleted ones)
        documents = await self.get_documents_by_submission(
            db, form_submission_id, include_deleted=True
        )

        for document in documents:
            if hard_delete:
                # Hard delete for failed uploads - remove files
                file_path = Path(document.file_path)
                if file_path.exists():
                    os.remove(file_path)
                await db.delete(document)
            else:
                # Soft delete
                document.soft_delete()

        await db.commit()

        logger.info(
            sanitize_log_message(
                "Cleaned up failed uploads",
                form_submission_id=form_submission_id,
                document_count=len(documents),
                hard_delete=hard_delete
            )
        )

