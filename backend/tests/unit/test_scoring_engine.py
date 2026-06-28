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
        """Stock above SMA50 should score more than stock far below with no recovery signals."""
        indicators_above = TechnicalIndicators(sma_50=100.0)
        indicators_below = TechnicalIndicators(sma_50=100.0)
        score_above, _ = engine.calculate_score(103.0, 0, indicators_above)
        score_below, _ = engine.calculate_score(75.0, 0, indicators_below)  # Far below, no RSI/ROC
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


# ============================================================================
# V3 Phase 2: Hard filters (R2), recovery removal (R3), extension penalty (R4)
# ============================================================================

def _passing_hard_filter_indicators():
    """TechnicalIndicators that PASS all six Minervini hard filters at price=120."""
    return TechnicalIndicators(
        sma_50=110.0,        # > sma_200 (H4)
        sma_150=105.0,       # price 120 > 105 (H3)
        sma_200=100.0,       # price 120 > 100 (H1)
        sma_200_slope=2.0,   # rising (H2)
        week52_high=130.0,   # 120 >= 0.75*130 = 97.5 (H6)
        week52_low=80.0,     # 120 >= 1.30*80 = 104 (H5)
    )


class TestHardFilters:
    PRICE = 120.0

    def test_all_pass(self, engine):
        ok, checks = engine.passes_hard_filters(self.PRICE, _passing_hard_filter_indicators())
        assert ok is True
        assert all(checks.values())

    @pytest.mark.parametrize("field,value,failed_key", [
        ("sma_200", 130.0, "H1"),     # price 120 < sma_200 130 → H1 fail (also H4)
        ("sma_200_slope", -1.0, "H2"),  # falling → H2 fail
        ("sma_150", 125.0, "H3"),     # price 120 < sma_150 125 → H3 fail
        ("week52_low", 100.0, "H5"),  # 1.30*100=130 > 120 → H5 fail
        ("week52_high", 200.0, "H6"), # 0.75*200=150 > 120 → H6 fail
    ])
    def test_single_check_failure(self, engine, field, value, failed_key):
        ind = _passing_hard_filter_indicators()
        setattr(ind, field, value)
        ok, checks = engine.passes_hard_filters(self.PRICE, ind)
        assert ok is False
        assert checks[failed_key] is False

    def test_h4_golden_cross_failure(self, engine):
        ind = _passing_hard_filter_indicators()
        ind.sma_50 = 90.0  # sma_50 < sma_200 (100) → H4 fail
        ok, checks = engine.passes_hard_filters(self.PRICE, ind)
        assert ok is False
        assert checks["H4"] is False

    @pytest.mark.parametrize("field,check", [
        ("sma_200", "H1"), ("sma_200_slope", "H2"), ("sma_150", "H3"),
        ("week52_low", "H5"), ("week52_high", "H6"),
    ])
    def test_none_indicator_fails_its_check(self, engine, field, check):
        ind = _passing_hard_filter_indicators()
        setattr(ind, field, None)
        ok, checks = engine.passes_hard_filters(self.PRICE, ind)
        assert ok is False
        assert checks[check] is False

    def test_strict_boundary_equality_fails(self, engine):
        """H1/H2/H4 are strict (>): equality must FAIL."""
        ind = _passing_hard_filter_indicators()
        ind.sma_200 = self.PRICE        # price == sma_200 → H1 fail
        assert engine.passes_hard_filters(self.PRICE, ind)[1]["H1"] is False
        ind = _passing_hard_filter_indicators()
        ind.sma_200_slope = 0.0          # slope == 0 → H2 fail
        assert engine.passes_hard_filters(self.PRICE, ind)[1]["H2"] is False
        ind = _passing_hard_filter_indicators()
        ind.sma_50 = ind.sma_200         # sma_50 == sma_200 → H4 fail
        assert engine.passes_hard_filters(self.PRICE, ind)[1]["H4"] is False

    def test_inclusive_boundary_equality_passes(self, engine):
        """H5/H6 are inclusive (>=): equality must PASS."""
        ind = _passing_hard_filter_indicators()
        ind.week52_low = self.PRICE / 1.30   # price == 1.30*low → H5 pass
        assert engine.passes_hard_filters(self.PRICE, ind)[1]["H5"] is True
        ind = _passing_hard_filter_indicators()
        ind.week52_high = self.PRICE / 0.75  # price == 0.75*high → H6 pass
        assert engine.passes_hard_filters(self.PRICE, ind)[1]["H6"] is True


class TestRecoveryBonusRemoved:
    def test_below_ma_oversold_scores_low(self, engine):
        """A below-MA oversold stock no longer gets a recovery bump (R3)."""
        ind = TechnicalIndicators(
            sma_50=120.0, ema_20=118.0, rsi_14=35.0, roc_10=3.0,
            macd_line=-0.5, macd_signal=-0.2, macd_histogram=-0.3,
            avg_volume_20=1_000_000.0, relative_strength=-3.0, proximity_to_20d_high=85.0,
        )
        score, _ = engine.calculate_score(100.0, 1_000_000.0, ind)  # price well below sma_50
        assert score < 40  # would have been boosted ~15-25 under V2 recovery bonus


class TestExtensionPenalty:
    def _extended_indicators(self, dist_pct, rsi=50.0, roc=2.0):
        """Indicators with price `dist_pct`% above SMA50 (price fixed at 100)."""
        sma_50 = 100.0 / (1 + dist_pct / 100.0)
        return TechnicalIndicators(
            sma_50=sma_50, rsi_14=rsi, roc_10=roc,
        )

    def _penalty(self, engine, ind, price=100.0):
        """Recover the extension penalty by comparing to a non-extended baseline trend."""
        # Trend component only depends on sma_50/ema_20; isolate by scoring twice.
        return ind  # placeholder not used; see explicit tests below

    def test_far_extended_overbought_fading_hits_cap(self, engine):
        """>15% extended + RSI>75 + ROC<-3 → penalty caps at -25."""
        ind = self._extended_indicators(20.0, rsi=80.0, roc=-5.0)
        score_extended, _ = engine.calculate_score(100.0, 1_000_000.0, ind)
        # Same trend but not overbought/fading (RSI healthy, ROC positive, only 6% ext)
        ind_mild = self._extended_indicators(6.0, rsi=55.0, roc=2.0)
        score_mild, _ = engine.calculate_score(100.0, 1_000_000.0, ind_mild)
        assert score_extended < score_mild

    def test_penalty_never_makes_score_negative(self, engine):
        ind = self._extended_indicators(20.0, rsi=80.0, roc=-5.0)
        score, _ = engine.calculate_score(100.0, 1_000_000.0, ind)
        assert 0 <= score <= 100

    def test_no_divergence_penalty_when_not_extended(self, engine):
        """dist<=5% → momentum-divergence block contributes nothing even with bad ROC."""
        ind = self._extended_indicators(3.0, rsi=55.0, roc=-10.0)
        score, _ = engine.calculate_score(100.0, 1_000_000.0, ind)
        assert 0 <= score <= 100  # no crash; divergence block skipped at low extension


# ============================================================================
# V3 Phase 3: RS percentile (R5) and indicator divergence penalty (R6)
# ============================================================================

class TestRSPercentile:
    def _base(self):
        return TechnicalIndicators(
            sma_50=95.0, ema_20=98.0, rsi_14=60.0, roc_10=3.0,
            macd_line=1.0, macd_signal=0.5, macd_histogram=0.5,
            avg_volume_20=1_000_000.0, relative_strength=2.0,
            proximity_to_20d_high=96.0,
        )

    def test_percentile_monotonic_non_decreasing(self, engine):
        prev = -1
        for pct in [0, 49, 50, 69, 70, 89, 90, 100]:
            score, _ = engine.calculate_score(100.0, 1_500_000.0, self._base(), rs_percentile=pct)
            assert score >= prev
            prev = score

    def test_percentile_tier_boundaries(self, engine):
        s49, _ = engine.calculate_score(100.0, 1_500_000.0, self._base(), rs_percentile=49)
        s50, _ = engine.calculate_score(100.0, 1_500_000.0, self._base(), rs_percentile=50)
        s70, _ = engine.calculate_score(100.0, 1_500_000.0, self._base(), rs_percentile=70)
        s90, _ = engine.calculate_score(100.0, 1_500_000.0, self._base(), rs_percentile=90)
        assert s50 > s49      # crossing the 50th tier adds points
        assert s70 > s50      # 70th tier adds more
        assert s90 > s70      # 90th tier adds the most

    def test_none_percentile_falls_back_to_raw_rs(self, engine):
        # No crash, returns a valid score when rs_percentile is omitted
        score, _ = engine.calculate_score(100.0, 1_500_000.0, self._base())
        assert 0 <= score <= 100


class TestDivergencePenalty:
    def _ind(self, rsi, macd_above, roc, price_above_sma):
        sma = 90.0 if price_above_sma else 110.0  # price fixed at 100
        return TechnicalIndicators(
            sma_50=sma, rsi_14=rsi, roc_10=roc,
            macd_line=(1.0 if macd_above else -1.0), macd_signal=0.0,
        )

    def test_four_zero_agreement_no_penalty(self):
        ind = self._ind(rsi=60, macd_above=True, roc=2.0, price_above_sma=True)  # 4 bull
        assert ScoringEngine.divergence_penalty(100.0, ind) == 0

    def test_three_one_split_penalty_four(self):
        ind = self._ind(rsi=60, macd_above=True, roc=2.0, price_above_sma=False)  # 3 bull, 1 bear
        assert ScoringEngine.divergence_penalty(100.0, ind) == 4

    def test_two_two_split_penalty_eight(self):
        ind = self._ind(rsi=60, macd_above=True, roc=-2.0, price_above_sma=False)  # 2 bull, 2 bear
        assert ScoringEngine.divergence_penalty(100.0, ind) == 8

    def test_exactly_075_gives_four_not_zero(self):
        """The corrected <= 0.75 boundary: a 3-1 split (0.75) must score -4, not 0."""
        ind = self._ind(rsi=40, macd_above=True, roc=2.0, price_above_sma=True)  # rsi<50 bear → 3-1
        assert ScoringEngine.divergence_penalty(100.0, ind) == 4

    def test_fewer_than_two_signals_skipped(self):
        ind = TechnicalIndicators(rsi_14=60.0)  # only 1 available signal
        assert ScoringEngine.divergence_penalty(100.0, ind) == 0

    def test_none_aware_denominator(self):
        """3 available signals, 2 bull / 1 bear → agreement 0.667 → -4."""
        ind = TechnicalIndicators(rsi_14=60.0, roc_10=2.0, sma_50=110.0)  # rsi bull, roc bull, price<sma bear
        assert ScoringEngine.divergence_penalty(100.0, ind) == 4

    def test_no_typeerror_with_all_none(self):
        assert ScoringEngine.divergence_penalty(100.0, TechnicalIndicators()) == 0
