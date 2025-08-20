"""
API Client for Portuguese Government Procurement API
====================================================

This module provides an async API client with retry logic and rate limiting
for fetching data from the Portuguese Government Procurement API (BASE.gov.pt).

Features:
- Async HTTP requests with aiohttp
- Exponential backoff retry logic
- Rate limiting (5 requests/second)
- Extended timeouts for slow API responses
- Comprehensive error handling
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from asyncio_throttle import Throttler
import json
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIEndpoint(Enum):
    """API endpoints for the Portuguese Government Procurement API"""
    ANNOUNCEMENTS = "GetInfoAnuncio"
    CONTRACTS = "GetInfoContrato"
    ENTITIES = "GetInfoEntidades"
    CONTRACT_MODS = "GetInfoModContrat"

@dataclass
class APIConfig:
    """Configuration for the API client"""
    base_url: str = "https://www.base.gov.pt/APIBase2"
    access_token: str = "Nmq28lKgTbr05RaFOJNf"
    rate_limit: int = 5  # requests per second
    timeout: int = 120  # seconds (2 minutes for large responses)
    max_retries: int = 3
    retry_delay: int = 2  # base delay in seconds
    backoff_factor: float = 2.0  # exponential backoff factor
    
@dataclass
class AsyncRequestConfig:
    """Configuration for async requests with extended timeouts"""
    max_retries: int = 5
    base_delay: int = 10  # seconds
    max_delay: int = 300  # 5 minutes
    timeout: int = 600  # 10 minutes for very slow responses
    backoff_factor: float = 2.0

class ContrapAPIClient:
    """
    Async API client for fetching Portuguese Government Procurement data.
    
    This client handles the slow and unreliable government API with:
    - Extended timeouts (up to 60 minutes for batch operations)
    - Exponential backoff retry logic
    - Rate limiting to respect API limits
    - Comprehensive error handling and logging
    """
    
    def __init__(self, config: Optional[APIConfig] = None):
        """
        Initialize the API client.
        
        Args:
            config: Optional API configuration. Uses defaults if not provided.
        """
        self.config = config or APIConfig()
        self.throttler = Throttler(rate_limit=self.config.rate_limit)
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_count = 0
        self.error_count = 0
        
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_request(
        self, 
        endpoint: str, 
        params: Dict[str, Any] = None,
        async_config: Optional[AsyncRequestConfig] = None
    ) -> Dict[str, Any]:
        """
        Make an API request with retry logic and rate limiting.
        
        Args:
            endpoint: API endpoint to call
            params: Query parameters for the request
            async_config: Optional async configuration for extended timeouts
            
        Returns:
            JSON response from the API
            
        Raises:
            aiohttp.ClientError: If all retry attempts fail
        """
        url = f"{self.config.base_url}/{endpoint}"
        
        # Token should be in headers (note: _AcessToken with one 'c')
        headers = {"_AcessToken": self.config.access_token}
        
        if params is None:
            params = {}
        
        # Use extended config if provided
        if async_config:
            max_retries = async_config.max_retries
            base_delay = async_config.base_delay
            max_delay = async_config.max_delay
            timeout = async_config.timeout
            backoff_factor = async_config.backoff_factor
        else:
            max_retries = self.config.max_retries
            base_delay = self.config.retry_delay
            max_delay = 60
            timeout = self.config.timeout
            backoff_factor = self.config.backoff_factor
        
        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                async with self.throttler:
                    # Create custom timeout for this request
                    request_timeout = aiohttp.ClientTimeout(total=timeout)
                    
                    logger.debug(f"Attempt {attempt + 1}/{max_retries} for {endpoint}")
                    logger.debug(f"Request params: {params}")
                    
                    async with self.session.get(
                        url, 
                        headers=headers,
                        params=params,
                        timeout=request_timeout
                    ) as response:
                        self.request_count += 1
                        
                        # Check for API errors
                        if response.status == 400:
                            text = await response.text()
                            if "Token is required" in text:
                                logger.error("API token is missing or invalid")
                                raise ValueError("Invalid API token")
                            elif "no Params submited" in text:
                                logger.error("Missing required parameters")
                                raise ValueError(f"Missing parameters: {params}")
                        
                        response.raise_for_status()
                        
                        # Parse response - API returns text/plain but with JSON content
                        text = await response.text()
                        
                        # Try to parse as JSON regardless of content-type
                        try:
                            data = json.loads(text) if text else {}
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse JSON from response: {text[:200]}")
                            raise ValueError(f"Invalid JSON response from {endpoint}")
                        
                        logger.info(f"Successfully fetched data from {endpoint} "
                                  f"(attempt {attempt + 1})")
                        
                        return data
                        
            except asyncio.TimeoutError:
                self.error_count += 1
                delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                
                logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries} "
                             f"for {endpoint}. Waiting {delay}s before retry...")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All retry attempts failed for {endpoint}")
                    raise
                    
            except aiohttp.ClientError as e:
                self.error_count += 1
                delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                
                logger.error(f"Client error on attempt {attempt + 1}: {str(e)}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                else:
                    raise
                    
            except Exception as e:
                self.error_count += 1
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
                
                if attempt < max_retries - 1:
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    await asyncio.sleep(delay)
                else:
                    raise
    
    async def get_announcements(
        self, 
        start_date: datetime, 
        end_date: datetime,
        year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch announcements for a date range.
        
        Args:
            start_date: Start date for the query
            end_date: End date for the query
            year: Optional year filter
            
        Returns:
            List of announcement dictionaries
        """
        params = {}
        
        # The API primarily uses year parameter
        if year:
            params["Ano"] = year
        else:
            # Extract year from start_date if not provided
            params["Ano"] = start_date.year
        
        logger.info(f"Fetching announcements with params: {params}")
        
        result = await self._make_request(APIEndpoint.ANNOUNCEMENTS.value, params)
        
        # Handle different response formats
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "items" in result:
            return result["items"]
        else:
            logger.warning(f"Unexpected response format: {type(result)}")
            return []
    
    async def get_contracts(
        self, 
        start_date: datetime, 
        end_date: datetime,
        year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch contracts for a date range.
        
        Args:
            start_date: Start date for the query
            end_date: End date for the query
            year: Optional year filter
            
        Returns:
            List of contract dictionaries
        """
        params = {}
        
        # The API primarily uses year parameter
        if year:
            params["Ano"] = year
        else:
            # Extract year from start_date if not provided
            params["Ano"] = start_date.year
        
        logger.info(f"Fetching contracts with params: {params}")
        
        result = await self._make_request(APIEndpoint.CONTRACTS.value, params)
        
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "items" in result:
            return result["items"]
        else:
            logger.warning(f"Unexpected response format: {type(result)}")
            return []
    
    async def get_entity(self, nif: str) -> Dict[str, Any]:
        """
        Fetch entity information by NIF.
        
        Args:
            nif: Portuguese Tax ID (9 digits)
            
        Returns:
            Entity information dictionary
        """
        params = {"nifEntidade": nif}
        
        logger.info(f"Fetching entity with NIF: {nif}")
        
        return await self._make_request(APIEndpoint.ENTITIES.value, params)
    
    async def get_contract_modifications(
        self, 
        contract_id: str,
        year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch contract modifications.
        
        Args:
            contract_id: Contract identifier
            year: Optional year filter
            
        Returns:
            List of contract modification dictionaries
        """
        params = {"idContrato": contract_id}
        if year:
            params["Ano"] = year
        
        logger.info(f"Fetching contract modifications for: {contract_id}")
        
        result = await self._make_request(APIEndpoint.CONTRACT_MODS.value, params)
        
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "items" in result:
            return result["items"]
        else:
            return []
    
    # Async methods with extended timeouts for very slow responses
    
    async def get_announcements_async(
        self,
        start_date: datetime,
        end_date: datetime,
        config: Optional[AsyncRequestConfig] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch announcements with extended async configuration.
        
        This method is designed for handling very slow API responses
        that can take 2-5 minutes or more.
        
        Args:
            start_date: Start date for the query
            end_date: End date for the query
            config: Optional async configuration
            
        Returns:
            List of announcement dictionaries
        """
        config = config or AsyncRequestConfig()
        
        params = {
            "Ano": start_date.year
        }
        
        logger.info(f"Fetching announcements async with extended timeout: {config.timeout}s")
        
        result = await self._make_request(
            APIEndpoint.ANNOUNCEMENTS.value, 
            params,
            config
        )
        
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "items" in result:
            return result["items"]
        else:
            return []
    
    async def get_contracts_async(
        self,
        start_date: datetime,
        end_date: datetime,
        config: Optional[AsyncRequestConfig] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch contracts with extended async configuration.
        
        Args:
            start_date: Start date for the query
            end_date: End date for the query
            config: Optional async configuration
            
        Returns:
            List of contract dictionaries
        """
        config = config or AsyncRequestConfig()
        
        params = {
            "Ano": start_date.year
        }
        
        logger.info(f"Fetching contracts async with extended timeout: {config.timeout}s")
        
        result = await self._make_request(
            APIEndpoint.CONTRACTS.value, 
            params,
            config
        )
        
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "items" in result:
            return result["items"]
        else:
            return []
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get client statistics.
        
        Returns:
            Dictionary with request and error counts
        """
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "success_rate": (
                (self.request_count - self.error_count) / self.request_count * 100
                if self.request_count > 0 else 0
            )
        }

# Factory function for creating default async configuration
def get_default_async_config() -> AsyncRequestConfig:
    """
    Get default async configuration for slow API responses.
    
    Returns:
        AsyncRequestConfig with sensible defaults
    """
    return AsyncRequestConfig(
        max_retries=5,
        base_delay=10,
        max_delay=300,
        timeout=600,
        backoff_factor=2.0
    )

# Factory function for batch processing configuration
def get_batch_processing_config() -> AsyncRequestConfig:
    """
    Get configuration optimized for batch processing.
    
    Returns:
        AsyncRequestConfig for batch operations
    """
    return AsyncRequestConfig(
        max_retries=3,
        base_delay=30,
        max_delay=600,
        timeout=3600,  # 60 minutes for very large batches
        backoff_factor=2.5
    )
