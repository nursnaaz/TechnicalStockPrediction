"""
V3 pipeline integration tests (task 4.3).

Wires the REAL core components (UniverseBuilder, MarketRegimeAnalyzer,
IndicatorCalculator, ScoringEngine, RankingService) with a MOCKED api_client that
returns per-ticker synthetic data (>=260 bars). Exercises the V3 behaviors end to
end at the orchestrator level:

  IT-1 regime gate short-circuit (bearish → zero candidates)
  IT-2 indicators → hard-filter exclusion (weak ticker dropped, leader kept)
  IT-3 two-pass RS percentile (stronger relative strength ranks/scored higher)
  IT-4 threshold gate vs backtest-mode (apply_signal_gate=False returns all scores)
"""

import numpy as np
import pytest
from unittest.mock import AsyncMock, Mock

from core.orchestrator import ScanOrchestrator
from core.universe_builder import UniverseBuilder
from core.regime_analyzer import MarketRegimeAnalyzer
from core.indicator_calculator import IndicatorCalculator
from core.scoring_engine import ScoringEngine
from core.ranking_service import RankingService
from core.models import StockData
from api.models import ScanRequest, MarketRegime


N = 260


def _stock(ticker, prices, volumes=None):
    prices = np.asarray(prices, dtype=float)
    if volumes is None:
        volumes = np.full(len(prices), 1_000_000.0)
    return StockData(
        ticker=ticker,
        prices=prices,
        volumes=np.asarray(volumes, dtype=float),
        timestamps=np.arange(len(prices), dtype=np.int64),
    )


def _uptrend(ticker, start=50.0, end=150.0, n=N):
    """Strong uptrend → passes all Minervini hard filters."""
    return _stock(ticker, np.linspace(start, end, n))


def _downtrend(ticker, start=150.0, end=100.0, n=N):
    """Downtrend → price below SMA200 → fails hard filters."""
    return _stock(ticker, np.linspace(start, end, n))


def _make_orchestrator(data_by_ticker):
    """Build an orchestrator with real components and a mocked api_client."""
    api_client = Mock()
    api_client.clear_cache = Mock()

    async def _fetch(ticker, days=365, as_of_date=None):
        return data_by_ticker[ticker]

    api_client.fetch_stock_data = AsyncMock(side_effect=_fetch)

    return ScanOrchestrator(
        api_client=api_client,
        universe_builder=UniverseBuilder(),
        regime_analyzer=MarketRegimeAnalyzer(api_client),
        indicator_calc=IndicatorCalculator(),
        scoring_engine=ScoringEngine(),
        ranking_service=RankingService(),
    )


@pytest.mark.asyncio
async def test_it1_bearish_regime_zero_candidates():
    """IT-1: bearish SPY → empty candidates, regime reported bearish."""
    data = {
        "SPY": _downtrend("SPY"),       # SPY below its SMA200 → BEARISH
        "AAPL": _uptrend("AAPL"),
    }
    orch = _make_orchestrator(data)
    resp = await orch.execute_scan(ScanRequest(tickers=["AAPL"]))
    assert resp.market_regime == MarketRegime.BEARISH
    assert resp.ranked_tickers == []


@pytest.mark.asyncio
async def test_it2_hard_filter_excludes_weak_keeps_leader():
    """IT-2: a downtrending ticker is excluded; an uptrending leader is kept."""
    data = {
        "SPY": _uptrend("SPY"),          # bullish market
        "STRONG": _uptrend("STRONG"),
        "WEAK": _downtrend("WEAK"),      # below MAs → fails hard filters
    }
    orch = _make_orchestrator(data)
    # apply_signal_gate=False isolates the hard-filter gate from the score threshold:
    # a hard-filter PASS appears regardless of score; a FAIL is always excluded.
    resp = await orch.execute_scan(
        ScanRequest(tickers=["STRONG", "WEAK"]), apply_signal_gate=False
    )
    tickers = [t.ticker for t in resp.ranked_tickers]
    assert "WEAK" not in tickers     # below MAs → fails hard filters
    assert "STRONG" in tickers       # uptrend → passes hard filters


@pytest.mark.asyncio
async def test_it3_rs_percentile_orders_leaders_first():
    """IT-3: stronger recent relative strength → higher score / ranked first."""
    # FAST rose more than SLOW over the recent window; both uptrends pass filters.
    data = {
        "SPY": _uptrend("SPY", 90.0, 110.0),
        "FAST": _uptrend("FAST", 40.0, 160.0),   # steeper → higher RS
        "SLOW": _uptrend("SLOW", 95.0, 130.0),   # shallower → lower RS
    }
    orch = _make_orchestrator(data)
    resp = await orch.execute_scan(
        ScanRequest(tickers=["FAST", "SLOW"]), apply_signal_gate=False
    )
    scores = {t.ticker: t.bullish_score for t in resp.ranked_tickers}
    assert "FAST" in scores and "SLOW" in scores
    assert scores["FAST"] >= scores["SLOW"]
    # ranked_tickers is sorted descending by score
    assert resp.ranked_tickers[0].bullish_score >= resp.ranked_tickers[-1].bullish_score


@pytest.mark.asyncio
async def test_it4_backtest_mode_returns_below_threshold_scores():
    """IT-4: apply_signal_gate=False returns ALL hard-filter-passing scored tickers,
    even those below the BUY threshold (needed for FN/TN + threshold sweeps)."""
    data = {
        "SPY": _uptrend("SPY"),
        "AAPL": _uptrend("AAPL"),
    }
    orch = _make_orchestrator(data)
    gated = await orch.execute_scan(ScanRequest(tickers=["AAPL"]), apply_signal_gate=True)
    ungated = await orch.execute_scan(ScanRequest(tickers=["AAPL"]), apply_signal_gate=False)
    # Backtest mode never drops a hard-filter-passing ticker on threshold grounds.
    assert len(ungated.ranked_tickers) >= len(gated.ranked_tickers)
    assert len(ungated.ranked_tickers) == 1
