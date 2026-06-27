"""
Property-Based Tests for Indicator Calculator

Tests mathematical properties and invariants for technical indicator calculations.
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, assume, settings
from core.indicator_calculator import IndicatorCalculator


# Custom strategies for price and volume data
def price_array_strategy(min_size=50, max_size=250, min_price=1.0, max_price=1000.0):
    """Generate realistic price arrays."""
    return st.lists(
        st.floats(min_value=min_price, max_value=max_price, allow_nan=False, allow_infinity=False),
        min_size=min_size,
        max_size=max_size
    ).map(lambda x: np.array(x))


def volume_array_strategy(min_size=50, max_size=250):
    """Generate realistic volume arrays."""
    return st.lists(
        st.integers(min_value=1000, max_value=1000000000),
        min_size=min_size,
        max_size=max_size
    ).map(lambda x: np.array(x, dtype=np.float64))


class TestSMAProperties:
    """Property-based tests for SMA calculation."""
    
    @settings(max_examples=20)
    @given(price_array_strategy(min_size=50, max_size=250))
    def test_property_6_sma_calculation_correctness(self, prices: np.ndarray):
        """
        Property 6: SMA Calculation Correctness
        **Validates: Requirements 4.1**
        
        Property: For any price sequence with sufficient data, the calculated
        50-day Simple Moving Average SHALL equal the arithmetic mean of the
        last 50 prices.
        """
        calc = IndicatorCalculator()
        sma_50 = calc.calculate_sma(prices, 50)
        
        # Should not return None with sufficient data
        assert sma_50 is not None
        
        # Calculate expected SMA manually
        expected_sma = np.mean(prices[-50:])
        
        # Should match within floating point tolerance
        assert abs(sma_50 - expected_sma) < 1e-9
    
    @settings(max_examples=20)
    @given(
        price_array_strategy(min_size=50, max_size=250),
        st.integers(min_value=1, max_value=50)
    )
    def test_property_sma_with_various_periods(self, prices: np.ndarray, period: int):
        """
        Property 6: SMA Calculation Correctness (Extended)
        **Validates: Requirements 4.1**
        
        Property: For any valid period, SMA should equal the arithmetic mean
        of the last 'period' prices.
        """
        assume(len(prices) >= period)
        
        calc = IndicatorCalculator()
        sma = calc.calculate_sma(prices, period)
        
        assert sma is not None
        expected_sma = np.mean(prices[-period:])
        assert abs(sma - expected_sma) < 1e-9
    
    @settings(max_examples=20)
    @given(price_array_strategy(min_size=1, max_size=49))
    def test_property_sma_insufficient_data(self, prices: np.ndarray):
        """
        Property 6: SMA Calculation Correctness (Insufficient Data)
        **Validates: Requirements 4.1**
        
        Property: When insufficient data is available (< 50 prices),
        SMA should return None.
        """
        calc = IndicatorCalculator()
        sma_50 = calc.calculate_sma(prices, 50)
        
        assert sma_50 is None
    
    @settings(max_examples=20)
    @given(price_array_strategy(min_size=50, max_size=250))
    def test_property_sma_range_bounds(self, prices: np.ndarray):
        """
        Property 6: SMA Calculation Correctness (Range Bounds)
        **Validates: Requirements 4.1**
        
        Property: SMA should be within the range of the prices used for calculation.
        """
        calc = IndicatorCalculator()
        sma_50 = calc.calculate_sma(prices, 50)
        
        assert sma_50 is not None
        
        min_price = np.min(prices[-50:])
        max_price = np.max(prices[-50:])
        
        # SMA should be within min and max of the window
        assert min_price <= sma_50 <= max_price


class TestEMAProperties:
    """Property-based tests for EMA calculation."""
    
    @settings(max_examples=20)
    @given(price_array_strategy(min_size=20, max_size=250))
    def test_property_7_ema_calculation_correctness(self, prices: np.ndarray):
        """
        Property 7: EMA Calculation Correctness
        **Validates: Requirements 4.2**
        
        Property: For any price sequence with sufficient data, the calculated
        20-day Exponential Moving Average SHALL correctly apply the EMA formula
        with multiplier 2/(period+1) at each step.
        """
        calc = IndicatorCalculator()
        ema_20 = calc.calculate_ema(prices, 20)
        
        assert ema_20 is not None
        
        # Calculate EMA manually using the same formula
        period = 20
        multiplier = 2 / (period + 1)
        
        # Start with SMA of first 'period' prices
        expected_ema = float(np.mean(prices[:period]))
        
        # Apply EMA formula iteratively
        for price in prices[period:]:
            expected_ema = (price * multiplier) + (expected_ema * (1 - multiplier))
        
        # Should match within floating point tolerance
        assert abs(ema_20 - expected_ema) < 1e-9
    
    @settings(max_examples=20)
    @given(
        price_array_strategy(min_size=50, max_size=250),
        st.integers(min_value=5, max_value=50)
    )
    def test_property_ema_with_various_periods(self, prices: np.ndarray, period: int):
        """
        Property 7: EMA Calculation Correctness (Extended)
        **Validates: Requirements 4.2**
        
        Property: For any valid period, EMA should correctly apply the formula.
        """
        assume(len(prices) >= period)
        
        calc = IndicatorCalculator()
        ema = calc.calculate_ema(prices, period)
        
        assert ema is not None
        
        # Calculate manually
        multiplier = 2 / (period + 1)
        expected_ema = float(np.mean(prices[:period]))
        for price in prices[period:]:
            expected_ema = (price * multiplier) + (expected_ema * (1 - multiplier))
        
        assert abs(ema - expected_ema) < 1e-9
    
    @settings(max_examples=20)
    @given(price_array_strategy(min_size=1, max_size=19))
    def test_property_ema_insufficient_data(self, prices: np.ndarray):
        """
        Property 7: EMA Calculation Correctness (Insufficient Data)
        **Validates: Requirements 4.2**
        
        Property: When insufficient data is available (< 20 prices),
        EMA should return None.
        """
        calc = IndicatorCalculator()
        ema_20 = calc.calculate_ema(prices, 20)
        
        assert ema_20 is None
    
    @settings(max_examples=20)
    @given(price_array_strategy(min_size=20, max_size=250))
    def test_property_ema_converges_to_recent_prices(self, prices: np.ndarray):
        """
        Property 7: EMA Calculation Correctness (Convergence)
        **Validates: Requirements 4.2**
        
        Property: EMA should be closer to recent prices than to older prices
        (weighted towards recent data).
        """
        calc = IndicatorCalculator()
        ema_20 = calc.calculate_ema(prices, 20)
        
        assert ema_20 is not None
        
        # EMA should be closer to the last price than to the first price in the window
        # (though not always, depends on trend)
        # At minimum, EMA should be within the range of recent prices
        recent_min = np.min(prices[-20:])
        recent_max = np.max(prices[-20:])
        
        # EMA might be slightly outside due to historical influence, but should be close
        # Allow 10% margin
        margin = 0.1 * (recent_max - recent_min)
        assert recent_min - margin <= ema_20 <= recent_max + margin


class TestMACDProperties:
    """Property-based tests for MACD calculation."""
    
    @settings(max_examples=20)
    @given(price_array_strategy(min_size=34, max_size=250))
    def test_property_8_macd_calculation_correctness(self, prices: np.ndarray):
        """
        Property 8: MACD Calculation Correctness
        **Validates: Requirements 4.3**
        
        Property: For any price sequence with sufficient data, the MACD indicator
        SHALL correctly compute the MACD line as EMA(12) - EMA(26), the signal line
        as EMA(9) of the MACD line, and the histogram as MACD line minus signal line.
        """
        calc = IndicatorCalculator()
        macd_line, signal_line, histogram = calc.calculate_macd(prices)
        
        # Should have all values with sufficient data
        assert macd_line is not None
        assert signal_line is not None
        assert histogram is not None
        
        # Verify MACD line = EMA(12) - EMA(26)
        ema_12 = calc.calculate_ema(prices, 12)
        ema_26 = calc.calculate_ema(prices, 26)
        expected_macd_line = ema_12 - ema_26
        
        assert abs(macd_line - expected_macd_line) < 1e-9
        
        # Verify histogram = MACD line - signal line
        expected_histogram = macd_line - signal_line
        assert abs(histogram - expected_histogram) < 1e-9
    
    @settings(max_examples=20)
    @given(price_array_strategy(min_size=34, max_size=250))
    def test_property_macd_signal_line_correctness(self, prices: np.ndarray):
        """
        Property 8: MACD Calculation Correctness (Signal Line)
        **Validates: Requirements 4.3**
        
        Property: Signal line should be EMA(9) of the MACD line values.
        """
        calc = IndicatorCalculator()
        _, signal_line, _ = calc.calculate_macd(prices)
        
        assert signal_line is not None
        
        # Calculate MACD values manually for the last 34 periods
        macd_values = []
        for i in range(len(prices) - 33, len(prices) + 1):
            ema_12_i = calc.calculate_ema(prices[:i], 12)
            ema_26_i = calc.calculate_ema(prices[:i], 26)
            if ema_12_i is not None and ema_26_i is not None:
                macd_values.append(ema_12_i - ema_26_i)
        
        # Signal should be EMA(9) of these MACD values
        if len(macd_values) >= 9:
            expected_signal = calc.calculate_ema(np.array(macd_values), 9)
            assert abs(signal_line - expected_signal) < 1e-9
    
    @settings(max_examples=20)
    @given(price_array_strategy(min_size=1, max_size=25))
    def test_property_macd_insufficient_data(self, prices: np.ndarray):
        """
        Property 8: MACD Calculation Correctness (Insufficient Data)
        **Validates: Requirements 4.3**
        
        Property: When insufficient data is available (< 26 prices),
        MACD should return None for all components.
        """
        calc = IndicatorCalculator()
        macd_line, signal_line, histogram = calc.calculate_macd(prices)
        
        assert macd_line is None
        assert signal_line is None
        assert histogram is None
    
    @settings(max_examples=20)
    @given(price_array_strategy(min_size=26, max_size=33))
    def test_property_macd_partial_data(self, prices: np.ndarray):
        """
        Property 8: MACD Calculation Correctness (Partial Data)
        **Validates: Requirements 4.3**
        
        Property: With 26-33 prices, MACD line can be calculated but signal
        line and histogram may not be available.
        """
        calc = IndicatorCalculator()
        macd_line, signal_line, histogram = calc.calculate_macd(prices)
        
        # MACD line should be available
        assert macd_line is not None
        
        # Signal line and histogram may or may not be available
        # depending on exact length
    
    @settings(max_examples=20)
    @given(price_array_strategy(min_size=34, max_size=250))
    def test_property_macd_histogram_sign_invariant(self, prices: np.ndarray):
        """
        Property 8: MACD Calculation Correctness (Histogram Sign)
        **Validates: Requirements 4.3**
        
        Property: Histogram should be positive when MACD > Signal,
        negative when MACD < Signal, and zero when equal.
        """
        calc = IndicatorCalculator()
        macd_line, signal_line, histogram = calc.calculate_macd(prices)
        
        assert macd_line is not None
        assert signal_line is not None
        assert histogram is not None
        
        if macd_line > signal_line:
            assert histogram > 0 or abs(histogram) < 1e-9
        elif macd_line < signal_line:
            assert histogram < 0 or abs(histogram) < 1e-9
        else:
            assert abs(histogram) < 1e-9


class TestAverageVolumeProperties:
    """Property-based tests for average volume calculation."""
    
    @settings(max_examples=20)
    @given(volume_array_strategy(min_size=20, max_size=250))
    def test_property_9_avg_volume_calculation_correctness(self, volumes: np.ndarray):
        """
        Property 9: Average Volume Calculation Correctness
        **Validates: Requirements 4.4**
        
        Property: For any volume sequence with sufficient data, the calculated
        20-day average volume SHALL equal the arithmetic mean of the last 20
        volume values.
        """
        calc = IndicatorCalculator()
        avg_volume = calc.calculate_avg_volume(volumes, 20)
        
        assert avg_volume is not None
        
        # Calculate expected average manually
        expected_avg = np.mean(volumes[-20:])
        
        # Should match within floating point tolerance
        assert abs(avg_volume - expected_avg) < 1e-6
    
    @settings(max_examples=20)
    @given(
        volume_array_strategy(min_size=50, max_size=250),
        st.integers(min_value=1, max_value=50)
    )
    def test_property_avg_volume_with_various_periods(self, volumes: np.ndarray, period: int):
        """
        Property 9: Average Volume Calculation Correctness (Extended)
        **Validates: Requirements 4.4**
        
        Property: For any valid period, average volume should equal the
        arithmetic mean of the last 'period' volumes.
        """
        assume(len(volumes) >= period)
        
        calc = IndicatorCalculator()
        avg_vol = calc.calculate_avg_volume(volumes, period)
        
        assert avg_vol is not None
        expected_avg = np.mean(volumes[-period:])
        assert abs(avg_vol - expected_avg) < 1e-6
    
    @settings(max_examples=20)
    @given(volume_array_strategy(min_size=1, max_size=19))
    def test_property_avg_volume_insufficient_data(self, volumes: np.ndarray):
        """
        Property 9: Average Volume Calculation Correctness (Insufficient Data)
        **Validates: Requirements 4.4**
        
        Property: When insufficient data is available (< 20 volumes),
        average volume should return None.
        """
        calc = IndicatorCalculator()
        avg_vol = calc.calculate_avg_volume(volumes, 20)
        
        assert avg_vol is None
    
    @settings(max_examples=20)
    @given(volume_array_strategy(min_size=20, max_size=250))
    def test_property_avg_volume_range_bounds(self, volumes: np.ndarray):
        """
        Property 9: Average Volume Calculation Correctness (Range Bounds)
        **Validates: Requirements 4.4**
        
        Property: Average volume should be within the range of the volumes
        used for calculation.
        """
        calc = IndicatorCalculator()
        avg_vol = calc.calculate_avg_volume(volumes, 20)
        
        assert avg_vol is not None
        
        min_vol = np.min(volumes[-20:])
        max_vol = np.max(volumes[-20:])
        
        # Average should be within min and max
        assert min_vol <= avg_vol <= max_vol


class TestRelativeStrengthProperties:
    """Property-based tests for relative strength calculation."""
    
    @settings(max_examples=20)
    @given(
        price_array_strategy(min_size=21, max_size=250, min_price=10.0, max_price=500.0),
        price_array_strategy(min_size=21, max_size=250, min_price=10.0, max_price=500.0)
    )
    def test_property_10_relative_strength_calculation_correctness(
        self, ticker_prices: np.ndarray, market_prices: np.ndarray
    ):
        """
        Property 10: Relative Strength Calculation Correctness
        **Validates: Requirements 4.5**
        
        Property: For any pair of ticker and market price sequences over a
        20-day period, the Relative Strength SHALL equal the ticker's percentage
        return minus the market's percentage return over that period.
        """
        # Ensure both arrays have the same length
        min_len = min(len(ticker_prices), len(market_prices))
        ticker_prices = ticker_prices[:min_len]
        market_prices = market_prices[:min_len]
        
        assume(min_len >= 21)
        assume(ticker_prices[-21] > 0)
        assume(market_prices[-21] > 0)
        
        calc = IndicatorCalculator()
        rs = calc.calculate_relative_strength(ticker_prices, market_prices, 20)
        
        assert rs is not None
        
        # Calculate expected RS manually
        ticker_start = ticker_prices[-21]
        ticker_end = ticker_prices[-1]
        ticker_return = ((ticker_end - ticker_start) / ticker_start) * 100
        
        market_start = market_prices[-21]
        market_end = market_prices[-1]
        market_return = ((market_end - market_start) / market_start) * 100
        
        expected_rs = ticker_return - market_return
        
        # Should match within floating point tolerance
        assert abs(rs - expected_rs) < 1e-9
    
    @settings(max_examples=20)
    @given(
        price_array_strategy(min_size=21, max_size=250, min_price=10.0, max_price=500.0),
        price_array_strategy(min_size=21, max_size=250, min_price=10.0, max_price=500.0),
        st.integers(min_value=5, max_value=20)
    )
    def test_property_rs_with_various_periods(
        self, ticker_prices: np.ndarray, market_prices: np.ndarray, period: int
    ):
        """
        Property 10: Relative Strength Calculation Correctness (Extended)
        **Validates: Requirements 4.5**
        
        Property: For any valid period, RS should equal the difference in
        percentage returns over that period.
        """
        min_len = min(len(ticker_prices), len(market_prices))
        ticker_prices = ticker_prices[:min_len]
        market_prices = market_prices[:min_len]
        
        assume(min_len >= period + 1)
        assume(ticker_prices[-(period + 1)] > 0)
        assume(market_prices[-(period + 1)] > 0)
        
        calc = IndicatorCalculator()
        rs = calc.calculate_relative_strength(ticker_prices, market_prices, period)
        
        assert rs is not None
        
        # Calculate manually
        ticker_return = ((ticker_prices[-1] - ticker_prices[-(period + 1)]) / 
                        ticker_prices[-(period + 1)]) * 100
        market_return = ((market_prices[-1] - market_prices[-(period + 1)]) / 
                        market_prices[-(period + 1)]) * 100
        expected_rs = ticker_return - market_return
        
        assert abs(rs - expected_rs) < 1e-9
    
    @settings(max_examples=20)
    @given(
        price_array_strategy(min_size=1, max_size=20, min_price=10.0, max_price=500.0),
        price_array_strategy(min_size=1, max_size=20, min_price=10.0, max_price=500.0)
    )
    def test_property_rs_insufficient_data(
        self, ticker_prices: np.ndarray, market_prices: np.ndarray
    ):
        """
        Property 10: Relative Strength Calculation Correctness (Insufficient Data)
        **Validates: Requirements 4.5**
        
        Property: When insufficient data is available (< 21 prices),
        RS should return None.
        """
        calc = IndicatorCalculator()
        rs = calc.calculate_relative_strength(ticker_prices, market_prices, 20)
        
        assert rs is None
    
    @settings(max_examples=20)
    @given(
        price_array_strategy(min_size=21, max_size=250, min_price=10.0, max_price=500.0),
        price_array_strategy(min_size=21, max_size=250, min_price=10.0, max_price=500.0)
    )
    def test_property_rs_positive_when_ticker_outperforms(
        self, ticker_prices: np.ndarray, market_prices: np.ndarray
    ):
        """
        Property 10: Relative Strength Calculation Correctness (Sign)
        **Validates: Requirements 4.5**
        
        Property: RS should be positive when ticker outperforms market,
        negative when underperforms, and zero when equal performance.
        """
        min_len = min(len(ticker_prices), len(market_prices))
        ticker_prices = ticker_prices[:min_len]
        market_prices = market_prices[:min_len]
        
        assume(min_len >= 21)
        assume(ticker_prices[-21] > 0)
        assume(market_prices[-21] > 0)
        
        calc = IndicatorCalculator()
        rs = calc.calculate_relative_strength(ticker_prices, market_prices, 20)
        
        assert rs is not None
        
        # Calculate returns
        ticker_return = ((ticker_prices[-1] - ticker_prices[-21]) / ticker_prices[-21]) * 100
        market_return = ((market_prices[-1] - market_prices[-21]) / market_prices[-21]) * 100
        
        if ticker_return > market_return:
            assert rs > 0 or abs(rs) < 1e-9
        elif ticker_return < market_return:
            assert rs < 0 or abs(rs) < 1e-9
        else:
            assert abs(rs) < 1e-9
    
    @settings(max_examples=20)
    @given(
        price_array_strategy(min_size=21, max_size=250, min_price=10.0, max_price=500.0)
    )
    def test_property_rs_zero_when_identical_performance(self, prices: np.ndarray):
        """
        Property 10: Relative Strength Calculation Correctness (Identity)
        **Validates: Requirements 4.5**
        
        Property: RS should be zero (or very close) when ticker and market
        have identical prices (same performance).
        """
        assume(prices[-21] > 0)
        
        calc = IndicatorCalculator()
        # Use same prices for both ticker and market
        rs = calc.calculate_relative_strength(prices, prices, 20)
        
        assert rs is not None
        # RS should be zero or very close to zero
        assert abs(rs) < 1e-9
