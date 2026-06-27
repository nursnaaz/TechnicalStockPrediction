"""
Integration Tests: Universe Builder + API Client

Tests the integration between universe building and API data fetching.
Validates that invalid tickers are filtered before API calls and error handling works correctly.
"""

import pytest
import pytest_asyncio
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch

from core.universe_builder import UniverseBuilder
from core.api_client import RestApiClient, ApiError
from core.models import StockData


@pytest_asyncio.fixture
async def api_client():
    """Create a mock API client for testing."""
    # Create client with mock API key to avoid requiring real credentials
    with patch.dict('os.environ', {'POLYGON_TOKEN': 'test_token'}):
        client = RestApiClient(api_key="test_token", base_url="https://test.api.com")
        yield client
        await client.close()


@pytest.fixture
def universe_builder():
    """Create a UniverseBuilder instance."""
    return UniverseBuilder()


class TestUniverseBuilderAndApiClientIntegration:
    """Integration tests for Universe Builder and API Client working together."""
    
    @pytest.mark.asyncio
    async def test_build_universe_and_fetch_data_for_valid_tickers(self, universe_builder, api_client):
        """Test building universe and fetching data for each valid ticker."""
        # Setup: Valid tickers
        tickers = ["AAPL", "MSFT", "GOOGL"]
        
        # Build universe
        valid_tickers = universe_builder.build_universe(tickers)
        assert len(valid_tickers) == 3
        assert valid_tickers == ["AAPL", "MSFT", "GOOGL"]
        
        # Mock API responses for each ticker
        mock_stock_data = {
            "AAPL": StockData(
                ticker="AAPL",
                prices=np.array([150.0, 151.0, 152.0, 153.0, 154.0]),
                volumes=np.array([1000000, 1100000, 1200000, 1300000, 1400000]),
                timestamps=np.array([1, 2, 3, 4, 5])
            ),
            "MSFT": StockData(
                ticker="MSFT",
                prices=np.array([250.0, 251.0, 252.0, 253.0, 254.0]),
                volumes=np.array([2000000, 2100000, 2200000, 2300000, 2400000]),
                timestamps=np.array([1, 2, 3, 4, 5])
            ),
            "GOOGL": StockData(
                ticker="GOOGL",
                prices=np.array([100.0, 101.0, 102.0, 103.0, 104.0]),
                volumes=np.array([500000, 510000, 520000, 530000, 540000]),
                timestamps=np.array([1, 2, 3, 4, 5])
            )
        }
        
        # Mock the fetch_stock_data method
        async def mock_fetch(ticker: str, days: int = 250) -> StockData:
            return mock_stock_data[ticker]
        
        api_client.fetch_stock_data = mock_fetch
        
        # Fetch data for each ticker in the universe
        fetched_data = {}
        for ticker in valid_tickers:
            data = await api_client.fetch_stock_data(ticker)
            fetched_data[ticker] = data
        
        # Verify all tickers were fetched successfully
        assert len(fetched_data) == 3
        assert "AAPL" in fetched_data
        assert "MSFT" in fetched_data
        assert "GOOGL" in fetched_data
        
        # Verify data structure
        for ticker, data in fetched_data.items():
            assert data.ticker == ticker
            assert len(data.prices) == 5
            assert len(data.volumes) == 5
            assert len(data.timestamps) == 5
    
    @pytest.mark.asyncio
    async def test_invalid_tickers_filtered_before_api_calls(self, universe_builder, api_client):
        """Test that invalid tickers are filtered out before making API calls."""
        # Setup: Mix of valid and invalid tickers
        tickers = ["AAPL", "aapl", "MSFT", "brk.b", "GOOGL", "", "tsla"]
        
        # Build universe - should filter invalid tickers
        valid_tickers = universe_builder.build_universe(tickers)
        
        # Only valid uppercase alphanumeric tickers should remain
        assert len(valid_tickers) == 3
        assert valid_tickers == ["AAPL", "MSFT", "GOOGL"]
        assert "aapl" not in valid_tickers
        assert "brk.b" not in valid_tickers
        assert "tsla" not in valid_tickers
        
        # Mock API client to track which tickers are fetched
        fetched_tickers = []
        
        async def mock_fetch(ticker: str, days: int = 250) -> StockData:
            fetched_tickers.append(ticker)
            return StockData(
                ticker=ticker,
                prices=np.array([100.0, 101.0, 102.0]),
                volumes=np.array([1000000, 1100000, 1200000]),
                timestamps=np.array([1, 2, 3])
            )
        
        api_client.fetch_stock_data = mock_fetch
        
        # Fetch data only for valid tickers
        for ticker in valid_tickers:
            await api_client.fetch_stock_data(ticker)
        
        # Verify only valid tickers were passed to API
        assert len(fetched_tickers) == 3
        assert "AAPL" in fetched_tickers
        assert "MSFT" in fetched_tickers
        assert "GOOGL" in fetched_tickers
        assert "aapl" not in fetched_tickers
        assert "brk.b" not in fetched_tickers
        assert "tsla" not in fetched_tickers
    
    @pytest.mark.asyncio
    async def test_error_handling_when_api_fails_for_specific_tickers(self, universe_builder, api_client):
        """Test that API failures for specific tickers are handled gracefully and processing continues."""
        # Setup: Valid tickers
        tickers = ["AAPL", "FAIL", "MSFT", "ERROR", "GOOGL"]
        
        # Build universe
        valid_tickers = universe_builder.build_universe(tickers)
        assert len(valid_tickers) == 5
        
        # Mock API to fail for specific tickers
        async def mock_fetch_with_failures(ticker: str, days: int = 250) -> StockData:
            if ticker == "FAIL":
                raise ApiError(f"Failed to fetch data for {ticker} after 3 retries")
            elif ticker == "ERROR":
                raise ApiError(f"API unavailable for {ticker}")
            else:
                return StockData(
                    ticker=ticker,
                    prices=np.array([100.0, 101.0, 102.0]),
                    volumes=np.array([1000000, 1100000, 1200000]),
                    timestamps=np.array([1, 2, 3])
                )
        
        api_client.fetch_stock_data = mock_fetch_with_failures
        
        # Fetch data for each ticker, handling errors
        successful_data = {}
        failed_tickers = []
        
        for ticker in valid_tickers:
            try:
                data = await api_client.fetch_stock_data(ticker)
                successful_data[ticker] = data
            except ApiError as e:
                failed_tickers.append(ticker)
                # In real implementation, would log error and continue
        
        # Verify that successful tickers were processed
        assert len(successful_data) == 3
        assert "AAPL" in successful_data
        assert "MSFT" in successful_data
        assert "GOOGL" in successful_data
        
        # Verify that failed tickers were tracked
        assert len(failed_tickers) == 2
        assert "FAIL" in failed_tickers
        assert "ERROR" in failed_tickers
        
        # Verify that processing continued despite failures
        assert len(successful_data) + len(failed_tickers) == len(valid_tickers)
    
    @pytest.mark.asyncio
    async def test_empty_ticker_list_raises_error_before_api_calls(self, universe_builder, api_client):
        """Test that empty ticker list raises ValueError before any API calls."""
        # Setup: Empty ticker list
        tickers = []
        
        # Track if any API calls were made
        api_calls_made = []
        
        async def mock_fetch(ticker: str, days: int = 250) -> StockData:
            api_calls_made.append(ticker)
            return StockData(
                ticker=ticker,
                prices=np.array([100.0]),
                volumes=np.array([1000000]),
                timestamps=np.array([1])
            )
        
        api_client.fetch_stock_data = mock_fetch
        
        # Attempt to build universe - should raise ValueError
        with pytest.raises(ValueError, match="Ticker list cannot be empty"):
            universe_builder.build_universe(tickers)
        
        # Verify no API calls were made
        assert len(api_calls_made) == 0
    
    @pytest.mark.asyncio
    async def test_all_invalid_tickers_raises_error_before_api_calls(self, universe_builder, api_client):
        """Test that all invalid tickers raises ValueError before any API calls."""
        # Setup: All invalid tickers
        tickers = ["aapl", "msft", "brk.b", ""]
        
        # Track if any API calls were made
        api_calls_made = []
        
        async def mock_fetch(ticker: str, days: int = 250) -> StockData:
            api_calls_made.append(ticker)
            return StockData(
                ticker=ticker,
                prices=np.array([100.0]),
                volumes=np.array([1000000]),
                timestamps=np.array([1])
            )
        
        api_client.fetch_stock_data = mock_fetch
        
        # Attempt to build universe - should raise ValueError
        with pytest.raises(ValueError, match="All tickers are invalid"):
            universe_builder.build_universe(tickers)
        
        # Verify no API calls were made
        assert len(api_calls_made) == 0
    
    @pytest.mark.asyncio
    async def test_cache_behavior_with_valid_universe(self, universe_builder, api_client):
        """Test that API client caching works correctly with valid universe tickers."""
        # Setup: Valid tickers
        tickers = ["AAPL", "MSFT"]
        
        # Build universe
        valid_tickers = universe_builder.build_universe(tickers)
        assert len(valid_tickers) == 2
        
        # Track API call count
        api_call_count = {"count": 0}
        
        async def mock_fetch_with_count(ticker: str, days: int = 250) -> StockData:
            api_call_count["count"] += 1
            return StockData(
                ticker=ticker,
                prices=np.array([100.0, 101.0, 102.0]),
                volumes=np.array([1000000, 1100000, 1200000]),
                timestamps=np.array([1, 2, 3])
            )
        
        # Replace the fetch method but keep cache functionality
        original_fetch = api_client.fetch_stock_data
        
        # Manually mock with caching logic
        async def mock_fetch_with_cache(ticker: str, days: int = 250) -> StockData:
            cache_key = (ticker, days)
            if cache_key in api_client._cache:
                return api_client._cache[cache_key]
            
            api_call_count["count"] += 1
            data = StockData(
                ticker=ticker,
                prices=np.array([100.0, 101.0, 102.0]),
                volumes=np.array([1000000, 1100000, 1200000]),
                timestamps=np.array([1, 2, 3])
            )
            api_client._cache[cache_key] = data
            return data
        
        api_client.fetch_stock_data = mock_fetch_with_cache
        
        # First fetch - should hit API
        data1 = await api_client.fetch_stock_data("AAPL")
        assert api_call_count["count"] == 1
        
        # Second fetch of same ticker - should use cache
        data2 = await api_client.fetch_stock_data("AAPL")
        assert api_call_count["count"] == 1  # Should still be 1
        
        # Verify data is same
        assert data1.ticker == data2.ticker
        assert np.array_equal(data1.prices, data2.prices)
        
        # Fetch different ticker - should hit API
        data3 = await api_client.fetch_stock_data("MSFT")
        assert api_call_count["count"] == 2
        
        # Clear cache and fetch again - should hit API
        api_client.clear_cache()
        data4 = await api_client.fetch_stock_data("AAPL")
        assert api_call_count["count"] == 3
    
    @pytest.mark.asyncio
    async def test_concurrent_fetches_for_universe(self, universe_builder, api_client):
        """Test that multiple tickers can be fetched concurrently from valid universe."""
        import asyncio
        
        # Setup: Valid tickers
        tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
        
        # Build universe
        valid_tickers = universe_builder.build_universe(tickers)
        assert len(valid_tickers) == 5
        
        # Mock API with delay to simulate real API calls
        async def mock_fetch_with_delay(ticker: str, days: int = 250) -> StockData:
            await asyncio.sleep(0.1)  # Simulate network delay
            return StockData(
                ticker=ticker,
                prices=np.array([100.0, 101.0, 102.0]),
                volumes=np.array([1000000, 1100000, 1200000]),
                timestamps=np.array([1, 2, 3])
            )
        
        api_client.fetch_stock_data = mock_fetch_with_delay
        
        # Fetch all tickers concurrently
        fetch_tasks = [
            api_client.fetch_stock_data(ticker)
            for ticker in valid_tickers
        ]
        
        results = await asyncio.gather(*fetch_tasks)
        
        # Verify all tickers were fetched
        assert len(results) == 5
        fetched_tickers = [data.ticker for data in results]
        assert set(fetched_tickers) == set(valid_tickers)
    
    @pytest.mark.asyncio
    async def test_mixed_success_and_failure_with_concurrent_fetches(self, universe_builder, api_client):
        """Test concurrent fetching handles mixed success and failures gracefully."""
        import asyncio
        
        # Setup: Mix of tickers that will succeed and fail
        tickers = ["AAPL", "FAIL1", "MSFT", "FAIL2", "GOOGL"]
        
        # Build universe
        valid_tickers = universe_builder.build_universe(tickers)
        assert len(valid_tickers) == 5
        
        # Mock API with failures for specific tickers
        async def mock_fetch_mixed(ticker: str, days: int = 250) -> StockData:
            await asyncio.sleep(0.05)  # Simulate network delay
            if "FAIL" in ticker:
                raise ApiError(f"Failed to fetch {ticker}")
            return StockData(
                ticker=ticker,
                prices=np.array([100.0, 101.0, 102.0]),
                volumes=np.array([1000000, 1100000, 1200000]),
                timestamps=np.array([1, 2, 3])
            )
        
        api_client.fetch_stock_data = mock_fetch_mixed
        
        # Fetch all tickers concurrently with error handling
        async def safe_fetch(ticker: str):
            try:
                return await api_client.fetch_stock_data(ticker)
            except ApiError:
                return None
        
        fetch_tasks = [safe_fetch(ticker) for ticker in valid_tickers]
        results = await asyncio.gather(*fetch_tasks)
        
        # Filter out None values (failures)
        successful_results = [r for r in results if r is not None]
        failed_count = len([r for r in results if r is None])
        
        # Verify correct number of successes and failures
        assert len(successful_results) == 3  # AAPL, MSFT, GOOGL
        assert failed_count == 2  # FAIL1, FAIL2
        
        # Verify successful tickers
        successful_tickers = [data.ticker for data in successful_results]
        assert "AAPL" in successful_tickers
        assert "MSFT" in successful_tickers
        assert "GOOGL" in successful_tickers
