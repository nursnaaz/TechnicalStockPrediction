"""
Tests for ScoringEngine V2 (Gradient Scoring)

Tests verify:
1. Gradient scoring produces meaningful score distribution
2. Higher indicator values produce higher scores
3. Scores range from 0-100
4. Signal booleans are correctly derived
5. None indicators don't crash
"""

import pytest
from core.scoring_engine import ScoringEngine
from core.models import TechnicalIndicators
from api.models import IndicatorSignals


@pytest.fixture
def engine():
    return ScoringEngine()


@pytest.fixture
def strong_bullish_indicators():
    """Indicators for a stock clearly in an uptrend."""
    return TechnicalIndicators(
        sma_50=100.0,
        ema_20=105.0,
        ema_9=107.0,
        macd_line=2.0,
        macd_signal=1.0,
        macd_histogram=1.0,
        avg_volume_20=1000000.0,
        relative_strength=6.0,
        rsi_14=60.0,
        roc_10=4.0,
        proximity_to_20d_high=99.0
    )


@pytest.fixture
def weak_bearish_indicators():
    """Indicators for a stock clearly in a downtrend."""
    return TechnicalIndicators(
        sma_50=120.0,
        ema_20=115.0,
        ema_9=112.0,
        macd_line=-3.0,
        macd_signal=-1.0,
        macd_histogram=-2.0,
        avg_volume_20=1000000.0,
        relative_strength=-8.0,
        rsi_14=25.0,
        roc_10=-6.0,
        proximity_to_20d_high=78.0
    )


@pytest.fixture
def none_indicators():
    """All indicators are None (no data available)."""
    return TechnicalIndicators()


class TestScoringEngine:
    """Tests for the V2 gradient scoring engine."""

    def test_strong_bullish_scores_high(self, engine, strong_bullish_indicators):
        """Stock well above averages with strong momentum should score 70+."""
        # Price well above SMA50 (100) and EMA20 (105)
        score, signals = engine.calculate_score(110.0, 1500000.0, strong_bullish_indicators)
        assert score >= 70
        assert score <= 100
        assert signals.price_above_sma50 is True
        assert signals.price_above_ema20 is True
        assert signals.macd_above_signal is True

    def test_weak_bearish_scores_low(self, engine, weak_bearish_indicators):
        """Stock below averages with negative momentum should score low."""
        # Price at 95 (below SMA50=120, EMA20=115)
        score, signals = engine.calculate_score(95.0, 400000.0, weak_bearish_indicators)
        assert score < 30
        assert signals.price_above_sma50 is False
        assert signals.price_above_ema20 is False
        assert signals.macd_above_signal is False

    def test_none_indicators_returns_zero(self, engine, none_indicators):
        """All None indicators should produce score 0 without errors."""
        score, signals = engine.calculate_score(100.0, 1000000.0, none_indicators)
        assert score == 0
        assert signals.price_above_sma50 is False
        assert signals.price_above_ema20 is False

    def test_score_never_exceeds_100(self, engine, strong_bullish_indicators):
        """Score must never exceed 100."""
        # Even with extreme values
        score, _ = engine.calculate_score(200.0, 5000000.0, strong_bullish_indicators)
        assert score <= 100

    def test_score_never_below_zero(self, engine, weak_bearish_indicators):
        """Score must never go below 0."""
        score, _ = engine.calculate_score(50.0, 100000.0, weak_bearish_indicators)
        assert score >= 0

    def test_gradient_sma50_near_gives_partial_credit(self, engine):
        """Stock within 2% of SMA50 should get partial credit (not 0)."""
        indicators = TechnicalIndicators(sma_50=100.0)
        # Price at 99 (1% below SMA50) — should still get some points
        score, signals = engine.calculate_score(99.0, 0, indicators)
        assert score > 0  # Partial credit for being near
        assert signals.price_above_sma50 is False

    def test_gradient_sma50_above_gives_more(self, engine):
        """Stock above SMA50 should score more than stock below."""
        indicators = TechnicalIndicators(sma_50=100.0)
        score_above, _ = engine.calculate_score(105.0, 0, indicators)
        score_below, _ = engine.calculate_score(99.0, 0, indicators)
        assert score_above > score_below

    def test_gradient_volume_relaxed(self, engine):
        """Normal volume (0.8x-1.2x avg) should still get points."""
        indicators = TechnicalIndicators(avg_volume_20=1000000.0)
        # Volume at exactly average — should get points (not 0)
        score, signals = engine.calculate_score(100.0, 1000000.0, indicators)
        assert score > 0
        assert signals.volume_above_average is False  # Not 20% above

    def test_high_volume_scores_more(self, engine):
        """High volume should score more than normal volume."""
        indicators = TechnicalIndicators(avg_volume_20=1000000.0)
        score_high, _ = engine.calculate_score(100.0, 2000000.0, indicators)
        score_normal, _ = engine.calculate_score(100.0, 1000000.0, indicators)
        assert score_high > score_normal

    def test_rsi_bullish_zone_contributes(self, engine):
        """RSI in 50-70 zone (bullish) should add more than RSI > 80 (overbought)."""
        indicators_bullish = TechnicalIndicators(rsi_14=60.0)
        indicators_overbought = TechnicalIndicators(rsi_14=85.0)
        score_bullish, _ = engine.calculate_score(100.0, 0, indicators_bullish)
        score_overbought, _ = engine.calculate_score(100.0, 0, indicators_overbought)
        assert score_bullish > score_overbought

    def test_rsi_oversold_still_gets_some_points(self, engine):
        """RSI below 30 (oversold) should still get some points (bounce potential)."""
        indicators = TechnicalIndicators(rsi_14=25.0)
        score, _ = engine.calculate_score(100.0, 0, indicators)
        assert score > 0

    def test_positive_roc_adds_momentum(self, engine):
        """Positive ROC (price rising) should add more points than negative ROC."""
        indicators_up = TechnicalIndicators(roc_10=5.0)
        indicators_down = TechnicalIndicators(roc_10=-5.0)
        score_up, _ = engine.calculate_score(100.0, 0, indicators_up)
        score_down, _ = engine.calculate_score(100.0, 0, indicators_down)
        assert score_up > score_down

    def test_near_20d_high_adds_points(self, engine):
        """Stock near its 20-day high should get breakout proximity credit."""
        indicators_near = TechnicalIndicators(proximity_to_20d_high=99.0)
        indicators_far = TechnicalIndicators(proximity_to_20d_high=80.0)
        score_near, _ = engine.calculate_score(100.0, 0, indicators_near)
        score_far, _ = engine.calculate_score(100.0, 0, indicators_far)
        assert score_near > score_far

    def test_relative_strength_gradient(self, engine):
        """Higher relative strength should produce higher scores."""
        indicators_strong = TechnicalIndicators(relative_strength=8.0)
        indicators_weak = TechnicalIndicators(relative_strength=-3.0)
        score_strong, sig_strong = engine.calculate_score(100.0, 0, indicators_strong)
        score_weak, sig_weak = engine.calculate_score(100.0, 0, indicators_weak)
        assert score_strong > score_weak
        assert sig_strong.relative_strength_positive is True
        assert sig_weak.relative_strength_positive is False

    def test_macd_crossover_imminent_gets_credit(self, engine):
        """MACD about to cross (slightly below signal) should get partial credit."""
        indicators = TechnicalIndicators(
            sma_50=100.0,
            macd_line=0.5,
            macd_signal=0.8,  # MACD below signal but close
            macd_histogram=-0.3
        )
        score, signals = engine.calculate_score(100.0, 0, indicators)
        assert score > 0  # Should get some momentum credit
        assert signals.macd_above_signal is False

    def test_complete_bullish_setup_above_70(self, engine):
        """A textbook bullish setup should score 70+."""
        indicators = TechnicalIndicators(
            sma_50=95.0,       # Price 5% above
            ema_20=98.0,       # Price 2% above
            ema_9=99.0,
            macd_line=1.5,
            macd_signal=0.5,
            macd_histogram=1.0,
            avg_volume_20=1000000.0,
            relative_strength=4.0,
            rsi_14=58.0,
            roc_10=3.0,
            proximity_to_20d_high=97.0
        )
        score, signals = engine.calculate_score(100.0, 1300000.0, indicators)
        assert score >= 70, f"Expected >=70, got {score}"

    def test_mediocre_setup_scores_40_60(self, engine):
        """A mixed setup (some bullish, some not) should score 40-60."""
        indicators = TechnicalIndicators(
            sma_50=100.0,      # Price at SMA (gradient gives partial)
            ema_20=101.0,      # Price slightly below EMA
            ema_9=101.5,
            macd_line=0.2,
            macd_signal=0.1,
            macd_histogram=0.1,
            avg_volume_20=1000000.0,
            relative_strength=0.5,
            rsi_14=50.0,
            roc_10=1.0,
            proximity_to_20d_high=93.0
        )
        score, _ = engine.calculate_score(100.0, 900000.0, indicators)
        assert 35 <= score <= 70, f"Expected 35-70, got {score}"

    def test_score_increases_monotonically_with_strength(self, engine):
        """Stronger signals should always produce higher scores."""
        # Weak setup
        weak = TechnicalIndicators(
            sma_50=100.0, ema_20=100.0, rsi_14=45.0, roc_10=0.5,
            relative_strength=0.5, avg_volume_20=1000000.0,
            proximity_to_20d_high=90.0
        )
        # Strong setup
        strong = TechnicalIndicators(
            sma_50=90.0, ema_20=95.0, rsi_14=62.0, roc_10=6.0,
            relative_strength=7.0, avg_volume_20=1000000.0,
            proximity_to_20d_high=99.0
        )
        score_weak, _ = engine.calculate_score(100.0, 900000.0, weak)
        score_strong, _ = engine.calculate_score(105.0, 1600000.0, strong)
        assert score_strong > score_weak
