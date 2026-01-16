"""
HSM API Client for sending WhatsApp Highly Structured Messages.

Implements JWT authentication with token caching to avoid unnecessary login calls.
"""
import httpx
import logging
import time
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class HSMClientError(Exception):
    """Base exception for HSM client errors."""
    pass


class HSMAuthenticationError(HSMClientError):
    """Authentication failed with HSM API."""
    pass


class HSMSendError(HSMClientError):
    """Failed to send HSM message."""
    pass


class HSMClient:
    """
    Client for HSM API with JWT token caching.

    The client automatically handles authentication and token refresh.
    Tokens are cached in memory and only refreshed when expired.
    """

    def __init__(self):
        self.base_url = settings.HSM_API_URL.rstrip("/") if settings.HSM_API_URL else ""
        self.client_id = settings.HSM_CLIENT_ID
        self.client_secret = settings.HSM_CLIENT_SECRET
        self.provider = settings.HSM_PROVIDER
        self.origin_phone = settings.HSM_ORIGIN_PHONE
        self.default_language = settings.HSM_DEFAULT_LANGUAGE
        self.timeout = settings.HSM_API_TIMEOUT

        # Token cache
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0  # Unix timestamp
        self._token_buffer: int = 60  # Refresh 60 seconds before expiry

    def _is_configured(self) -> bool:
        """Check if HSM API is configured."""
        return bool(self.base_url and self.client_id and self.client_secret)

    async def _login(self) -> str:
        """
        Authenticate with HSM API and get access token.

        Returns:
            Access token string

        Raises:
            HSMAuthenticationError: If authentication fails
        """
        if not self._is_configured():
            raise HSMAuthenticationError("HSM API is not configured. Set HSM_API_URL, HSM_CLIENT_ID, and HSM_CLIENT_SECRET.")

        logger.info("HSM API: Authenticating...")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/auth/login",
                    json={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret
                    },
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 401:
                    raise HSMAuthenticationError("Invalid HSM API credentials")

                response.raise_for_status()
                data = response.json()

                self._access_token = data["access_token"]
                # Assume 1 hour expiry (common JWT default)
                self._token_expiry = time.time() + 3600

                logger.info("HSM API: Successfully authenticated")
                return self._access_token

        except httpx.HTTPStatusError as e:
            logger.error(f"HSM API authentication failed: {e.response.status_code}")
            raise HSMAuthenticationError(f"Authentication failed: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"HSM API connection error: {e}")
            raise HSMAuthenticationError(f"Connection error: {e}")

    async def _get_valid_token(self) -> str:
        """
        Get a valid access token, refreshing if needed.

        Returns:
            Valid access token
        """
        if self._access_token and time.time() < (self._token_expiry - self._token_buffer):
            return self._access_token

        logger.debug("HSM API: Token expired or missing, refreshing...")
        return await self._login()

    def _clear_token(self) -> None:
        """Clear the cached token (used on 401 errors)."""
        self._access_token = None
        self._token_expiry = 0

    async def send_hsm(
        self,
        template_name: str,
        phone_number: str,
        parameters: Optional[dict] = None,
        language: Optional[str] = None,
        origin: Optional[str] = None
    ) -> dict:
        """
        Send an HSM message.

        Args:
            template_name: Name of the HSM template
            phone_number: Recipient phone number with country code (10-15 digits)
            parameters: Template parameters as key-value pairs
            language: Template language code (default: from settings)
            origin: Sender phone number (default: from settings)

        Returns:
            API response dict with message status

        Raises:
            HSMSendError: If message sending fails
            HSMAuthenticationError: If authentication fails
        """
        if not self._is_configured():
            logger.warning("HSM API not configured, skipping message send")
            return {"success": False, "error": "HSM API not configured"}

        token = await self._get_valid_token()

        payload = {
            "template_name": template_name,
            "phone_number": phone_number,
            "origin": origin or self.origin_phone,
            "language": language or self.default_language,
            "parameters": parameters or {},
            "provider": self.provider
        }

        logger.info(f"HSM API: Sending message to {phone_number[:4]}*** with template '{template_name}'")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/hsm/send-hsm",
                    params={"provider": self.provider},
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                )

                # Handle 401 - clear token and retry once
                if response.status_code == 401:
                    logger.warning("HSM API: Token expired, refreshing and retrying...")
                    self._clear_token()
                    token = await self._get_valid_token()

                    response = await client.post(
                        f"{self.base_url}/api/v1/hsm/send-hsm",
                        params={"provider": self.provider},
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json"
                        }
                    )

                if response.status_code == 404:
                    logger.error(f"HSM API: Template '{template_name}' not found")
                    raise HSMSendError(f"Template '{template_name}' not found")

                if response.status_code == 503:
                    logger.error("HSM API: Provider unavailable")
                    raise HSMSendError("HSM provider unavailable")

                response.raise_for_status()
                result = response.json()

                logger.info(f"HSM API: Message sent successfully to {phone_number[:4]}***")
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"HSM API send failed: {e.response.status_code} - {e.response.text}")
            raise HSMSendError(f"Send failed: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"HSM API connection error: {e}")
            raise HSMSendError(f"Connection error: {e}")


# Singleton instance
_hsm_client: Optional[HSMClient] = None


def get_hsm_client() -> HSMClient:
    """
    Get or create the HSM client singleton.

    Returns:
        HSMClient instance
    """
    global _hsm_client
    if _hsm_client is None:
        _hsm_client = HSMClient()
    return _hsm_client
