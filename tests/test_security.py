"""
Tests for security functions including JWT tokens and OAuth validation.
"""
import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock

from app.core.security import (
    create_access_token,
    decode_access_token,
    verify_password,
    get_password_hash,
    verify_google_token,
)
from app.config import settings


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_get_password_hash_returns_hash(self):
        """Password hashing should return a bcrypt hash."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_password_hash_different_each_time(self):
        """Same password should produce different hashes (due to salt)."""
        password = "same_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Verification should succeed with correct password."""
        password = "correct_password"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Verification should fail with incorrect password."""
        password = "correct_password"
        hashed = get_password_hash(password)

        assert verify_password("wrong_password", hashed) is False


class TestJWTTokens:
    """Tests for JWT token creation and validation."""

    def test_create_access_token_returns_string(self):
        """Token creation should return a JWT string."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0
        # JWT tokens have 3 parts separated by dots
        assert token.count(".") == 2

    def test_create_access_token_with_custom_expiry(self):
        """Token should respect custom expiry delta."""
        data = {"sub": "user123"}
        expires_delta = timedelta(hours=1)
        token = create_access_token(data, expires_delta)

        # Token should be decodable
        payload = decode_access_token(token)
        assert payload is not None
        assert "exp" in payload

    def test_decode_access_token_valid(self):
        """Valid token should decode successfully."""
        original_data = {"sub": "user123", "role": "admin"}
        token = create_access_token(original_data)

        payload = decode_access_token(token)

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"
        assert "exp" in payload

    def test_decode_access_token_invalid(self):
        """Invalid token should return None."""
        invalid_token = "not.a.valid.jwt.token"

        payload = decode_access_token(invalid_token)

        assert payload is None

    def test_decode_access_token_tampered(self):
        """Tampered token should return None."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        # Tamper with the token
        parts = token.split(".")
        parts[1] = parts[1][:-5] + "XXXXX"  # Modify payload
        tampered_token = ".".join(parts)

        payload = decode_access_token(tampered_token)

        assert payload is None

    def test_decode_access_token_empty(self):
        """Empty token should return None."""
        payload = decode_access_token("")

        assert payload is None


class TestGoogleOAuth:
    """Tests for Google OAuth token verification."""

    @pytest.mark.asyncio
    async def test_verify_google_token_invalid(self):
        """Invalid Google token should return None."""
        result = await verify_google_token("invalid_token")

        assert result is None

    @pytest.mark.asyncio
    async def test_verify_google_token_wrong_issuer(self):
        """Token with wrong issuer should return None."""
        with patch("app.core.security.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = {
                "iss": "wrong_issuer.com",
                "email": "test@example.com",
            }

            result = await verify_google_token("some_token")

            assert result is None

    @pytest.mark.asyncio
    async def test_verify_google_token_valid(self):
        """Valid Google token should return user info."""
        with patch("app.core.security.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = {
                "iss": "https://accounts.google.com",
                "email": "test@example.com",
                "name": "Test User",
                "picture": "https://example.com/photo.jpg",
                "sub": "google_user_id_123",
            }

            result = await verify_google_token("valid_token")

            assert result is not None
            assert result["email"] == "test@example.com"
            assert result["name"] == "Test User"
            assert result["sub"] == "google_user_id_123"

    @pytest.mark.asyncio
    async def test_verify_google_token_only_https_issuer(self):
        """Only https://accounts.google.com issuer should be accepted."""
        with patch("app.core.security.id_token.verify_oauth2_token") as mock_verify:
            # Test that non-https issuer is rejected
            mock_verify.return_value = {
                "iss": "accounts.google.com",  # Without https://
                "email": "test@example.com",
            }

            result = await verify_google_token("some_token")

            # Should be None because only https://accounts.google.com is accepted
            assert result is None


class TestSecurityEdgeCases:
    """Tests for edge cases in security functions."""

    def test_password_hash_special_characters(self):
        """Password with special characters should hash correctly."""
        password = "p@$$w0rd!#$%^&*()"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_password_hash_unicode(self):
        """Password with unicode characters should hash correctly."""
        password = "пароль_密码_パスワード"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_token_with_special_data(self):
        """Token with special characters in data should work."""
        data = {
            "sub": "user@example.com",
            "name": "José García",
            "role": "admin/superuser",
        }
        token = create_access_token(data)
        payload = decode_access_token(token)

        assert payload["sub"] == "user@example.com"
        assert payload["name"] == "José García"
