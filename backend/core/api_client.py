"""
REST API Client

Manages communication with external market data API (Polygon.io).
Handles authentication, connection pooling, retry logic, and caching.
"""

import asyncio
import logging
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta

import httpx
import numpy as np

from core.models import StockData
from config import config


logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Exception raised when API requests fail after retries."""
    pass


class RestApiClient:
    """Client for external market data API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_concurrent: int = 5,
        max_retries: int = 3
    ):
        """
        Initialize REST API client.
        
        Args:
            api_key: API authentication token (defaults to config.POLYGON_TOKEN)
            base_url: Base URL for API (defaults to config.API_BASE_URL)
            max_concurrent: Maximum concurrent connections (default: 5)
            max_retries: Maximum retry attempts (default: 3)
        """
        self.api_key = api_key or config.POLYGON_TOKEN
        self.base_url = base_url or config.API_BASE_URL
        self.max_retries = max_retries
        
        if not self.api_key:
            raise ValueError("API key is required. Set POLYGON_TOKEN environment variable.")
        
        # Configure httpx client with connection limits
        limits = httpx.Limits(max_connections=max_concurrent, max_keepalive_connections=max_concurrent)
        self.client = httpx.AsyncClient(
            limits=limits,
            timeout=30.0,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        
        # In-memory cache keyed by (ticker, days)
        self._cache: Dict[Tuple[str, int], StockData] = {}
        
        logger.info(f"RestApiClient initialized with max {max_concurrent} concurrent connections")
    
    async def fetch_stock_data(self, ticker: str, days: int = 250) -> StockData:
        """
        Fetch historical price and volume data for a ticker.
        
        Uses Polygon.io aggregates endpoint: /v2/aggs/ticker/{ticker}/range/1/day/{from}/{to}
        
        Args:
            ticker: Stock symbol (e.g., "AAPL")
            days: Number of historical days to fetch (default: 250)
            
        Returns:
            StockData with prices, volumes, timestamps
            
        Raises:
            ApiError: After max_retries failed attempts
        """
        # Check cache first
        cache_key = (ticker, days)
        if cache_key in self._cache:
            logger.debug(f"Cache hit for {ticker} ({days} days)")
            return self._cache[cache_key]
        
        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        
        # Format dates as YYYY-MM-DD
        from_str = from_date.strftime("%Y-%m-%d")
        to_str = to_date.strftime("%Y-%m-%d")
        
        # Construct endpoint URL
        # Polygon.io format: /v2/aggs/ticker/{ticker}/range/1/day/{from}/{to}
        endpoint = f"/v2/aggs/ticker/{ticker}/range/1/day/{from_str}/{to_str}"
        url = f"{self.base_url}{endpoint}"
        
        # Add API key as query parameter for Polygon.io
        params = {"apiKey": self.api_key, "adjusted": "true", "sort": "asc"}
        
        # Retry with exponential backoff
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Fetching {ticker} data (attempt {attempt}/{self.max_retries})")
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                
                # Parse response
                data = response.json()
                
                # Polygon.io returns results in "results" array
                if "results" not in data or not data["results"]:
                    logger.warning(f"No data returned for {ticker}")
                    raise ApiError(f"No data available for {ticker}")
                
                results = data["results"]
                
                # Extract prices, volumes, timestamps
                prices = np.array([bar["c"] for bar in results], dtype=np.float64)
                volumes = np.array([bar["v"] for bar in results], dtype=np.float64)
                timestamps = np.array([bar["t"] for bar in results], dtype=np.int64)
                
                stock_data = StockData(
                    ticker=ticker,
                    prices=prices,
                    volumes=volumes,
                    timestamps=timestamps
                )
                
                # Cache the result
                self._cache[cache_key] = stock_data
                
                logger.info(f"Successfully fetched {len(prices)} data points for {ticker}")
                return stock_data
                
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    f"HTTP error fetching {ticker} (attempt {attempt}/{self.max_retries}): "
                    f"Status {e.response.status_code}"
                )
            except httpx.RequestError as e:
                last_error = e
                logger.warning(
                    f"Request error fetching {ticker} (attempt {attempt}/{self.max_retries}): {e}"
                )
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Unexpected error fetching {ticker} (attempt {attempt}/{self.max_retries}): {e}"
                )
            
            # Exponential backoff: 1s, 2s, 4s
            if attempt < self.max_retries:
                delay = 2 ** (attempt - 1)  # 1, 2, 4
                logger.debug(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)
        
        # All retries exhausted
        logger.error(f"Failed to fetch {ticker} after {self.max_retries} attempts")
        raise ApiError(f"Failed to fetch data for {ticker} after {self.max_retries} retries: {last_error}")
    
    def clear_cache(self) -> None:
        """Clear in-memory cache. Called at start of new scan session."""
        logger.debug(f"Clearing cache ({len(self._cache)} entries)")
        self._cache.clear()
    
    async def close(self) -> None:
        """Close the HTTP client. Should be called on shutdown."""
        await self.client.aclose()
        logger.info("RestApiClient closed")
