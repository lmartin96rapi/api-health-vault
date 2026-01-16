import asyncio
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import httpx
from app.config import settings
from app.core.exceptions import ExternalAPIException
from app.core.logging_utils import mask_sensitive_data, sanitize_log_message
from app.core.circuit_breaker import backend_api_circuit_breaker, CircuitBreakerOpenException

logger = logging.getLogger(__name__)


class BackendAPIClient:
    """Client for Backend API integration with retry logic, error handling, and circuit breaker."""

    def __init__(self):
        self.base_url = settings.BACKEND_API_URL
        self.api_key = settings.BACKEND_API_KEY
        self.timeout = settings.BACKEND_API_TIMEOUT
        self.retry_attempts = settings.BACKEND_API_RETRY_ATTEMPTS
        self.circuit_breaker = backend_api_circuit_breaker
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key authentication."""
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
        }
    
    async def _execute_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        """
        Execute a single HTTP request (used by circuit breaker).

        Args:
            method: HTTP method
            url: Full URL
            headers: Request headers
            data: Request body data
            params: Query parameters

        Returns:
            httpx Response object
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await client.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params
            )

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic, exponential backoff, and circuit breaker.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters

        Returns:
            Response JSON data

        Raises:
            ExternalAPIException if request fails after retries
            CircuitBreakerOpenException if circuit breaker is open
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        # Mask sensitive data for logging
        masked_data = mask_sensitive_data(data) if data else None
        masked_headers = mask_sensitive_data(headers) if headers else None

        logger.info(
            sanitize_log_message(
                f"Making {method} request to Backend API",
                Endpoint=endpoint,
                URL=url,
                HasData=data is not None,
                HasParams=params is not None,
                Data=masked_data,
                Headers=masked_headers
            )
        )

        last_exception = None
        start_time = datetime.now()

        for attempt in range(self.retry_attempts):
            try:
                # Use circuit breaker to wrap the request execution
                response = await self.circuit_breaker.call(
                    self._execute_request,
                    method=method,
                    url=url,
                    headers=headers,
                    data=data,
                    params=params
                )

                response_time = (datetime.now() - start_time).total_seconds()

                logger.debug(
                    sanitize_log_message(
                        f"Backend API response received",
                        Endpoint=endpoint,
                        StatusCode=response.status_code,
                        ResponseTime=f"{response_time:.3f}s",
                        ResponseSize=len(response.content) if response.content else 0
                    )
                )

                # Check if request was successful
                if response.status_code < 400:
                    logger.info(
                        sanitize_log_message(
                            f"Backend API request successful",
                            Endpoint=endpoint,
                            StatusCode=response.status_code,
                            ResponseTime=f"{response_time:.3f}s"
                        )
                    )
                    return response.json() if response.content else {}

                # If 4xx error, don't retry (except 429)
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    error_msg = f"Backend API error: {response.status_code} - {response.text[:500]}"
                    logger.error(
                        sanitize_log_message(
                            error_msg,
                            Endpoint=endpoint,
                            StatusCode=response.status_code,
                            Attempt=attempt + 1,
                            ResponseText=response.text[:500]
                        )
                    )
                    raise ExternalAPIException(detail=error_msg)

                # For 5xx or 429, retry
                error_msg = f"Backend API error: {response.status_code} - {response.text[:500]}"
                logger.warning(
                    sanitize_log_message(
                        f"Retrying Backend API request",
                        Endpoint=endpoint,
                        StatusCode=response.status_code,
                        Attempt=attempt + 1,
                        MaxAttempts=self.retry_attempts
                    )
                )
                last_exception = ExternalAPIException(detail=error_msg)

            except CircuitBreakerOpenException:
                # Circuit breaker is open, fail fast without retrying
                logger.warning(
                    sanitize_log_message(
                        f"Circuit breaker open for Backend API",
                        Endpoint=endpoint,
                        CircuitState="OPEN"
                    )
                )
                raise

            except httpx.TimeoutException as e:
                logger.warning(
                    sanitize_log_message(
                        f"Backend API timeout",
                        Endpoint=endpoint,
                        Timeout=self.timeout,
                        Attempt=attempt + 1,
                        MaxAttempts=self.retry_attempts,
                        Error=str(e)
                    )
                )
                last_exception = ExternalAPIException(
                    detail=f"Backend API timeout: {str(e)}"
                )
            except httpx.RequestError as e:
                logger.error(
                    sanitize_log_message(
                        f"Backend API request error",
                        Endpoint=endpoint,
                        Attempt=attempt + 1,
                        MaxAttempts=self.retry_attempts,
                        Error=str(e)
                    ),
                    exc_info=True
                )
                last_exception = ExternalAPIException(
                    detail=f"Backend API request error: {str(e)}"
                )

            # Exponential backoff: wait 2^attempt seconds
            if attempt < self.retry_attempts - 1:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)

        # All retries failed
        logger.error(
            sanitize_log_message(
                f"All Backend API retries failed",
                Endpoint=endpoint,
                MaxAttempts=self.retry_attempts,
                FinalError=str(last_exception.detail) if last_exception else "Unknown"
            )
        )
        raise last_exception
    
    async def create_reintegro(
        self,
        form_submission_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create reintegro order via Backend API.
        
        Args:
            form_submission_data: Data for order creation matching backend API format:
                - client_id (int): Client ID
                - policy_id (int): Policy ID
                - service_id (int): Service ID
                - factura (str): Invoice document URL
                - email_asegurado (str, optional): Email
                - cuit_cuil_asegurado (str, optional): CUIT/CUIL
                - cbu_asegurado (str, optional): CBU
                - comment (str, optional): Comment with access link
                - organization_id (int, optional): Organization ID
                - request_origin (int, optional): Default 13 for bot
                
        Returns:
            Response from Backend API with id (pedido_id)
        """
        # TODO: Replace with actual API call when backend is ready
        # For now, return mock response with pedido_id
        timestamp = int(datetime.utcnow().timestamp())
        mock_pedido_id = timestamp  # Backend returns integer ID
        
        return {
            "id": mock_pedido_id,
            "created_time": datetime.utcnow().strftime("%Y-%m-%d"),
            "description": form_submission_data.get("comment", ""),
            "status_request": "En negociación"
        }
        
        # When ready, uncomment this:
        # return await self._make_request(
        #     method="POST",
        #     endpoint="/v1/bot/order/",
        #     data=form_submission_data
        # )
    
    async def update_reintegro(
        self,
        reintegro_id: str,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update reintegro order via Backend API.
        Note: Update endpoint not implemented yet - skip for now.
        
        Args:
            reintegro_id: pedido_id of the order to update
            update_data: Data to update
            
        Returns:
            Response from Backend API
        """
        # TODO: Implement when backend update endpoint is available
        # For now, return mock success response
        return {
            "id": int(reintegro_id),
            "status": "success",
            "message": "Reintegro updated successfully"
        }

