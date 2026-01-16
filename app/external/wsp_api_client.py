import asyncio
from typing import Optional, Dict, Any
import httpx
from app.config import settings
from app.core.exceptions import ExternalAPIException


class WspAPIClient:
    """Client for WspApi integration (WhatsApp messaging) with retry logic and error handling."""
    
    def __init__(self):
        self.base_url = settings.WSP_API_URL
        self.api_key = settings.WSP_API_KEY
        self.oauth_token = settings.WSP_API_OAUTH_TOKEN
        self.timeout = settings.WSP_API_TIMEOUT
        self.retry_attempts = settings.WSP_API_RETRY_ATTEMPTS
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
        }
        
        # Use OAuth token if available, otherwise use API key
        if self.oauth_token:
            headers["Authorization"] = f"Bearer {self.oauth_token}"
        elif self.api_key:
            headers["X-API-Key"] = self.api_key
        
        return headers
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and exponential backoff.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            
        Returns:
            Response JSON data
            
        Raises:
            ExternalAPIException if request fails after retries
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        last_exception = None
        
        for attempt in range(self.retry_attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=data,
                        params=params
                    )
                    
                    # Check if request was successful
                    if response.status_code < 400:
                        return response.json() if response.content else {}
                    
                    # If 4xx error, don't retry (except 429)
                    if 400 <= response.status_code < 500 and response.status_code != 429:
                        raise ExternalAPIException(
                            detail=f"WspApi error: {response.status_code} - {response.text}"
                        )
                    
                    # For 5xx or 429, retry
                    last_exception = ExternalAPIException(
                        detail=f"WspApi error: {response.status_code} - {response.text}"
                    )
                    
            except httpx.TimeoutException as e:
                last_exception = ExternalAPIException(
                    detail=f"WspApi timeout: {str(e)}"
                )
            except httpx.RequestError as e:
                last_exception = ExternalAPIException(
                    detail=f"WspApi request error: {str(e)}"
                )
            
            # Exponential backoff: wait 2^attempt seconds
            if attempt < self.retry_attempts - 1:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
        
        # All retries failed
        raise last_exception
    
    async def send_message(
        self,
        phone_number: str,
        message: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send WhatsApp message via WspApi.
        
        Args:
            phone_number: Recipient phone number
            message: Message content
            **kwargs: Additional parameters for the API
            
        Returns:
            Response from WspApi
        """
        data = {
            "phone_number": phone_number,
            "message": message,
            **kwargs
        }
        
        return await self._make_request(
            method="POST",
            endpoint="/send",  # Adjust endpoint as needed
            data=data
        )
    
    async def send_form_notification(
        self,
        phone_number: str,
        form_url: str,
        client_name: str
    ) -> Dict[str, Any]:
        """
        Send form notification via WhatsApp.
        
        Args:
            phone_number: Recipient phone number
            form_url: URL to the form
            client_name: Name of the client
            
        Returns:
            Response from WspApi
        """
        message = f"Hola {client_name}, puedes completar tu formulario de reintegro en: {form_url}"
        
        return await self.send_message(
            phone_number=phone_number,
            message=message
        )
    
    async def send_submission_confirmation(
        self,
        phone_number: str,
        client_name: str,
        access_link: str
    ) -> Dict[str, Any]:
        """
        Send submission confirmation via WhatsApp.
        
        Args:
            phone_number: Recipient phone number
            client_name: Name of the client
            access_link: Access link for operators
            
        Returns:
            Response from WspApi
        """
        message = f"Hola {client_name}, tu formulario ha sido enviado exitosamente. Link de acceso: {access_link}"
        
        return await self.send_message(
            phone_number=phone_number,
            message=message
        )

