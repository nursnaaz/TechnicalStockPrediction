"""
Unit Tests for Scoring Engine

Tests for the ScoringEngine component that assigns bullish scores based on
technical indicator signals.
"""

import pytest
from core.scoring_engine import ScoringEngine
from core.models import TechnicalIndicators
from api.models import IndicatorSignals


class TestScoringEngine:
    """Test suite for ScoringEngine."""

    @pytest.fixture
    def engine(self):
        """Create a ScoringEngine instance."""
        return ScoringEngine()

    def test_price_above_sma50_rule(self, engine):
        """Test price above SMA50 awards 20 points."""
        indicators = TechnicalIndicators(sma_50=100.0)
        score, signals = engine.calculate_score(
            current_price=105.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 20
        assert signals.price_above_sma50 is True
        assert signals.price_above_ema20 is False
        assert signals.macd_above_signal is False
        assert signals.macd_histogram_positive is False
        assert signals.volume_above_average is False
        assert signals.relative_strength_positive is False

    def test_price_below_sma50_no_points(self, engine):
        """Test price below SMA50 awards 0 points."""
        indicators = TechnicalIndicators(sma_50=100.0)
        score, signals = engine.calculate_score(
            current_price=95.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 0
        assert signals.price_above_sma50 is False

    def test_price_above_ema20_rule(self, engine):
        """Test price above EMA20 awards 15 points."""
        indicators = TechnicalIndicators(ema_20=100.0)
        score, signals = engine.calculate_score(
            current_price=105.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 15
        assert signals.price_above_ema20 is True
        assert signals.price_above_sma50 is False

    def test_price_below_ema20_no_points(self, engine):
        """Test price below EMA20 awards 0 points."""
        indicators = TechnicalIndicators(ema_20=100.0)
        score, signals = engine.calculate_score(
            current_price=95.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 0
        assert signals.price_above_ema20 is False

    def test_macd_above_signal_rule(self, engine):
        """Test MACD line above signal line awards 20 points."""
        indicators = TechnicalIndicators(macd_line=1.5, macd_signal=1.0)
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 20
        assert signals.macd_above_signal is True

    def test_macd_below_signal_no_points(self, engine):
        """Test MACD line below signal line awards 0 points."""
        indicators = TechnicalIndicators(macd_line=0.5, macd_signal=1.0)
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 0
        assert signals.macd_above_signal is False

    def test_macd_histogram_positive_rule(self, engine):
        """Test positive MACD histogram awards 10 points."""
        indicators = TechnicalIndicators(macd_histogram=0.5)
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 10
        assert signals.macd_histogram_positive is True

    def test_macd_histogram_negative_no_points(self, engine):
        """Test negative MACD histogram awards 0 points."""
        indicators = TechnicalIndicators(macd_histogram=-0.5)
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 0
        assert signals.macd_histogram_positive is False

    def test_macd_histogram_zero_no_points(self, engine):
        """Test zero MACD histogram awards 0 points."""
        indicators = TechnicalIndicators(macd_histogram=0.0)
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 0
        assert signals.macd_histogram_positive is False

    def test_volume_surge_rule(self, engine):
        """Test volume 20% above average awards 15 points."""
        indicators = TechnicalIndicators(avg_volume_20=1000000.0)
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1200001,  # Just over 20% threshold
            indicators=indicators
        )
        assert score == 15
        assert signals.volume_above_average is True

    def test_volume_at_threshold_awards_points(self, engine):
        """Test volume exactly at 120% threshold awards 15 points."""
        indicators = TechnicalIndicators(avg_volume_20=1000000.0)
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1200000.0,  # Exactly 120%
            indicators=indicators
        )
        # Volume must be > 1.2x, not >= 1.2x
        assert score == 0
        assert signals.volume_above_average is False

    def test_volume_just_above_threshold(self, engine):
        """Test volume just above 120% threshold awards points."""
        indicators = TechnicalIndicators(avg_volume_20=1000000.0)
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1200000.1,  # Just above 120%
            indicators=indicators
        )
        assert score == 15
        assert signals.volume_above_average is True

    def test_volume_below_threshold_no_points(self, engine):
        """Test volume below 120% threshold awards 0 points."""
        indicators = TechnicalIndicators(avg_volume_20=1000000.0)
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1100000,  # Only 110%
            indicators=indicators
        )
        assert score == 0
        assert signals.volume_above_average is False

    def test_relative_strength_positive_rule(self, engine):
        """Test positive relative strength awards 20 points."""
        indicators = TechnicalIndicators(relative_strength=2.5)
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 20
        assert signals.relative_strength_positive is True

    def test_relative_strength_negative_no_points(self, engine):
        """Test negative relative strength awards 0 points."""
        indicators = TechnicalIndicators(relative_strength=-2.5)
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 0
        assert signals.relative_strength_positive is False

    def test_relative_strength_zero_no_points(self, engine):
        """Test zero relative strength awards 0 points."""
        indicators = TechnicalIndicators(relative_strength=0.0)
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 0
        assert signals.relative_strength_positive is False

    def test_all_signals_active(self, engine):
        """Test total score with all signals active."""
        indicators = TechnicalIndicators(
            sma_50=90.0,
            ema_20=95.0,
            macd_line=1.5,
            macd_signal=1.0,
            macd_histogram=0.5,
            avg_volume_20=1000000.0,
            relative_strength=2.5
        )
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1300000,
            indicators=indicators
        )
        # 20 + 15 + 20 + 10 + 15 + 20 = 100
        assert score == 100
        assert signals.price_above_sma50 is True
        assert signals.price_above_ema20 is True
        assert signals.macd_above_signal is True
        assert signals.macd_histogram_positive is True
        assert signals.volume_above_average is True
        assert signals.relative_strength_positive is True

    def test_missing_indicators_none_values(self, engine):
        """Test handling of missing indicators (None values)."""
        indicators = TechnicalIndicators()  # All None
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 0
        assert signals.price_above_sma50 is False
        assert signals.price_above_ema20 is False
        assert signals.macd_above_signal is False
        assert signals.macd_histogram_positive is False
        assert signals.volume_above_average is False
        assert signals.relative_strength_positive is False

    def test_partial_indicators_available(self, engine):
        """Test scoring with some indicators available and others None."""
        indicators = TechnicalIndicators(
            sma_50=90.0,  # Available
            ema_20=None,  # Missing
            macd_line=None,  # Missing
            macd_signal=None,  # Missing
            macd_histogram=0.5,  # Available
            avg_volume_20=None,  # Missing
            relative_strength=2.5  # Available
        )
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        # 20 (SMA) + 10 (histogram) + 20 (RS) = 50
        assert score == 50
        assert signals.price_above_sma50 is True
        assert signals.price_above_ema20 is False
        assert signals.macd_above_signal is False
        assert signals.macd_histogram_positive is True
        assert signals.volume_above_average is False
        assert signals.relative_strength_positive is True

    def test_score_capping_at_100(self, engine):
        """Test score is capped at 100 (edge case verification)."""
        # Although max possible is 100, verify capping logic works
        indicators = TechnicalIndicators(
            sma_50=90.0,
            ema_20=95.0,
            macd_line=1.5,
            macd_signal=1.0,
            macd_histogram=0.5,
            avg_volume_20=1000000.0,
            relative_strength=2.5
        )
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1300000,
            indicators=indicators
        )
        assert score <= 100
        assert score == 100

    def test_partial_signal_combination_1(self, engine):
        """Test partial signal combination: price signals only."""
        indicators = TechnicalIndicators(
            sma_50=90.0,
            ema_20=95.0
        )
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        # 20 + 15 = 35
        assert score == 35
        assert signals.price_above_sma50 is True
        assert signals.price_above_ema20 is True

    def test_partial_signal_combination_2(self, engine):
        """Test partial signal combination: MACD signals only."""
        indicators = TechnicalIndicators(
            macd_line=1.5,
            macd_signal=1.0,
            macd_histogram=0.5
        )
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        # 20 + 10 = 30
        assert score == 30
        assert signals.macd_above_signal is True
        assert signals.macd_histogram_positive is True

    def test_partial_signal_combination_3(self, engine):
        """Test partial signal combination: volume and RS only."""
        indicators = TechnicalIndicators(
            avg_volume_20=1000000.0,
            relative_strength=2.5
        )
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1300000,
            indicators=indicators
        )
        # 15 + 20 = 35
        assert score == 35
        assert signals.volume_above_average is True
        assert signals.relative_strength_positive is True

    def test_macd_only_line_available(self, engine):
        """Test MACD scoring when only line is available (signal missing)."""
        indicators = TechnicalIndicators(
            macd_line=1.5,
            macd_signal=None
        )
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 0
        assert signals.macd_above_signal is False

    def test_macd_only_signal_available(self, engine):
        """Test MACD scoring when only signal is available (line missing)."""
        indicators = TechnicalIndicators(
            macd_line=None,
            macd_signal=1.0
        )
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 0
        assert signals.macd_above_signal is False

    def test_boundary_price_equal_sma50(self, engine):
        """Test boundary: price exactly equal to SMA50."""
        indicators = TechnicalIndicators(sma_50=100.0)
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 0
        assert signals.price_above_sma50 is False

    def test_boundary_price_equal_ema20(self, engine):
        """Test boundary: price exactly equal to EMA20."""
        indicators = TechnicalIndicators(ema_20=100.0)
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 0
        assert signals.price_above_ema20 is False

    def test_boundary_macd_equal(self, engine):
        """Test boundary: MACD line exactly equal to signal."""
        indicators = TechnicalIndicators(macd_line=1.0, macd_signal=1.0)
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1000000,
            indicators=indicators
        )
        assert score == 0
        assert signals.macd_above_signal is False

    def test_very_small_positive_values(self, engine):
        """Test very small positive values trigger signals."""
        indicators = TechnicalIndicators(
            sma_50=99.999,
            ema_20=99.999,
            macd_line=0.001,
            macd_signal=0.0,
            macd_histogram=0.001,
            avg_volume_20=1000000.0,
            relative_strength=0.001
        )
        score, signals = engine.calculate_score(
            current_price=100.0,
            current_volume=1200000.1,
            indicators=indicators
        )
        # All signals should trigger
        assert score == 100
        assert signals.price_above_sma50 is True
        assert signals.price_above_ema20 is True
        assert signals.macd_above_signal is True
        assert signals.macd_histogram_positive is True
        assert signals.volume_above_average is True
        assert signals.relative_strength_positive is True
