"""Add soft delete fields and idempotency key

Revision ID: a1b2c3d4e5f6
Revises: 58a4ae00bf2b
Create Date: 2026-01-15 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '58a4ae00bf2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add soft delete fields to documents table
    op.add_column('documents', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('documents', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_documents_is_deleted'), 'documents', ['is_deleted'], unique=False)

    # Add soft delete fields to form_submissions table
    op.add_column('form_submissions', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('form_submissions', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_form_submissions_is_deleted'), 'form_submissions', ['is_deleted'], unique=False)

    # Add idempotency_key to forms table
    op.add_column('forms', sa.Column('idempotency_key', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_forms_idempotency_key'), 'forms', ['idempotency_key'], unique=True)


def downgrade() -> None:
    # Remove idempotency_key from forms
    op.drop_index(op.f('ix_forms_idempotency_key'), table_name='forms')
    op.drop_column('forms', 'idempotency_key')

    # Remove soft delete fields from form_submissions
    op.drop_index(op.f('ix_form_submissions_is_deleted'), table_name='form_submissions')
    op.drop_column('form_submissions', 'deleted_at')
    op.drop_column('form_submissions', 'is_deleted')

    # Remove soft delete fields from documents
    op.drop_index(op.f('ix_documents_is_deleted'), table_name='documents')
    op.drop_column('documents', 'deleted_at')
    op.drop_column('documents', 'is_deleted')
