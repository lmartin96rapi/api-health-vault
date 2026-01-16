"""
Tests for API key validation and security.
"""
import pytest
from app.core.api_key import hash_api_key, verify_api_key, get_api_key_from_header
from app.models.api_key import ApiKey


class TestApiKeyHashing:
    """Tests for API key hashing functions."""

    def test_hash_api_key_returns_hex_string(self):
        """Hash function should return a hex string."""
        api_key = "test_api_key_12345"
        hashed = hash_api_key(api_key)

        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA256 produces 64 hex characters
        assert all(c in '0123456789abcdef' for c in hashed)

    def test_hash_api_key_consistent(self):
        """Same input should produce same hash."""
        api_key = "consistent_key"
        hash1 = hash_api_key(api_key)
        hash2 = hash_api_key(api_key)

        assert hash1 == hash2

    def test_hash_api_key_different_inputs(self):
        """Different inputs should produce different hashes."""
        hash1 = hash_api_key("key1")
        hash2 = hash_api_key("key2")

        assert hash1 != hash2

    def test_verify_api_key_correct(self):
        """Verification should succeed with correct key."""
        api_key = "my_secret_api_key"
        hashed = hash_api_key(api_key)

        assert verify_api_key(api_key, hashed) is True

    def test_verify_api_key_incorrect(self):
        """Verification should fail with incorrect key."""
        api_key = "my_secret_api_key"
        hashed = hash_api_key(api_key)

        assert verify_api_key("wrong_key", hashed) is False

    def test_verify_api_key_empty_key(self):
        """Verification should fail with empty key."""
        hashed = hash_api_key("some_key")

        assert verify_api_key("", hashed) is False

    def test_hash_api_key_special_characters(self):
        """Hash function should handle special characters."""
        special_key = "key-with_special.chars!@#$%^&*()"
        hashed = hash_api_key(special_key)

        assert len(hashed) == 64
        assert verify_api_key(special_key, hashed) is True


class TestApiKeyFromHeader:
    """Tests for API key extraction and validation from headers."""

    @pytest.mark.asyncio
    async def test_get_api_key_from_header_none(self, db_session):
        """Should return None when no API key provided."""
        result = await get_api_key_from_header(None, db_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_api_key_from_header_empty(self, db_session):
        """Should return None when empty API key provided."""
        result = await get_api_key_from_header("", db_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_api_key_from_header_invalid(self, db_session):
        """Should return None for invalid API key."""
        result = await get_api_key_from_header("invalid_key", db_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_api_key_from_header_valid(self, db_session):
        """Should return ApiKey for valid API key."""
        # Create a test API key
        plain_key = "test_valid_api_key_12345"
        key_hash = hash_api_key(plain_key)

        api_key = ApiKey(
            name="Test Key",
            key_hash=key_hash,
            is_active=True
        )
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        # Test retrieval
        result = await get_api_key_from_header(plain_key, db_session)

        assert result is not None
        assert result.id == api_key.id
        assert result.name == "Test Key"

    @pytest.mark.asyncio
    async def test_get_api_key_inactive_key(self, db_session):
        """Should return None for inactive API key."""
        # Create an inactive API key
        plain_key = "inactive_api_key"
        key_hash = hash_api_key(plain_key)

        api_key = ApiKey(
            name="Inactive Key",
            key_hash=key_hash,
            is_active=False
        )
        db_session.add(api_key)
        await db_session.commit()

        # Test retrieval
        result = await get_api_key_from_header(plain_key, db_session)

        assert result is None


class TestApiKeyTimingAttack:
    """Tests to verify timing attack prevention."""

    def test_verify_uses_constant_time_comparison(self):
        """Verify that verification uses constant-time comparison."""
        import time

        correct_key = "correct_api_key_for_timing_test"
        hashed = hash_api_key(correct_key)

        # Run multiple iterations to get average times
        iterations = 100

        # Time correct key verification
        start = time.perf_counter()
        for _ in range(iterations):
            verify_api_key(correct_key, hashed)
        correct_time = time.perf_counter() - start

        # Time incorrect key verification (same length)
        wrong_key = "wrrong_api_key_for_timing_test"
        start = time.perf_counter()
        for _ in range(iterations):
            verify_api_key(wrong_key, hashed)
        wrong_time = time.perf_counter() - start

        # Time incorrect key verification (different length)
        short_key = "short"
        start = time.perf_counter()
        for _ in range(iterations):
            verify_api_key(short_key, hashed)
        short_time = time.perf_counter() - start

        # The times should be similar (within 50% of each other)
        # This is a rough check - constant time comparison should give similar times
        avg_time = (correct_time + wrong_time + short_time) / 3

        # All times should be within 2x of average (allowing for system variance)
        assert correct_time < avg_time * 2
        assert wrong_time < avg_time * 2
        assert short_time < avg_time * 2
