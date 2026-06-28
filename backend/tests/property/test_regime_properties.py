"""
Property-Based Tests for the V3 Market Regime Gate.

Replaces the obsolete V2 SMA50/SMA200-crossover properties with the V3 gate:
SPY vs SMA200 with 5-day persistence → RegimeResult(regime, threshold, emit_signals).

  P1  All last-5 closes above SMA200 → BULLISH (threshold 65, emit).
      All last-5 closes below SMA200 → BEARISH (emit_signals False).
      Otherwise → NEUTRAL (threshold 75, emit).  **Validates: R1**
"""

import asyncio
from unittest.mock import AsyncMock

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from api.models import MarketRegime
from config import config
from core.models import StockData
from core.regime_analyzer import MarketRegimeAnalyzer, RegimeResult


def _spy(last5, base=100.0, n=260):
    prices = np.concatenate([np.full(n - 5, base), np.array(last5, dtype=float)])
    return StockData(
        ticker="SPY",
        prices=prices,
        volumes=np.full(n, 1e6),
        timestamps=np.arange(n, dtype=np.int64),
    )


def _run(last5):
    client = AsyncMock()
    client.fetch_stock_data = AsyncMock(return_value=_spy(last5))
    analyzer = MarketRegimeAnalyzer(client)
    return asyncio.get_event_loop().run_until_complete(analyzer.analyze_regime())


class TestRegimeGateProperty:
    @settings(max_examples=40, deadline=None)
    @given(offset=st.floats(min_value=2.0, max_value=40.0))
    def test_all_above_is_bullish(self, offset):
        result = _run([100.0 + offset] * 5)  # all 5 closes clearly above base/SMA200
        assert isinstance(result, RegimeResult)
        assert result.regime == MarketRegime.BULLISH
        assert result.threshold == config.BULLISH_SCORE_THRESHOLD
        assert result.emit_signals is True

    @settings(max_examples=40, deadline=None)
    @given(offset=st.floats(min_value=2.0, max_value=40.0))
    def test_all_below_is_bearish_no_signals(self, offset):
        result = _run([100.0 - offset] * 5)  # all 5 closes clearly below SMA200
        assert result.regime == MarketRegime.BEARISH
        assert result.emit_signals is False

    @settings(max_examples=40, deadline=None)
    @given(
        above=st.floats(min_value=2.0, max_value=40.0),
        below=st.floats(min_value=2.0, max_value=40.0),
    )
    def test_mixed_window_is_neutral(self, above, below):
        # 4 above + 1 below → neither all-above nor all-below → NEUTRAL
        result = _run([100.0 + above] * 4 + [100.0 - below])
        assert result.regime == MarketRegime.NEUTRAL
        assert result.threshold == config.NEUTRAL_SCORE_THRESHOLD
        assert result.emit_signals is True
