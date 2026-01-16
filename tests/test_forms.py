"""
Tests for form creation, validation, and submission.
"""
import pytest
from datetime import datetime, timedelta
from app.services.form_service import FormService
from app.models.form import Form, FormStatus
from app.core.exceptions import (
    FormExpiredException,
    FormAlreadySubmittedException,
    InvalidFormTokenException,
)


class TestFormTokenGeneration:
    """Tests for form token generation."""

    def test_generate_form_token_returns_string(self):
        """Token generation should return a string."""
        token = FormService._generate_form_token()

        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_form_token_unique(self):
        """Each token should be unique."""
        tokens = [FormService._generate_form_token() for _ in range(100)]
        unique_tokens = set(tokens)

        assert len(tokens) == len(unique_tokens)

    def test_generate_form_token_url_safe(self):
        """Token should be URL-safe."""
        token = FormService._generate_form_token()

        # URL-safe characters only
        import string
        url_safe_chars = string.ascii_letters + string.digits + "-_"

        assert all(c in url_safe_chars for c in token)


class TestFormCreation:
    """Tests for form creation."""

    @pytest.mark.asyncio
    async def test_create_form_success(self, db_session):
        """Form creation should succeed with valid data."""
        form, was_created = await FormService.create_form(
            db=db_session,
            client_id="client123",
            policy_id="policy456",
            service_id=1,
            name="Test User",
            dni="12345678",
            email="test@example.com",
        )

        assert form is not None
        assert was_created is True
        assert form.client_id == "client123"
        assert form.policy_id == "policy456"
        assert form.status == FormStatus.PENDING
        assert form.is_submitted is False
        assert form.form_token is not None

    @pytest.mark.asyncio
    async def test_create_form_with_optional_fields(self, db_session):
        """Form creation should handle optional fields."""
        form, was_created = await FormService.create_form(
            db=db_session,
            client_id="client123",
            policy_id="policy456",
            service_id=1,
            name="Test User",
            dni="12345678",
            email="test@example.com",
            cbu="1234567890123456789012",
            cuit="20-12345678-9",
            order_id="order789",
        )

        assert form.cbu == "1234567890123456789012"
        assert form.cuit == "20-12345678-9"
        assert form.order_id == "order789"

    @pytest.mark.asyncio
    async def test_create_form_sets_expiration(self, db_session):
        """Form should have expiration time set."""
        form, _ = await FormService.create_form(
            db=db_session,
            client_id="client123",
            policy_id="policy456",
            service_id=1,
            name="Test User",
            dni="12345678",
            email="test@example.com",
        )

        assert form.expires_at is not None
        assert form.expires_at > datetime.utcnow()


class TestFormIdempotency:
    """Tests for form creation idempotency."""

    @pytest.mark.asyncio
    async def test_idempotency_key_returns_existing_form(self, db_session):
        """Same idempotency key should return existing form."""
        idempotency_key = "unique-idempotency-key-123"

        # First creation
        form1, was_created1 = await FormService.create_form(
            db=db_session,
            client_id="client123",
            policy_id="policy456",
            service_id=1,
            name="Test User",
            dni="12345678",
            email="test@example.com",
            idempotency_key=idempotency_key,
        )

        # Second creation with same key
        form2, was_created2 = await FormService.create_form(
            db=db_session,
            client_id="different_client",  # Different data
            policy_id="different_policy",
            service_id=2,
            name="Different User",
            dni="87654321",
            email="different@example.com",
            idempotency_key=idempotency_key,
        )

        assert was_created1 is True
        assert was_created2 is False
        assert form1.id == form2.id
        assert form2.client_id == "client123"  # Original data preserved

    @pytest.mark.asyncio
    async def test_different_idempotency_keys_create_different_forms(self, db_session):
        """Different idempotency keys should create different forms."""
        form1, _ = await FormService.create_form(
            db=db_session,
            client_id="client1",
            policy_id="policy1",
            service_id=1,
            name="User 1",
            dni="11111111",
            email="user1@example.com",
            idempotency_key="key-1",
        )

        form2, _ = await FormService.create_form(
            db=db_session,
            client_id="client2",
            policy_id="policy2",
            service_id=2,
            name="User 2",
            dni="22222222",
            email="user2@example.com",
            idempotency_key="key-2",
        )

        assert form1.id != form2.id


class TestFormValidation:
    """Tests for form validation."""

    @pytest.mark.asyncio
    async def test_validate_form_valid(self, db_session):
        """Validation should succeed for valid form."""
        form, _ = await FormService.create_form(
            db=db_session,
            client_id="client123",
            policy_id="policy456",
            service_id=1,
            name="Test User",
            dni="12345678",
            email="test@example.com",
        )

        validated_form = await FormService.validate_form(db_session, form.form_token)

        assert validated_form.id == form.id

    @pytest.mark.asyncio
    async def test_validate_form_invalid_token(self, db_session):
        """Validation should raise for invalid token."""
        with pytest.raises(InvalidFormTokenException):
            await FormService.validate_form(db_session, "invalid_token_123")

    @pytest.mark.asyncio
    async def test_validate_form_expired(self, db_session):
        """Validation should raise for expired form."""
        # Create a form
        form, _ = await FormService.create_form(
            db=db_session,
            client_id="client123",
            policy_id="policy456",
            service_id=1,
            name="Test User",
            dni="12345678",
            email="test@example.com",
        )

        # Manually expire it
        form.expires_at = datetime.utcnow() - timedelta(hours=1)
        await db_session.commit()

        with pytest.raises(FormExpiredException):
            await FormService.validate_form(db_session, form.form_token)

    @pytest.mark.asyncio
    async def test_validate_form_already_submitted(self, db_session):
        """Validation should raise for already submitted form."""
        # Create a form
        form, _ = await FormService.create_form(
            db=db_session,
            client_id="client123",
            policy_id="policy456",
            service_id=1,
            name="Test User",
            dni="12345678",
            email="test@example.com",
        )

        # Mark as submitted
        form.is_submitted = True
        await db_session.commit()

        with pytest.raises(FormAlreadySubmittedException):
            await FormService.validate_form(db_session, form.form_token)


class TestFormStatus:
    """Tests for form status retrieval."""

    @pytest.mark.asyncio
    async def test_get_form_status_valid(self, db_session):
        """Status retrieval should work for valid form."""
        form, _ = await FormService.create_form(
            db=db_session,
            client_id="client123",
            policy_id="policy456",
            service_id=1,
            name="Test User",
            dni="12345678",
            email="test@example.com",
        )

        status = await FormService.get_form_status(db_session, form.form_token)

        assert status["form_token"] == form.form_token
        assert status["status"] == "pending"
        assert status["is_submitted"] is False
        assert status["is_expired"] is False

    @pytest.mark.asyncio
    async def test_get_form_status_invalid_token(self, db_session):
        """Status retrieval should raise for invalid token."""
        with pytest.raises(InvalidFormTokenException):
            await FormService.get_form_status(db_session, "invalid_token")
