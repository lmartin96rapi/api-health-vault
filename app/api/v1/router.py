from fastapi import APIRouter
from app.api.v1.endpoints import forms, documents, auth, audit

api_router = APIRouter()

api_router.include_router(forms.router, prefix="/forms", tags=["forms"])
api_router.include_router(documents.router, prefix="/document-access", tags=["documents"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(audit.router, prefix="/audit-logs", tags=["audit"])

