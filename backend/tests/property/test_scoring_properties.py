"""
Property-Based Tests for Scoring Engine

Tests mathematical properties and invariants for bullish score calculations.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from core.scoring_engine import ScoringEngine
from core.models import TechnicalIndicators


# Custom strategies for realistic test data
def price_strategy(min_price=1.0, max_price=1000.0):
    """Generate realistic price values."""
    return st.floats(
        min_value=min_price,
        max_value=max_price,
        allow_nan=False,
        allow_infinity=False
    )


def volume_strategy(min_volume=1000, max_volume=1000000000):
    """Generate realistic volume values."""
    return st.integers(min_value=min_volume, max_value=max_volume)


def indicator_value_strategy():
    """Generate realistic indicator values (can be negative or positive)."""
    return st.floats(
        min_value=-1000.0,
        max_value=1000.0,
        allow_nan=False,
        allow_infinity=False
    )


def optional_indicator_strategy():
    """Generate optional indicator values (None or float)."""
    return st.one_of(st.none(), indicator_value_strategy())


class TestPriceAboveSMAScoring:
    """Property-based tests for Price Above SMA(50) scoring rule."""

    @settings(max_examples=20)
    @given(
        current_price=price_strategy(),
        sma_50=price_strategy()
    )
    def test_property_11_price_above_sma_scoring(
        self, current_price: float, sma_50: float
    ):
        """
        Property 11: Price Above SMA Scoring
        **Validates: Requirements 5.2**

        Property: When the current price is above the 50-day SMA, the scoring
        engine SHALL add exactly 20 points to the bullish score. When the
        current price is at or below the 50-day SMA, no points SHALL be added.
        """
        engine = ScoringEngine()
        
        # Create indicators with only SMA populated
        indicators = TechnicalIndicators(sma_50=sma_50)
        
        score, signals = engine.calculate_score(
            current_price=current_price,
            current_volume=1000000.0,
            indicators=indicators
        )
        
        # Verify signal flag
        assert signals.price_above_sma50 == (current_price > sma_50)
        
        # Verify score contribution
        if current_price > sma_50:
            assert score == 20
        else:
            assert score == 0

    @settings(max_examples=20)
    @given(
        current_price=price_strategy(),
        current_volume=volume_strategy()
    )
    def test_property_11_sma_none_no_points(
        self, current_price: float, current_volume: float
    ):
        """
        Property 11: Price Above SMA Scoring (Missing Indicator)
        **Validates: Requirements 5.2**

        Property: When SMA(50) is None (unavailable), the signal SHALL be
        False and no points SHALL be added regardless of current price.
        """
        engine = ScoringEngine()
        
        # Create indicators with SMA as None
        indicators = TechnicalIndicators(sma_50=None)
        
        score, signals = engine.calculate_score(
            current_price=current_price,
            current_volume=current_volume,
            indicators=indicators
        )
        
        # Signal should be False when indicator is missing
        assert signals.price_above_sma50 is False
        # Score should be 0 with no indicators
        assert score == 0


class TestPriceAboveEMAScoring:
    """Property-based tests for Price Above EMA(20) scoring rule."""

    @settings(max_examples=20)
    @given(
        current_price=price_strategy(),
        ema_20=price_strategy()
    )
    def test_property_12_price_above_ema_scoring(
        self, current_price: float, ema_20: float
    ):
        """
        Property 12: Price Above EMA Scoring
        **Validates: Requirements 5.3**

        Property: When the current price is above the 20-day EMA, the scoring
        engine SHALL add exactly 15 points to the bullish score. When the
        current price is at or below the 20-day EMA, no points SHALL be added.
        """
        engine = ScoringEngine()
        
        # Create indicators with only EMA populated
        indicators = TechnicalIndicators(ema_20=ema_20)
        
        score, signals = engine.calculate_score(
            current_price=current_price,
            current_volume=1000000.0,
            indicators=indicators
        )
        
        # Verify signal flag
        assert signals.price_above_ema20 == (current_price > ema_20)
        
        # Verify score contribution
        if current_price > ema_20:
            assert score == 15
        else:
            assert score == 0

    @settings(max_examples=20)
    @given(
        current_price=price_strategy(),
        current_volume=volume_strategy()
    )
    def test_property_12_ema_none_no_points(
        self, current_price: float, current_volume: float
    ):
        """
        Property 12: Price Above EMA Scoring (Missing Indicator)
        **Validates: Requirements 5.3**

        Property: When EMA(20) is None (unavailable), the signal SHALL be
        False and no points SHALL be added regardless of current price.
        """
        engine = ScoringEngine()
        
        # Create indicators with EMA as None
        indicators = TechnicalIndicators(ema_20=None)
        
        score, signals = engine.calculate_score(
            current_price=current_price,
            current_volume=current_volume,
            indicators=indicators
        )
        
        # Signal should be False when indicator is missing
        assert signals.price_above_ema20 is False
        # Score should be 0 with no indicators
        assert score == 0


class TestMACDAboveSignalScoring:
    """Property-based tests for MACD Above Signal scoring rule."""

    @settings(max_examples=20)
    @given(
        macd_line=indicator_value_strategy(),
        macd_signal=indicator_value_strategy()
    )
    def test_property_13_macd_above_signal_scoring(
        self, macd_line: float, macd_signal: float
    ):
        """
        Property 13: MACD Above Signal Scoring
        **Validates: Requirements 5.4**

        Property: When the MACD line is above the signal line, the scoring
        engine SHALL add exactly 20 points to the bullish score. When the
        MACD line is at or below the signal line, no points SHALL be added.
        """
        engine = ScoringEngine()
        
        # Create indicators with MACD values populated
        indicators = TechnicalIndicators(
            macd_line=macd_line,
            macd_signal=macd_signal
        )
        
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000.0,
            indicators=indicators
        )
        
        # Verify signal flag
        assert signals.macd_above_signal == (macd_line > macd_signal)
        
        # Verify score contribution
        if macd_line > macd_signal:
            assert score == 20
        else:
            assert score == 0

    @settings(max_examples=20)
    @given(
        macd_line=st.one_of(st.none(), indicator_value_strategy()),
        macd_signal=st.one_of(st.none(), indicator_value_strategy())
    )
    def test_property_13_macd_none_no_points(
        self, macd_line: float, macd_signal: float
    ):
        """
        Property 13: MACD Above Signal Scoring (Missing Indicators)
        **Validates: Requirements 5.4**

        Property: When either MACD line or signal line is None (unavailable),
        the signal SHALL be False and no points SHALL be added.
        """
        # Skip if both are available (tested in main property test)
        assume(macd_line is None or macd_signal is None)
        
        engine = ScoringEngine()
        
        # Create indicators with at least one MACD value as None
        indicators = TechnicalIndicators(
            macd_line=macd_line,
            macd_signal=macd_signal
        )
        
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000.0,
            indicators=indicators
        )
        
        # Signal should be False when either indicator is missing
        assert signals.macd_above_signal is False
        # Score should be 0 with no other indicators
        assert score == 0


class TestMACDHistogramPositiveScoring:
    """Property-based tests for MACD Histogram Positive scoring rule."""

    @settings(max_examples=20)
    @given(macd_histogram=indicator_value_strategy())
    def test_property_14_macd_histogram_positive_scoring(
        self, macd_histogram: float
    ):
        """
        Property 14: MACD Histogram Positive Scoring
        **Validates: Requirements 5.5**

        Property: When the MACD histogram is positive (> 0), the scoring
        engine SHALL add exactly 10 points to the bullish score. When the
        MACD histogram is zero or negative, no points SHALL be added.
        """
        engine = ScoringEngine()
        
        # Create indicators with histogram populated
        indicators = TechnicalIndicators(macd_histogram=macd_histogram)
        
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000.0,
            indicators=indicators
        )
        
        # Verify signal flag
        assert signals.macd_histogram_positive == (macd_histogram > 0)
        
        # Verify score contribution
        if macd_histogram > 0:
            assert score == 10
        else:
            assert score == 0

    @settings(max_examples=20)
    @given(
        current_price=price_strategy(),
        current_volume=volume_strategy()
    )
    def test_property_14_histogram_none_no_points(
        self, current_price: float, current_volume: float
    ):
        """
        Property 14: MACD Histogram Positive Scoring (Missing Indicator)
        **Validates: Requirements 5.5**

        Property: When MACD histogram is None (unavailable), the signal SHALL
        be False and no points SHALL be added.
        """
        engine = ScoringEngine()
        
        # Create indicators with histogram as None
        indicators = TechnicalIndicators(macd_histogram=None)
        
        score, signals = engine.calculate_score(
            current_price=current_price,
            current_volume=current_volume,
            indicators=indicators
        )
        
        # Signal should be False when indicator is missing
        assert signals.macd_histogram_positive is False
        # Score should be 0 with no indicators
        assert score == 0


class TestVolumeSurgeScoring:
    """Property-based tests for Volume Surge scoring rule."""

    @settings(max_examples=20)
    @given(
        current_volume=volume_strategy(),
        avg_volume_20=volume_strategy()
    )
    def test_property_15_volume_surge_scoring(
        self, current_volume: float, avg_volume_20: float
    ):
        """
        Property 15: Volume Surge Scoring
        **Validates: Requirements 5.6**

        Property: When the current volume exceeds the 20-day average volume
        by at least 20% (current_volume > avg_volume * 1.2), the scoring
        engine SHALL add exactly 15 points to the bullish score. Otherwise,
        no points SHALL be added.
        """
        assume(avg_volume_20 > 0)  # Avoid division by zero edge cases
        
        engine = ScoringEngine()
        
        # Create indicators with average volume populated
        indicators = TechnicalIndicators(avg_volume_20=float(avg_volume_20))
        
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=float(current_volume),
            indicators=indicators
        )
        
        # Verify signal flag
        expected_signal = current_volume > (avg_volume_20 * 1.2)
        assert signals.volume_above_average == expected_signal
        
        # Verify score contribution
        if current_volume > (avg_volume_20 * 1.2):
            assert score == 15
        else:
            assert score == 0

    @settings(max_examples=20)
    @given(current_volume=volume_strategy())
    def test_property_15_avg_volume_none_no_points(self, current_volume: float):
        """
        Property 15: Volume Surge Scoring (Missing Indicator)
        **Validates: Requirements 5.6**

        Property: When average volume is None (unavailable), the signal SHALL
        be False and no points SHALL be added regardless of current volume.
        """
        engine = ScoringEngine()
        
        # Create indicators with average volume as None
        indicators = TechnicalIndicators(avg_volume_20=None)
        
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=current_volume,
            indicators=indicators
        )
        
        # Signal should be False when indicator is missing
        assert signals.volume_above_average is False
        # Score should be 0 with no indicators
        assert score == 0


class TestRelativeStrengthPositiveScoring:
    """Property-based tests for Relative Strength Positive scoring rule."""

    @settings(max_examples=20)
    @given(relative_strength=indicator_value_strategy())
    def test_property_16_relative_strength_positive_scoring(
        self, relative_strength: float
    ):
        """
        Property 16: Relative Strength Positive Scoring
        **Validates: Requirements 5.7**

        Property: When the relative strength is positive (> 0), indicating
        the ticker is outperforming the market, the scoring engine SHALL add
        exactly 20 points to the bullish score. When relative strength is
        zero or negative, no points SHALL be added.
        """
        engine = ScoringEngine()
        
        # Create indicators with relative strength populated
        indicators = TechnicalIndicators(relative_strength=relative_strength)
        
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000.0,
            indicators=indicators
        )
        
        # Verify signal flag
        assert signals.relative_strength_positive == (relative_strength > 0)
        
        # Verify score contribution
        if relative_strength > 0:
            assert score == 20
        else:
            assert score == 0

    @settings(max_examples=20)
    @given(
        current_price=price_strategy(),
        current_volume=volume_strategy()
    )
    def test_property_16_relative_strength_none_no_points(
        self, current_price: float, current_volume: float
    ):
        """
        Property 16: Relative Strength Positive Scoring (Missing Indicator)
        **Validates: Requirements 5.7**

        Property: When relative strength is None (unavailable), the signal
        SHALL be False and no points SHALL be added.
        """
        engine = ScoringEngine()
        
        # Create indicators with relative strength as None
        indicators = TechnicalIndicators(relative_strength=None)
        
        score, signals = engine.calculate_score(
            current_price=current_price,
            current_volume=current_volume,
            indicators=indicators
        )
        
        # Signal should be False when indicator is missing
        assert signals.relative_strength_positive is False
        # Score should be 0 with no indicators
        assert score == 0


class TestScoreAggregationAndCapping:
    """Property-based tests for score aggregation and capping."""

    @settings(max_examples=20)
    @given(
        current_price=price_strategy(min_price=50.0, max_price=500.0),
        current_volume=volume_strategy(min_volume=100000, max_volume=10000000),
        sma_50=price_strategy(min_price=10.0, max_price=400.0),
        ema_20=price_strategy(min_price=10.0, max_price=400.0),
        macd_line=indicator_value_strategy(),
        macd_signal=indicator_value_strategy(),
        macd_histogram=indicator_value_strategy(),
        avg_volume_20=volume_strategy(min_volume=50000, max_volume=8000000),
        relative_strength=indicator_value_strategy()
    )
    def test_property_17_score_aggregation_and_capping(
        self,
        current_price: float,
        current_volume: float,
        sma_50: float,
        ema_20: float,
        macd_line: float,
        macd_signal: float,
        macd_histogram: float,
        avg_volume_20: float,
        relative_strength: float
    ):
        """
        Property 17: Score Aggregation and Capping
        **Validates: Requirements 5.8**

        Property: The total bullish score SHALL be the sum of all earned
        points from individual indicator signals, and the final score SHALL
        be capped at a maximum of 100 points.
        """
        assume(avg_volume_20 > 0)
        
        engine = ScoringEngine()
        
        # Create indicators with all values populated
        indicators = TechnicalIndicators(
            sma_50=sma_50,
            ema_20=ema_20,
            macd_line=macd_line,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            avg_volume_20=float(avg_volume_20),
            relative_strength=relative_strength
        )
        
        score, signals = engine.calculate_score(
            current_price=current_price,
            current_volume=float(current_volume),
            indicators=indicators
        )
        
        # Calculate expected score manually
        expected_score = 0
        
        if current_price > sma_50:
            expected_score += 20
        
        if current_price > ema_20:
            expected_score += 15
        
        if macd_line > macd_signal:
            expected_score += 20
        
        if macd_histogram > 0:
            expected_score += 10
        
        if current_volume > (avg_volume_20 * 1.2):
            expected_score += 15
        
        if relative_strength > 0:
            expected_score += 20
        
        # Cap at 100 (though max possible is 100)
        expected_score = min(expected_score, 100)
        
        # Verify score matches expected
        assert score == expected_score
        
        # Verify score is within valid range
        assert 0 <= score <= 100

    @settings(max_examples=20)
    @given(
        current_price=price_strategy(),
        current_volume=volume_strategy()
    )
    def test_property_17_all_indicators_none(
        self, current_price: float, current_volume: float
    ):
        """
        Property 17: Score Aggregation and Capping (All Indicators Missing)
        **Validates: Requirements 5.8**

        Property: When all indicators are None (unavailable), the total score
        SHALL be 0 and all signals SHALL be False.
        """
        engine = ScoringEngine()
        
        # Create indicators with all values as None
        indicators = TechnicalIndicators()
        
        score, signals = engine.calculate_score(
            current_price=current_price,
            current_volume=current_volume,
            indicators=indicators
        )
        
        # Score should be 0 with no indicators
        assert score == 0
        
        # All signals should be False
        assert signals.price_above_sma50 is False
        assert signals.price_above_ema20 is False
        assert signals.macd_above_signal is False
        assert signals.macd_histogram_positive is False
        assert signals.volume_above_average is False
        assert signals.relative_strength_positive is False

    @settings(max_examples=20)
    @given(
        current_price=price_strategy(min_price=50.0, max_price=500.0),
        current_volume=volume_strategy(min_volume=100000, max_volume=10000000),
        sma_50=st.one_of(st.none(), price_strategy(min_price=10.0, max_price=400.0)),
        ema_20=st.one_of(st.none(), price_strategy(min_price=10.0, max_price=400.0)),
        macd_line=optional_indicator_strategy(),
        macd_signal=optional_indicator_strategy(),
        macd_histogram=optional_indicator_strategy(),
        avg_volume_20=st.one_of(st.none(), volume_strategy(min_volume=50000, max_volume=8000000)),
        relative_strength=optional_indicator_strategy()
    )
    def test_property_17_partial_indicators(
        self,
        current_price: float,
        current_volume: float,
        sma_50: float,
        ema_20: float,
        macd_line: float,
        macd_signal: float,
        macd_histogram: float,
        avg_volume_20: float,
        relative_strength: float
    ):
        """
        Property 17: Score Aggregation and Capping (Partial Indicators)
        **Validates: Requirements 5.8**

        Property: When some indicators are available and others are None,
        the scoring engine SHALL calculate the score using only available
        indicators and ignore missing ones (contributing 0 points).
        """
        # Skip if avg_volume is 0 (edge case)
        assume(avg_volume_20 is None or avg_volume_20 > 0)
        
        engine = ScoringEngine()
        
        # Create indicators with mixed None and actual values
        indicators = TechnicalIndicators(
            sma_50=sma_50,
            ema_20=ema_20,
            macd_line=macd_line,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            avg_volume_20=float(avg_volume_20) if avg_volume_20 is not None else None,
            relative_strength=relative_strength
        )
        
        score, signals = engine.calculate_score(
            current_price=current_price,
            current_volume=float(current_volume),
            indicators=indicators
        )
        
        # Calculate expected score manually
        expected_score = 0
        
        if sma_50 is not None and current_price > sma_50:
            expected_score += 20
        
        if ema_20 is not None and current_price > ema_20:
            expected_score += 15
        
        if macd_line is not None and macd_signal is not None and macd_line > macd_signal:
            expected_score += 20
        
        if macd_histogram is not None and macd_histogram > 0:
            expected_score += 10
        
        if avg_volume_20 is not None and current_volume > (avg_volume_20 * 1.2):
            expected_score += 15
        
        if relative_strength is not None and relative_strength > 0:
            expected_score += 20
        
        # Cap at 100
        expected_score = min(expected_score, 100)
        
        # Verify score matches expected
        assert score == expected_score
        
        # Verify score is within valid range
        assert 0 <= score <= 100

    @settings(max_examples=20)
    @given(
        current_price=price_strategy(min_price=200.0, max_price=500.0),
        current_volume=volume_strategy(min_volume=200000, max_volume=10000000)
    )
    def test_property_17_maximum_score_achievable(
        self, current_price: float, current_volume: float
    ):
        """
        Property 17: Score Aggregation and Capping (Maximum Score)
        **Validates: Requirements 5.8**

        Property: When all bullish conditions are met, the maximum achievable
        score SHALL be 100 points (20+15+20+10+15+20 = 100).
        """
        engine = ScoringEngine()
        
        # Create perfect bullish scenario
        indicators = TechnicalIndicators(
            sma_50=current_price - 10.0,  # Price above SMA
            ema_20=current_price - 10.0,  # Price above EMA
            macd_line=5.0,  # MACD above signal
            macd_signal=2.0,
            macd_histogram=3.0,  # Histogram positive
            avg_volume_20=float(current_volume / 1.5),  # Volume surge (>1.2x)
            relative_strength=10.0  # RS positive
        )
        
        score, signals = engine.calculate_score(
            current_price=current_price,
            current_volume=float(current_volume),
            indicators=indicators
        )
        
        # All signals should be True
        assert signals.price_above_sma50 is True
        assert signals.price_above_ema20 is True
        assert signals.macd_above_signal is True
        assert signals.macd_histogram_positive is True
        assert signals.volume_above_average is True
        assert signals.relative_strength_positive is True
        
        # Score should be exactly 100
        assert score == 100

    @settings(max_examples=20)
    @given(
        current_price=price_strategy(min_price=50.0, max_price=100.0),
        current_volume=volume_strategy(min_volume=10000, max_volume=50000)
    )
    def test_property_17_minimum_score_when_bearish(
        self, current_price: float, current_volume: float
    ):
        """
        Property 17: Score Aggregation and Capping (Minimum Score)
        **Validates: Requirements 5.8**

        Property: When all bearish conditions are met (or neutral), the
        minimum score SHALL be 0 points.
        """
        engine = ScoringEngine()
        
        # Create bearish scenario
        indicators = TechnicalIndicators(
            sma_50=current_price + 10.0,  # Price below SMA
            ema_20=current_price + 10.0,  # Price below EMA
            macd_line=-5.0,  # MACD below signal
            macd_signal=-2.0,
            macd_histogram=-3.0,  # Histogram negative
            avg_volume_20=float(current_volume * 2.0),  # Low volume
            relative_strength=-10.0  # RS negative
        )
        
        score, signals = engine.calculate_score(
            current_price=current_price,
            current_volume=float(current_volume),
            indicators=indicators
        )
        
        # All signals should be False
        assert signals.price_above_sma50 is False
        assert signals.price_above_ema20 is False
        assert signals.macd_above_signal is False
        assert signals.macd_histogram_positive is False
        assert signals.volume_above_average is False
        assert signals.relative_strength_positive is False
        
        # Score should be exactly 0
        assert score == 0
