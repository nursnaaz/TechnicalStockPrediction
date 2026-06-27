"""
Unit Tests for Indicator Calculator

Tests technical indicator calculations with known inputs.
"""

import pytest
import numpy as np
from core.indicator_calculator import IndicatorCalculator
from core.models import StockData, TechnicalIndicators


class TestSMACalculation:
    """Tests for Simple Moving Average calculation."""
    
    def test_sma_with_known_values(self):
        """Test SMA calculation with known price sequence."""
        prices = np.array([10.0, 12.0, 14.0, 16.0, 18.0])
        result = IndicatorCalculator.calculate_sma(prices, 5)
        expected = (10 + 12 + 14 + 16 + 18) / 5  # 14.0
        assert result == pytest.approx(expected, rel=1e-6)
    
    def test_sma_with_partial_period(self):
        """Test SMA uses last N periods when more data available."""
        prices = np.array([10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0])
        result = IndicatorCalculator.calculate_sma(prices, 3)
        expected = (18 + 20 + 22) / 3  # 20.0
        assert result == pytest.approx(expected, rel=1e-6)
    
    def test_sma_insufficient_data(self):
        """Test SMA returns None when insufficient data."""
        prices = np.array([10.0, 12.0])
        result = IndicatorCalculator.calculate_sma(prices, 5)
        assert result is None
    
    def test_sma_exact_period_length(self):
        """Test SMA when data length equals period."""
        prices = np.array([10.0, 20.0, 30.0])
        result = IndicatorCalculator.calculate_sma(prices, 3)
        expected = (10 + 20 + 30) / 3  # 20.0
        assert result == pytest.approx(expected, rel=1e-6)
    
    def test_sma_empty_array(self):
        """Test SMA with empty array."""
        prices = np.array([])
        result = IndicatorCalculator.calculate_sma(prices, 5)
        assert result is None


class TestEMACalculation:
    """Tests for Exponential Moving Average calculation."""
    
    def test_ema_with_known_values(self):
        """Test EMA calculation with known price sequence."""
        prices = np.array([10.0, 12.0, 14.0, 16.0, 18.0])
        period = 3
        result = IndicatorCalculator.calculate_ema(prices, period)
        
        # Manual calculation:
        # multiplier = 2 / (3 + 1) = 0.5
        # Initial EMA (SMA of first 3) = (10 + 12 + 14) / 3 = 12.0
        # EMA after 16: (16 * 0.5) + (12.0 * 0.5) = 14.0
        # EMA after 18: (18 * 0.5) + (14.0 * 0.5) = 16.0
        expected = 16.0
        assert result == pytest.approx(expected, rel=1e-6)
    
    def test_ema_longer_sequence(self):
        """Test EMA with longer price sequence."""
        prices = np.array([22.0, 24.0, 26.0, 28.0, 30.0, 32.0])
        period = 3
        result = IndicatorCalculator.calculate_ema(prices, period)
        
        # Manual calculation:
        # multiplier = 2 / 4 = 0.5
        # Initial EMA = (22 + 24 + 26) / 3 = 24.0
        # After 28: (28 * 0.5) + (24.0 * 0.5) = 26.0
        # After 30: (30 * 0.5) + (26.0 * 0.5) = 28.0
        # After 32: (32 * 0.5) + (28.0 * 0.5) = 30.0
        expected = 30.0
        assert result == pytest.approx(expected, rel=1e-6)
    
    def test_ema_insufficient_data(self):
        """Test EMA returns None when insufficient data."""
        prices = np.array([10.0, 12.0])
        result = IndicatorCalculator.calculate_ema(prices, 5)
        assert result is None
    
    def test_ema_exact_period_length(self):
        """Test EMA when data length equals period."""
        prices = np.array([10.0, 20.0, 30.0])
        result = IndicatorCalculator.calculate_ema(prices, 3)
        # Should equal SMA when no additional data
        expected = (10 + 20 + 30) / 3  # 20.0
        assert result == pytest.approx(expected, rel=1e-6)
    
    def test_ema_empty_array(self):
        """Test EMA with empty array."""
        prices = np.array([])
        result = IndicatorCalculator.calculate_ema(prices, 5)
        assert result is None


class TestMACDCalculation:
    """Tests for MACD calculation."""
    
    def test_macd_with_sufficient_data(self):
        """Test MACD calculation with sufficient data for all components."""
        # Create 40 periods of uptrending data
        prices = np.linspace(100.0, 120.0, 40)
        
        macd_line, signal_line, histogram = IndicatorCalculator.calculate_macd(prices)
        
        # All components should be calculated
        assert macd_line is not None
        assert signal_line is not None
        assert histogram is not None
        
        # Histogram should equal MACD line - Signal line
        assert histogram == pytest.approx(macd_line - signal_line, rel=1e-6)
    
    def test_macd_with_minimal_data_for_line(self):
        """Test MACD with just enough data for MACD line (26 periods)."""
        prices = np.linspace(100.0, 110.0, 26)
        
        macd_line, signal_line, histogram = IndicatorCalculator.calculate_macd(prices)
        
        # MACD line should be calculated
        assert macd_line is not None
        # Signal and histogram need more data
        assert signal_line is None
        assert histogram is None
    
    def test_macd_insufficient_data(self):
        """Test MACD returns None when insufficient data."""
        prices = np.array([100.0, 102.0, 104.0])
        
        macd_line, signal_line, histogram = IndicatorCalculator.calculate_macd(prices)
        
        assert macd_line is None
        assert signal_line is None
        assert histogram is None
    
    def test_macd_uptrend_positive(self):
        """Test MACD line is positive during uptrend."""
        # Strong uptrend should produce positive MACD
        prices = np.linspace(100.0, 150.0, 50)
        
        macd_line, signal_line, histogram = IndicatorCalculator.calculate_macd(prices)
        
        assert macd_line is not None
        assert macd_line > 0  # Should be positive in uptrend
    
    def test_macd_downtrend_negative(self):
        """Test MACD line is negative during downtrend."""
        # Strong downtrend should produce negative MACD
        prices = np.linspace(150.0, 100.0, 50)
        
        macd_line, signal_line, histogram = IndicatorCalculator.calculate_macd(prices)
        
        assert macd_line is not None
        assert macd_line < 0  # Should be negative in downtrend
    
    def test_macd_empty_array(self):
        """Test MACD with empty array."""
        prices = np.array([])
        
        macd_line, signal_line, histogram = IndicatorCalculator.calculate_macd(prices)
        
        assert macd_line is None
        assert signal_line is None
        assert histogram is None


class TestAverageVolumeCalculation:
    """Tests for average volume calculation."""
    
    def test_avg_volume_with_known_values(self):
        """Test average volume calculation with known values."""
        volumes = np.array([1000.0, 2000.0, 3000.0, 4000.0, 5000.0])
        result = IndicatorCalculator.calculate_avg_volume(volumes, 5)
        expected = (1000 + 2000 + 3000 + 4000 + 5000) / 5  # 3000.0
        assert result == pytest.approx(expected, rel=1e-6)
    
    def test_avg_volume_with_partial_period(self):
        """Test average volume uses last N periods."""
        volumes = np.array([1000.0, 2000.0, 3000.0, 4000.0, 5000.0, 6000.0])
        result = IndicatorCalculator.calculate_avg_volume(volumes, 3)
        expected = (4000 + 5000 + 6000) / 3  # 5000.0
        assert result == pytest.approx(expected, rel=1e-6)
    
    def test_avg_volume_insufficient_data(self):
        """Test average volume returns None when insufficient data."""
        volumes = np.array([1000.0, 2000.0])
        result = IndicatorCalculator.calculate_avg_volume(volumes, 5)
        assert result is None
    
    def test_avg_volume_empty_array(self):
        """Test average volume with empty array."""
        volumes = np.array([])
        result = IndicatorCalculator.calculate_avg_volume(volumes, 5)
        assert result is None


class TestRelativeStrengthCalculation:
    """Tests for relative strength calculation."""
    
    def test_relative_strength_outperformance(self):
        """Test relative strength when ticker outperforms market."""
        # Ticker gains 20% (100 -> 120)
        ticker_prices = np.array([100.0, 105.0, 110.0, 115.0, 120.0])
        # Market gains 10% (100 -> 110)
        market_prices = np.array([100.0, 102.5, 105.0, 107.5, 110.0])
        
        result = IndicatorCalculator.calculate_relative_strength(
            ticker_prices, market_prices, 4
        )
        
        # Ticker return: (120 - 100) / 100 = 20%
        # Market return: (110 - 100) / 100 = 10%
        # RS = 20 - 10 = 10 percentage points
        expected = 10.0
        assert result == pytest.approx(expected, rel=1e-6)
    
    def test_relative_strength_underperformance(self):
        """Test relative strength when ticker underperforms market."""
        # Ticker gains 5% (100 -> 105)
        ticker_prices = np.array([100.0, 101.25, 102.5, 103.75, 105.0])
        # Market gains 15% (100 -> 115)
        market_prices = np.array([100.0, 103.75, 107.5, 111.25, 115.0])
        
        result = IndicatorCalculator.calculate_relative_strength(
            ticker_prices, market_prices, 4
        )
        
        # Ticker return: 5%
        # Market return: 15%
        # RS = 5 - 15 = -10 percentage points
        expected = -10.0
        assert result == pytest.approx(expected, rel=1e-6)
    
    def test_relative_strength_equal_performance(self):
        """Test relative strength when ticker matches market."""
        # Both gain 10%
        ticker_prices = np.array([100.0, 105.0, 110.0])
        market_prices = np.array([200.0, 210.0, 220.0])
        
        result = IndicatorCalculator.calculate_relative_strength(
            ticker_prices, market_prices, 2
        )
        
        # Both have 10% return, RS should be ~0
        expected = 0.0
        assert result == pytest.approx(expected, rel=1e-6)
    
    def test_relative_strength_insufficient_ticker_data(self):
        """Test relative strength returns None with insufficient ticker data."""
        ticker_prices = np.array([100.0, 105.0])
        market_prices = np.array([100.0, 102.0, 104.0, 106.0, 108.0])
        
        result = IndicatorCalculator.calculate_relative_strength(
            ticker_prices, market_prices, 4
        )
        
        assert result is None
    
    def test_relative_strength_insufficient_market_data(self):
        """Test relative strength returns None with insufficient market data."""
        ticker_prices = np.array([100.0, 102.0, 104.0, 106.0, 108.0])
        market_prices = np.array([100.0, 105.0])
        
        result = IndicatorCalculator.calculate_relative_strength(
            ticker_prices, market_prices, 4
        )
        
        assert result is None
    
    def test_relative_strength_zero_start_price(self):
        """Test relative strength handles zero start price."""
        ticker_prices = np.array([0.0, 105.0, 110.0])
        market_prices = np.array([100.0, 105.0, 110.0])
        
        result = IndicatorCalculator.calculate_relative_strength(
            ticker_prices, market_prices, 2
        )
        
        assert result is None


class TestCalculateAll:
    """Tests for calculate_all method."""
    
    def test_calculate_all_with_sufficient_data(self):
        """Test calculate_all computes all indicators with sufficient data."""
        # Create 60 periods of data
        prices = np.linspace(100.0, 120.0, 60)
        volumes = np.linspace(1000000.0, 1500000.0, 60)
        timestamps = np.arange(60)
        
        stock_data = StockData(
            ticker="AAPL",
            prices=prices,
            volumes=volumes,
            timestamps=timestamps
        )
        
        market_prices = np.linspace(200.0, 220.0, 60)
        market_data = StockData(
            ticker="SPY",
            prices=market_prices,
            volumes=volumes,
            timestamps=timestamps
        )
        
        calc = IndicatorCalculator()
        indicators = calc.calculate_all(stock_data, market_data)
        
        # All indicators should be calculated
        assert indicators.sma_50 is not None
        assert indicators.ema_20 is not None
        assert indicators.macd_line is not None
        assert indicators.macd_signal is not None
        assert indicators.macd_histogram is not None
        assert indicators.avg_volume_20 is not None
        assert indicators.relative_strength is not None
    
    def test_calculate_all_with_insufficient_data(self):
        """Test calculate_all returns None for unavailable indicators."""
        # Only 10 periods of data
        prices = np.linspace(100.0, 110.0, 10)
        volumes = np.linspace(1000000.0, 1100000.0, 10)
        timestamps = np.arange(10)
        
        stock_data = StockData(
            ticker="TEST",
            prices=prices,
            volumes=volumes,
            timestamps=timestamps
        )
        
        market_data = StockData(
            ticker="SPY",
            prices=prices,
            volumes=volumes,
            timestamps=timestamps
        )
        
        calc = IndicatorCalculator()
        indicators = calc.calculate_all(stock_data, market_data)
        
        # SMA(50) should be None (need 50 periods)
        assert indicators.sma_50 is None
        # EMA(20) should be None (need 20 periods)
        assert indicators.ema_20 is None
        # MACD should be None (need 26+ periods)
        assert indicators.macd_line is None
        # Avg volume should be calculated (have 10 periods, need 20)
        assert indicators.avg_volume_20 is None
        # Relative strength should be None (need 21 periods)
        assert indicators.relative_strength is None
    
    def test_calculate_all_with_partial_data(self):
        """Test calculate_all with data sufficient for some indicators."""
        # 30 periods of data
        prices = np.linspace(100.0, 115.0, 30)
        volumes = np.linspace(1000000.0, 1300000.0, 30)
        timestamps = np.arange(30)
        
        stock_data = StockData(
            ticker="MSFT",
            prices=prices,
            volumes=volumes,
            timestamps=timestamps
        )
        
        market_data = StockData(
            ticker="SPY",
            prices=prices,
            volumes=volumes,
            timestamps=timestamps
        )
        
        calc = IndicatorCalculator()
        indicators = calc.calculate_all(stock_data, market_data)
        
        # SMA(50) should be None
        assert indicators.sma_50 is None
        # EMA(20) should be calculated
        assert indicators.ema_20 is not None
        # MACD line should be calculated (have 30, need 26)
        assert indicators.macd_line is not None
        # Avg volume should be calculated (have 30, need 20)
        assert indicators.avg_volume_20 is not None
        # Relative strength should be calculated (have 30, need 21)
        assert indicators.relative_strength is not None
    
    def test_calculate_all_returns_technical_indicators_instance(self):
        """Test calculate_all returns TechnicalIndicators instance."""
        prices = np.linspace(100.0, 120.0, 60)
        volumes = np.linspace(1000000.0, 1500000.0, 60)
        timestamps = np.arange(60)
        
        stock_data = StockData(
            ticker="GOOGL",
            prices=prices,
            volumes=volumes,
            timestamps=timestamps
        )
        
        market_data = StockData(
            ticker="SPY",
            prices=prices,
            volumes=volumes,
            timestamps=timestamps
        )
        
        calc = IndicatorCalculator()
        indicators = calc.calculate_all(stock_data, market_data)
        
        assert isinstance(indicators, TechnicalIndicators)


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_single_data_point(self):
        """Test indicators with single data point."""
        prices = np.array([100.0])
        volumes = np.array([1000000.0])
        
        # SMA should return None
        assert IndicatorCalculator.calculate_sma(prices, 5) is None
        
        # EMA should return None
        assert IndicatorCalculator.calculate_ema(prices, 5) is None
        
        # MACD should return None
        macd = IndicatorCalculator.calculate_macd(prices)
        assert macd == (None, None, None)
        
        # Avg volume should return None
        assert IndicatorCalculator.calculate_avg_volume(volumes, 5) is None
    
    def test_identical_values(self):
        """Test indicators with identical values."""
        prices = np.array([100.0] * 60)
        volumes = np.array([1000000.0] * 60)
        timestamps = np.arange(60)
        
        stock_data = StockData(
            ticker="FLAT",
            prices=prices,
            volumes=volumes,
            timestamps=timestamps
        )
        
        market_data = StockData(
            ticker="SPY",
            prices=prices,
            volumes=volumes,
            timestamps=timestamps
        )
        
        calc = IndicatorCalculator()
        indicators = calc.calculate_all(stock_data, market_data)
        
        # SMA should equal the constant value
        assert indicators.sma_50 == pytest.approx(100.0, rel=1e-6)
        
        # EMA should equal the constant value
        assert indicators.ema_20 == pytest.approx(100.0, rel=1e-6)
        
        # MACD should be 0 (no difference between EMAs)
        assert indicators.macd_line == pytest.approx(0.0, abs=1e-6)
        
        # Relative strength should be 0 (both have 0% return)
        assert indicators.relative_strength == pytest.approx(0.0, rel=1e-6)
