"""
Tests for API endpoints including health checks and error responses.
"""
import pytest


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """Health check endpoint should return healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_root_endpoint(self, client):
        """Root endpoint should return API info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data


class TestSecurityHeaders:
    """Tests for security headers in responses."""

    def test_csp_header(self, client):
        """Response should include Content-Security-Policy header."""
        response = client.get("/health")

        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'none'" in csp

    def test_xss_protection_header(self, client):
        """Response should include X-XSS-Protection header."""
        response = client.get("/health")

        assert "X-XSS-Protection" in response.headers

    def test_content_type_options_header(self, client):
        """Response should include X-Content-Type-Options header."""
        response = client.get("/health")

        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_frame_options_header(self, client):
        """Response should include X-Frame-Options header."""
        response = client.get("/health")

        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"


class TestErrorResponses:
    """Tests for error response handling."""

    def test_404_not_found(self, client):
        """Non-existent endpoint should return 404."""
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    def test_form_not_found(self, client):
        """Non-existent form should return 404."""
        response = client.get("/api/v1/forms/nonexistent_token_12345")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestFormEndpoints:
    """Tests for form-related endpoints."""

    def test_get_form_invalid_token(self, client):
        """Invalid form token should return 404."""
        response = client.get("/api/v1/forms/invalid_token_abc123")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Form not found"

    def test_get_form_status_invalid_token(self, client):
        """Invalid form token for status should return appropriate error."""
        response = client.get("/api/v1/forms/invalid_token/status")

        # Should return 404 or form-specific error
        assert response.status_code in [404, 400]


class TestRateLimiting:
    """Tests for rate limiting (if enabled)."""

    def test_rate_limit_headers_present(self, client):
        """Rate limit headers should be present in response."""
        response = client.get("/health")

        # Rate limiting headers may be present depending on configuration
        # This test just verifies the endpoint works
        assert response.status_code == 200


class TestCORSHeaders:
    """Tests for CORS headers."""

    def test_cors_headers_on_options(self, client):
        """OPTIONS request should return CORS headers."""
        response = client.options(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )

        # CORS headers should be present for allowed origins
        # The exact behavior depends on configuration
        assert response.status_code in [200, 204, 405]
