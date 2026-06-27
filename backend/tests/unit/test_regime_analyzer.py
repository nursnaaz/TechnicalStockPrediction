"""
Unit tests for Market Regime Analyzer

Tests market regime classification logic and error handling.
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, Mock

from api.models import MarketRegime
from core.regime_analyzer import MarketRegimeAnalyzer
from core.api_client import RestApiClient, ApiError
from core.models import StockData


@pytest.fixture
def mock_api_client():
    """Create a mock API client."""
    client = AsyncMock(spec=RestApiClient)
    return client


@pytest.fixture
def regime_analyzer(mock_api_client):
    """Create MarketRegimeAnalyzer instance with mock client."""
    return MarketRegimeAnalyzer(mock_api_client)


def create_spy_data_with_smas(sma_50: float, sma_200: float) -> StockData:
    """
    Create synthetic SPY data that will produce specific SMA values.
    
    Args:
        sma_50: Desired 50-day SMA value
        sma_200: Desired 200-day SMA value
        
    Returns:
        StockData with prices engineered to produce the desired SMAs
    """
    # Create price array with constant values for simplicity
    # Last 50 values will average to sma_50
    # Last 200 values will average to sma_200
    
    # Build price array: first 150 values average to create proper 200-day SMA,
    # last 50 values average to sma_50
    
    # For 200-day SMA = sma_200, and last 50 days = sma_50:
    # sum(all 200) / 200 = sma_200
    # sum(last 50) / 50 = sma_50
    # So: sum(first 150) = 200 * sma_200 - 50 * sma_50
    # And: avg(first 150) = (200 * sma_200 - 50 * sma_50) / 150
    
    first_150_avg = (200 * sma_200 - 50 * sma_50) / 150
    
    prices = np.concatenate([
        np.full(150, first_150_avg),  # First 150 days
        np.full(50, sma_50)           # Last 50 days
    ])
    
    volumes = np.full(200, 50000000.0)
    timestamps = np.arange(200, dtype=np.int64) * 86400000  # Daily timestamps
    
    return StockData(
        ticker="SPY",
        prices=prices,
        volumes=volumes,
        timestamps=timestamps
    )


class TestMarketRegimeAnalyzer:
    """Test suite for MarketRegimeAnalyzer."""
    
    @pytest.mark.asyncio
    async def test_bullish_regime_classification(self, regime_analyzer, mock_api_client):
        """Test bullish regime when SMA_50 > SMA_200."""
        # Arrange: SMA_50 = 450, SMA_200 = 440 (ratio = 1.0227 > 1.0)
        spy_data = create_spy_data_with_smas(sma_50=450.0, sma_200=440.0)
        mock_api_client.fetch_stock_data.return_value = spy_data
        
        # Act
        regime = await regime_analyzer.analyze_regime()
        
        # Assert
        assert regime == MarketRegime.BULLISH
        mock_api_client.fetch_stock_data.assert_called_once_with("SPY", days=250, as_of_date=None)
    
    @pytest.mark.asyncio
    async def test_bearish_regime_classification(self, regime_analyzer, mock_api_client):
        """Test bearish regime when SMA_50 < SMA_200 * 0.98."""
        # Arrange: SMA_50 = 430, SMA_200 = 450 (ratio = 0.9556 < 0.98)
        spy_data = create_spy_data_with_smas(sma_50=430.0, sma_200=450.0)
        mock_api_client.fetch_stock_data.return_value = spy_data
        
        # Act
        regime = await regime_analyzer.analyze_regime()
        
        # Assert
        assert regime == MarketRegime.BEARISH
        mock_api_client.fetch_stock_data.assert_called_once_with("SPY", days=250, as_of_date=None)
    
    @pytest.mark.asyncio
    async def test_neutral_regime_upper_boundary(self, regime_analyzer, mock_api_client):
        """Test neutral regime at upper boundary (ratio just below 1.0)."""
        # Arrange: SMA_50 = 445, SMA_200 = 450 (ratio = 0.9889, within neutral range)
        spy_data = create_spy_data_with_smas(sma_50=445.0, sma_200=450.0)
        mock_api_client.fetch_stock_data.return_value = spy_data
        
        # Act
        regime = await regime_analyzer.analyze_regime()
        
        # Assert
        assert regime == MarketRegime.NEUTRAL
        mock_api_client.fetch_stock_data.assert_called_once_with("SPY", days=250, as_of_date=None)
    
    @pytest.mark.asyncio
    async def test_neutral_regime_lower_boundary(self, regime_analyzer, mock_api_client):
        """Test neutral regime at lower boundary (ratio = 0.98)."""
        # Arrange: SMA_50 = 441, SMA_200 = 450 (ratio = 0.98, exactly at boundary)
        spy_data = create_spy_data_with_smas(sma_50=441.0, sma_200=450.0)
        mock_api_client.fetch_stock_data.return_value = spy_data
        
        # Act
        regime = await regime_analyzer.analyze_regime()
        
        # Assert
        assert regime == MarketRegime.NEUTRAL
        mock_api_client.fetch_stock_data.assert_called_once_with("SPY", days=250, as_of_date=None)
    
    @pytest.mark.asyncio
    async def test_api_failure_defaults_to_neutral(self, regime_analyzer, mock_api_client):
        """Test that API failures default to NEUTRAL regime."""
        # Arrange: API client raises ApiError
        mock_api_client.fetch_stock_data.side_effect = ApiError("API connection failed")
        
        # Act
        regime = await regime_analyzer.analyze_regime()
        
        # Assert
        assert regime == MarketRegime.NEUTRAL
        mock_api_client.fetch_stock_data.assert_called_once_with("SPY", days=250, as_of_date=None)
    
    @pytest.mark.asyncio
    async def test_unexpected_error_defaults_to_neutral(self, regime_analyzer, mock_api_client):
        """Test that unexpected errors default to NEUTRAL regime."""
        # Arrange: API client raises unexpected exception
        mock_api_client.fetch_stock_data.side_effect = ValueError("Unexpected error")
        
        # Act
        regime = await regime_analyzer.analyze_regime()
        
        # Assert
        assert regime == MarketRegime.NEUTRAL
        mock_api_client.fetch_stock_data.assert_called_once_with("SPY", days=250, as_of_date=None)
    
    @pytest.mark.asyncio
    async def test_insufficient_data_for_sma_50(self, regime_analyzer, mock_api_client):
        """Test handling of insufficient data for 50-day SMA."""
        # Arrange: Only 30 data points (insufficient for 50-day SMA)
        spy_data = StockData(
            ticker="SPY",
            prices=np.array([450.0] * 30),
            volumes=np.array([50000000.0] * 30),
            timestamps=np.arange(30, dtype=np.int64) * 86400000
        )
        mock_api_client.fetch_stock_data.return_value = spy_data
        
        # Act
        regime = await regime_analyzer.analyze_regime()
        
        # Assert
        assert regime == MarketRegime.NEUTRAL
        mock_api_client.fetch_stock_data.assert_called_once_with("SPY", days=250, as_of_date=None)
    
    @pytest.mark.asyncio
    async def test_insufficient_data_for_sma_200(self, regime_analyzer, mock_api_client):
        """Test handling of insufficient data for 200-day SMA."""
        # Arrange: Only 150 data points (insufficient for 200-day SMA)
        spy_data = StockData(
            ticker="SPY",
            prices=np.array([450.0] * 150),
            volumes=np.array([50000000.0] * 150),
            timestamps=np.arange(150, dtype=np.int64) * 86400000
        )
        mock_api_client.fetch_stock_data.return_value = spy_data
        
        # Act
        regime = await regime_analyzer.analyze_regime()
        
        # Assert
        assert regime == MarketRegime.NEUTRAL
        mock_api_client.fetch_stock_data.assert_called_once_with("SPY", days=250, as_of_date=None)
    
    @pytest.mark.asyncio
    async def test_sma_calculation_accuracy(self, regime_analyzer, mock_api_client):
        """Test SMA calculation with known values."""
        # Arrange: Create data where we can manually verify SMA calculations
        # Prices: last 50 values = 100, first 150 values chosen so SMA_200 = 95
        # SMA_50 = 100
        # For SMA_200 = 95: sum(all 200) = 95 * 200 = 19000
        # sum(last 50) = 100 * 50 = 5000
        # sum(first 150) = 19000 - 5000 = 14000
        # avg(first 150) = 14000 / 150 = 93.333...
        
        prices = np.concatenate([
            np.full(150, 93.333333),
            np.full(50, 100.0)
        ])
        
        spy_data = StockData(
            ticker="SPY",
            prices=prices,
            volumes=np.full(200, 50000000.0),
            timestamps=np.arange(200, dtype=np.int64) * 86400000
        )
        mock_api_client.fetch_stock_data.return_value = spy_data
        
        # Act
        regime = await regime_analyzer.analyze_regime()
        
        # Assert
        # SMA_50 = 100, SMA_200 ≈ 95, ratio ≈ 1.053 > 1.0 → BULLISH
        assert regime == MarketRegime.BULLISH
    
    def test_sma_calculation_static_method(self):
        """Test the static _calculate_sma method directly."""
        analyzer = MarketRegimeAnalyzer(None)  # No client needed for static method
        
        # Test with sufficient data
        prices = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        sma = analyzer._calculate_sma(prices, 3)
        assert sma == pytest.approx(40.0)  # (30 + 40 + 50) / 3 = 40
        
        # Test with exact period length
        sma = analyzer._calculate_sma(prices, 5)
        assert sma == pytest.approx(30.0)  # (10 + 20 + 30 + 40 + 50) / 5 = 30
        
        # Test with insufficient data
        sma = analyzer._calculate_sma(prices, 10)
        assert sma is None
        
        # Test with empty array
        sma = analyzer._calculate_sma(np.array([]), 5)
        assert sma is None
    
    @pytest.mark.asyncio
    async def test_bullish_regime_edge_case_just_above_threshold(self, regime_analyzer, mock_api_client):
        """Test bullish regime just above ratio = 1.0."""
        # Arrange: SMA_50 = 450.1, SMA_200 = 450 (ratio = 1.00022 > 1.0)
        spy_data = create_spy_data_with_smas(sma_50=450.1, sma_200=450.0)
        mock_api_client.fetch_stock_data.return_value = spy_data
        
        # Act
        regime = await regime_analyzer.analyze_regime()
        
        # Assert
        assert regime == MarketRegime.BULLISH
    
    @pytest.mark.asyncio
    async def test_bearish_regime_edge_case_just_below_threshold(self, regime_analyzer, mock_api_client):
        """Test bearish regime just below ratio = 0.98."""
        # Arrange: SMA_50 = 440.9, SMA_200 = 450 (ratio = 0.9798 < 0.98)
        spy_data = create_spy_data_with_smas(sma_50=440.9, sma_200=450.0)
        mock_api_client.fetch_stock_data.return_value = spy_data
        
        # Act
        regime = await regime_analyzer.analyze_regime()
        
        # Assert
        assert regime == MarketRegime.BEARISH
