"""
Database model mixins for common functionality.
"""
from datetime import datetime
from sqlalchemy import Column, Boolean, DateTime


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.

    Adds is_deleted and deleted_at fields to models.
    Records are marked as deleted instead of being permanently removed.
    """
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def soft_delete(self) -> None:
        """Mark the record as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
