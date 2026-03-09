"""
HTTP Client Manager for Enterprise-Grade Session Handling
=========================================================
Provides singleton aiohttp session management with proper lifecycle handling.
Ensures sessions are always properly closed to prevent resource leaks.
"""

import aiohttp
import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class HttpClientManager:
    """
    Manages aiohttp sessions with proper lifecycle handling.
    Uses singleton pattern to ensure consistent session reuse.
    """
    
    _instance: Optional['HttpClientManager'] = None
    _lock: asyncio.Lock = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
        self._closed = False
        self._initialized = True
        logger.info("HttpClientManager initialized")
    
    async def get_session(self) -> aiohttp.ClientSession:
        """
        Get or create the shared aiohttp session.
        Thread-safe singleton access.
        """
        if self._closed:
            raise RuntimeError("HttpClientManager has been shut down")
            
        if self._session is None or self._session.closed:
            async with self._lock:
                # Double-check after acquiring lock
                if self._session is None or self._session.closed:
                    logger.info("Creating new aiohttp ClientSession")
                    connector = aiohttp.TCPConnector(
                        limit=100,  # Max concurrent connections
                        limit_per_host=30,
                        keepalive_timeout=30,
                        enable_cleanup_closed=True,
                    )
                    self._session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=aiohttp.ClientTimeout(total=60, connect=10),
                    )
        return self._session
    
    @asynccontextmanager
    async def request(self, method: str, url: str, **kwargs):
        """
        Context manager for HTTP requests with automatic session handling.
        Ensures proper cleanup even on exceptions.
        """
        session = await self.get_session()
        async with session.request(method, url, **kwargs) as response:
            yield response
    
    async def close(self):
        """
        Properly close the session and release resources.
        Call this on application shutdown.
        """
        async with self._lock:
            if self._session is not None and not self._session.closed:
                logger.info("Closing aiohttp ClientSession")
                await self._session.close()
                # Give time for graceful closure
                await asyncio.sleep(0.25)
                self._session = None
            self._closed = True
            logger.info("HttpClientManager shutdown complete")
    
    def is_closed(self) -> bool:
        """Check if the manager has been shut down."""
        return self._closed


# Singleton accessor
_client_manager: Optional[HttpClientManager] = None


def get_http_client() -> HttpClientManager:
    """Get the singleton HTTP client manager."""
    global _client_manager
    if _client_manager is None:
        _client_manager = HttpClientManager()
    return _client_manager


async def close_http_client():
    """Call this on application shutdown to clean up resources."""
    global _client_manager
    if _client_manager is not None:
        await _client_manager.close()
        _client_manager = None
