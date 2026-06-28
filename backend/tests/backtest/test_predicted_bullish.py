"""
V3 task 4.2: regime-aware predicted-bullish in the backtest engine.

Drives BacktestEngine._analyze_trade directly with synthetic forward data so the
classification (TP/FP/FN/TN) reflects the shipped BUY logic:
    BUY  <=>  regime tradeable (not bearish) AND score >= regime threshold.
"""

from unittest.mock import Mock
from backtest.engine import BacktestEngine


def _engine():
    return BacktestEngine(api_client=Mock(), orchestrator=Mock())


def _forward(gain_pct):
    """Forward bars where price rises by `gain_pct` from entry 100."""
    peak = 100.0 * (1 + gain_pct / 100.0)
    return [{"high": peak, "low": 100.0, "close": peak} for _ in range(30)]


def test_bullish_high_score_went_up_is_true_positive():
    t = _engine()._analyze_trade(
        "AAPL", 100.0, 80, Mock(), _forward(10.0), 30,
        regime_tradeable=True, bullish_threshold=65,
    )
    assert t["predicted_bullish"] is True
    assert t["actually_went_up"] is True
    assert t["classification"] == "true_positive"


def test_below_threshold_is_not_predicted():
    t = _engine()._analyze_trade(
        "AAPL", 100.0, 60, Mock(), _forward(10.0), 30,
        regime_tradeable=True, bullish_threshold=65,
    )
    assert t["predicted_bullish"] is False
    # went up but not predicted → false negative
    assert t["classification"] == "false_negative"


def test_bearish_regime_never_predicts_bullish():
    """Even a 90 score in a bearish market is NOT a BUY (March-2026 behavior)."""
    t = _engine()._analyze_trade(
        "AAPL", 100.0, 90, Mock(), _forward(12.0), 30,
        regime_tradeable=False, bullish_threshold=65,
    )
    assert t["predicted_bullish"] is False
    assert t["classification"] == "false_negative"  # went up but we (correctly) stayed out


def test_neutral_threshold_75_boundary():
    below = _engine()._analyze_trade(
        "AAPL", 100.0, 70, Mock(), _forward(1.0), 30,
        regime_tradeable=True, bullish_threshold=75,
    )
    at = _engine()._analyze_trade(
        "AAPL", 100.0, 75, Mock(), _forward(1.0), 30,
        regime_tradeable=True, bullish_threshold=75,
    )
    assert below["predicted_bullish"] is False
    assert at["predicted_bullish"] is True
