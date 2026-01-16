import os
import logging
import aiofiles
from typing import List, Optional
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import UploadFile
from app.models.document import Document, DocumentType
from app.models.form import FormSubmission
from app.config import settings
from app.core.exceptions import DocumentUploadException
from app.core.logging_utils import sanitize_log_message

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
    
    def _get_document_path(
        self,
        form_submission_id: int,
        document_type: DocumentType,
        filename: str
    ) -> Path:
        """
        Get the file path for a document.
        Structure: {base_path}/{form_submission_id}/{document_type}/{filename}
        
        Args:
            form_submission_id: ID of the form submission
            document_type: Type of document
            filename: Name of the file
            
        Returns:
            Path object for the file
        """
        doc_dir = self.upload_dir / str(form_submission_id) / document_type.value
        doc_dir.mkdir(parents=True, exist_ok=True)
        return doc_dir / filename
    
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
        
        # Get file path
        file_path = self._get_document_path(
            form_submission_id=form_submission_id,
            document_type=document_type,
            filename=file.filename
        )
        
        try:
            # Save file to filesystem
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Create document record
            document = Document(
                form_submission_id=form_submission_id,
                document_type=document_type,
                file_path=str(file_path),
                file_name=file.filename,
                file_size=file_size,
                mime_type=file.content_type
            )
            
            db.add(document)
            await db.commit()
            await db.refresh(document)
            
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
        document_id: int
    ) -> Optional[Document]:
        """
        Get a document by ID.
        
        Args:
            db: Database session
            document_id: ID of the document
            
        Returns:
            Document record or None
        """
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()
    
    async def get_documents_by_submission(
        self,
        db: AsyncSession,
        form_submission_id: int
    ) -> List[Document]:
        """
        Get all documents for a form submission.
        
        Args:
            db: Database session
            form_submission_id: ID of the form submission
            
        Returns:
            List of Document records
        """
        result = await db.execute(
            select(Document).where(Document.form_submission_id == form_submission_id)
        )
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
        document_id: int
    ) -> bool:
        """
        Delete a document and its file.
        
        Args:
            db: Database session
            document_id: ID of the document
            
        Returns:
            True if deleted, False otherwise
        """
        document = await self.get_document(db, document_id)
        if not document:
            return False
        
        file_path = Path(document.file_path)
        
        # Delete file from filesystem
        if file_path.exists():
            os.remove(file_path)
        
        # Delete database record
        await db.delete(document)
        await db.commit()
        
        return True
    
    async def cleanup_failed_uploads(
        self,
        db: AsyncSession,
        form_submission_id: int
    ) -> None:
        """
        Clean up files for a form submission if upload fails.
        
        Args:
            db: Database session
            form_submission_id: ID of the form submission
        """
        documents = await self.get_documents_by_submission(db, form_submission_id)
        
        for document in documents:
            file_path = Path(document.file_path)
            if file_path.exists():
                os.remove(file_path)
            
            await db.delete(document)
        
        await db.commit()

