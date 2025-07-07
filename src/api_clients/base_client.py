# src/api_clients/base_client.py

import aiohttp
import asyncio
import json
import time
from typing import Dict, Any, Optional, Union, List
from urllib.parse import urljoin, urlencode
import logging
from dataclasses import dataclass
from enum import Enum

from ..utils.exceptions import APIError, RateLimitError, AuthenticationError
from ..config.settings import get_config

logger = logging.getLogger(__name__)

class HTTPMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

@dataclass
class APIResponse:
    """Standardized API response container"""
    status_code: int
    data: Any
    headers: Dict[str, str]
    success: bool
    error_message: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        return self.success and 200 <= self.status_code < 300

class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_requests: int = 60, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: List[float] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Acquire permission to make an API call"""
        async with self._lock:
            now = time.time()
            # Remove old requests outside the time window
            self.requests = [req_time for req_time in self.requests 
                           if now - req_time < self.time_window]
            
            if len(self.requests) >= self.max_requests:
                sleep_time = self.time_window - (now - self.requests[0])
                if sleep_time > 0:
                    logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()
            
            self.requests.append(now)

class BaseHTTPClient:
    """Base HTTP client with common functionality for all API clients"""
    
    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit_requests: int = 60,
        rate_limit_window: int = 60,
        headers: Optional[Dict[str, str]] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = RateLimiter(rate_limit_requests, rate_limit_window)
        self.default_headers = headers or {}
        
        # Response cache
        self._cache: Dict[str, tuple] = {}  # key: (response, timestamp)
        self._cache_ttl = 60  # Default cache TTL in seconds
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_session(self) -> None:
        """Ensure aiohttp session is created"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=10,
                keepalive_timeout=30
            )
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
                headers=self.default_headers
            )
    
    async def close(self) -> None:
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    def _build_url(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Build complete URL with query parameters"""
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        if params:
            # Filter out None values
            filtered_params = {k: v for k, v in params.items() if v is not None}
            if filtered_params:
                url += '?' + urlencode(filtered_params)
        return url
    
    def _get_cache_key(self, method: str, url: str, headers: Dict[str, str]) -> str:
        """Generate cache key for request"""
        key_parts = [method, url]
        # Include relevant headers in cache key
        for header in ['X-EXCHANGE', 'X-API-KEY']:
            if header in headers:
                key_parts.append(f"{header}:{headers[header]}")
        return "|".join(key_parts)
    
    def _get_cached_response(self, cache_key: str, ttl: Optional[int] = None) -> Optional[APIResponse]:
        """Get cached response if valid"""
        if cache_key not in self._cache:
            return None
        
        response, timestamp = self._cache[cache_key]
        cache_ttl = ttl or self._cache_ttl
        
        if time.time() - timestamp > cache_ttl:
            del self._cache[cache_key]
            return None
        
        logger.debug(f"Cache hit for {cache_key}")
        return response
    
    def _cache_response(self, cache_key: str, response: APIResponse) -> None:
        """Cache response"""
        if response.is_success:
            self._cache[cache_key] = (response, time.time())
            logger.debug(f"Cached response for {cache_key}")
    
    async def _make_request(
        self,
        method: HTTPMethod,
        endpoint: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None
    ) -> APIResponse:
        """Make HTTP request with retries and error handling"""
        
        await self._ensure_session()
        
        # Merge headers
        request_headers = {**self.default_headers}
        if headers:
            request_headers.update(headers)
        
        url = self._build_url(endpoint, params)
        
        # Check cache for GET requests
        cache_key = self._get_cache_key(method.value, url, request_headers)
        if method == HTTPMethod.GET and use_cache:
            cached_response = self._get_cached_response(cache_key, cache_ttl)
            if cached_response:
                return cached_response
        
        # Rate limiting
        await self.rate_limiter.acquire()
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Making {method.value} request to {url} (attempt {attempt + 1})")
                
                # Prepare request data
                kwargs = {
                    'method': method.value,
                    'url': url,
                    'headers': request_headers
                }
                
                if data:
                    if isinstance(data, dict):
                        kwargs['json'] = data
                    else:
                        kwargs['data'] = data
                
                async with self.session.request(**kwargs) as response:
                    response_text = await response.text()
                    
                    # Try to parse JSON response
                    try:
                        response_data = json.loads(response_text) if response_text else {}
                    except json.JSONDecodeError:
                        response_data = response_text
                    
                    # Create API response
                    api_response = APIResponse(
                        status_code=response.status,
                        data=response_data,
                        headers=dict(response.headers),
                        success=200 <= response.status < 300
                    )
                    
                    # Handle specific error status codes
                    if response.status == 401:
                        api_response.error_message = "Authentication failed"
                        logger.error(f"Authentication error: {response_data}")
                        raise AuthenticationError(api_response.error_message)
                    
                    elif response.status == 429:
                        api_response.error_message = "Rate limit exceeded"
                        logger.warning(f"Rate limit exceeded: {response_data}")
                        if attempt < self.max_retries:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        raise RateLimitError(api_response.error_message)
                    
                    elif response.status >= 400:
                        error_msg = response_data.get('error', f"HTTP {response.status}")
                        api_response.error_message = str(error_msg)
                        logger.error(f"API error {response.status}: {error_msg}")
                        
                        if response.status >= 500 and attempt < self.max_retries:
                            # Retry on server errors
                            await asyncio.sleep(2 ** attempt)
                            continue
                        
                        raise APIError(api_response.error_message, response.status)
                    
                    # Cache successful GET responses
                    if method == HTTPMethod.GET and use_cache and api_response.is_success:
                        self._cache_response(cache_key, api_response)
                    
                    logger.debug(f"Request successful: {response.status}")
                    return api_response
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                logger.warning(f"Request failed (attempt {attempt + 1}): {str(e)}")
                
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
        
        # All retries failed
        error_msg = f"Request failed after {self.max_retries + 1} attempts: {str(last_exception)}"
        logger.error(error_msg)
        raise APIError(error_msg)
    
    # Convenience methods for different HTTP verbs
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None
    ) -> APIResponse:
        """Make GET request"""
        return await self._make_request(
            HTTPMethod.GET, endpoint, params=params, headers=headers,
            use_cache=use_cache, cache_ttl=cache_ttl
        )
    
    async def post(
        self,
        endpoint: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> APIResponse:
        """Make POST request"""
        return await self._make_request(
            HTTPMethod.POST, endpoint, data=data, params=params, headers=headers,
            use_cache=False
        )
    
    async def put(
        self,
        endpoint: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> APIResponse:
        """Make PUT request"""
        return await self._make_request(
            HTTPMethod.PUT, endpoint, data=data, params=params, headers=headers,
            use_cache=False
        )
    
    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> APIResponse:
        """Make DELETE request"""
        return await self._make_request(
            HTTPMethod.DELETE, endpoint, params=params, headers=headers,
            use_cache=False
        )
    
    def clear_cache(self) -> None:
        """Clear all cached responses"""
        self._cache.clear()
        logger.info("API response cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'total_entries': len(self._cache),
            'size_bytes': sum(len(str(data)) for data, _ in self._cache.values())
        }
