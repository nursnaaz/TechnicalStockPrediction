"""
Property-Based Tests for the V3 Scoring Engine.

Replaces the obsolete V2 binary-scoring properties (P11-P17) with the V3
Correctness Properties from the spec:

  P2  Hard-filter failure forces exclusion (passes_hard_filters)
  P4  Extension penalty never raises the score; score stays bounded
  P5  RS-percentile scoring is monotonic non-decreasing
  P6  Divergence penalty thresholds (None-aware denominator, <=0.75 boundary)
  P8  Final score is always an int in [0, 100], even with None indicators
"""

import pytest
from hypothesis import given, strategies as st, settings

from core.scoring_engine import ScoringEngine
from core.models import TechnicalIndicators


engine = ScoringEngine()


# ---------------------------------------------------------------------------
# P2: Hard-filter failure
# ---------------------------------------------------------------------------
class TestHardFilterProperty:
    """P2: all_pass is exactly the conjunction of the six checks. **Validates: R2**"""

    @settings(max_examples=50)
    @given(
        price=st.floats(min_value=10, max_value=500),
        sma_200=st.floats(min_value=10, max_value=500),
        slope=st.floats(min_value=-50, max_value=50),
        sma_150=st.floats(min_value=10, max_value=500),
        sma_50=st.floats(min_value=10, max_value=500),
        wk_low=st.floats(min_value=1, max_value=500),
        wk_high=st.floats(min_value=1, max_value=600),
    )
    def test_all_pass_matches_individual_checks(
        self, price, sma_200, slope, sma_150, sma_50, wk_low, wk_high
    ):
        ind = TechnicalIndicators(
            sma_50=sma_50, sma_150=sma_150, sma_200=sma_200,
            sma_200_slope=slope, week52_low=wk_low, week52_high=wk_high,
        )
        ok, checks = engine.passes_hard_filters(price, ind)
        assert ok == all(checks.values())
        assert checks["H1"] == (price > sma_200)
        assert checks["H2"] == (slope > 0)
        assert checks["H4"] == (sma_50 > sma_200)

    @pytest.mark.parametrize("missing", ["sma_200", "sma_200_slope", "sma_150", "week52_low", "week52_high"])
    def test_missing_indicator_fails(self, missing):
        ind = TechnicalIndicators(
            sma_50=110, sma_150=105, sma_200=100, sma_200_slope=1.0,
            week52_low=80, week52_high=130,
        )
        setattr(ind, missing, None)
        ok, _ = engine.passes_hard_filters(120.0, ind)
        assert ok is False


# ---------------------------------------------------------------------------
# P4 + P8: bounds
# ---------------------------------------------------------------------------
class TestScoreBoundsProperty:
    """P8: score is always int in [0,100]. **Validates: R7, R8**"""

    @settings(max_examples=100)
    @given(
        price=st.floats(min_value=1, max_value=1000),
        volume=st.floats(min_value=0, max_value=1e9),
        sma_50=st.one_of(st.none(), st.floats(min_value=1, max_value=1000)),
        ema_20=st.one_of(st.none(), st.floats(min_value=1, max_value=1000)),
        rsi=st.one_of(st.none(), st.floats(min_value=0, max_value=100)),
        roc=st.one_of(st.none(), st.floats(min_value=-50, max_value=50)),
        macd_line=st.one_of(st.none(), st.floats(min_value=-10, max_value=10)),
        macd_signal=st.one_of(st.none(), st.floats(min_value=-10, max_value=10)),
        rs=st.one_of(st.none(), st.floats(min_value=-20, max_value=20)),
        pct=st.one_of(st.none(), st.floats(min_value=0, max_value=100)),
    )
    def test_score_bounded(self, price, volume, sma_50, ema_20, rsi, roc,
                           macd_line, macd_signal, rs, pct):
        ind = TechnicalIndicators(
            sma_50=sma_50, ema_20=ema_20, rsi_14=rsi, roc_10=roc,
            macd_line=macd_line, macd_signal=macd_signal, relative_strength=rs,
            avg_volume_20=1_000_000.0,
        )
        score, _ = engine.calculate_score(price, volume, ind, rs_percentile=pct)
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_all_none_indicators_safe(self):
        score, _ = engine.calculate_score(100.0, 1.0, TechnicalIndicators())
        assert isinstance(score, int) and 0 <= score <= 100


# ---------------------------------------------------------------------------
# P5: RS-percentile monotonicity
# ---------------------------------------------------------------------------
class TestRSPercentileMonotonic:
    """P5: strength contribution is non-decreasing in rs_percentile. **Validates: R5**"""

    @settings(max_examples=50)
    @given(a=st.floats(min_value=0, max_value=100), b=st.floats(min_value=0, max_value=100))
    def test_monotonic(self, a, b):
        lo, hi = min(a, b), max(a, b)
        ind = TechnicalIndicators(
            sma_50=95.0, ema_20=98.0, rsi_14=60.0, roc_10=3.0,
            macd_line=1.0, macd_signal=0.5, avg_volume_20=1_000_000.0,
            relative_strength=2.0, proximity_to_20d_high=96.0,
        )
        s_lo, _ = engine.calculate_score(100.0, 1_500_000.0, ind, rs_percentile=lo)
        s_hi, _ = engine.calculate_score(100.0, 1_500_000.0, ind, rs_percentile=hi)
        assert s_hi >= s_lo


# ---------------------------------------------------------------------------
# P6: Divergence penalty thresholds
# ---------------------------------------------------------------------------
class TestDivergencePenaltyProperty:
    """P6: divergence penalty matches the agreement rule. **Validates: R6**"""

    @settings(max_examples=100)
    @given(
        rsi_bull=st.booleans(),
        macd_bull=st.booleans(),
        roc_bull=st.booleans(),
        price_bull=st.booleans(),
    )
    def test_penalty_matches_agreement(self, rsi_bull, macd_bull, roc_bull, price_bull):
        sma = 90.0 if price_bull else 110.0  # price fixed at 100
        ind = TechnicalIndicators(
            sma_50=sma,
            rsi_14=(60.0 if rsi_bull else 40.0),
            roc_10=(2.0 if roc_bull else -2.0),
            macd_line=(1.0 if macd_bull else -1.0),
            macd_signal=0.0,
        )
        penalty = ScoringEngine.divergence_penalty(100.0, ind)
        bull = sum([rsi_bull, macd_bull, roc_bull, price_bull])
        bear = 4 - bull
        agreement = max(bull, bear) / 4
        if agreement < 0.6:
            expected = 8
        elif agreement <= 0.75:
            expected = 4
        else:
            expected = 0
        assert penalty == expected
        assert penalty in (0, 4, 8)
