"""
Unit tests for Market Regime Analyzer (V3)

Tests the SPY 200-day SMA gate with 5-day persistence, the RegimeResult contract
(regime / threshold / emit_signals), and error handling.
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock

from api.models import MarketRegime
from core.regime_analyzer import MarketRegimeAnalyzer, RegimeResult
from core.api_client import RestApiClient, ApiError
from core.models import StockData
from config import config


@pytest.fixture
def mock_api_client():
    return AsyncMock(spec=RestApiClient)


@pytest.fixture
def regime_analyzer(mock_api_client):
    return MarketRegimeAnalyzer(mock_api_client)


def make_spy(last5, base: float = 100.0, n: int = 260) -> StockData:
    """
    Build synthetic SPY data: `n` bars at `base`, with the final 5 closes set
    explicitly to `last5`. With base-dominated history, SMA200 ≈ base, so the
    last-5 values control the gate.
    """
    assert len(last5) == 5
    prices = np.concatenate([np.full(n - 5, base), np.array(last5, dtype=float)])
    return StockData(
        ticker="SPY",
        prices=prices,
        volumes=np.full(n, 50_000_000.0),
        timestamps=np.arange(n, dtype=np.int64) * 86_400_000,
    )


class TestRegimeGate:
    @pytest.mark.asyncio
    async def test_bullish_all_five_above(self, regime_analyzer, mock_api_client):
        mock_api_client.fetch_stock_data.return_value = make_spy([110, 110, 110, 110, 110])
        result = await regime_analyzer.analyze_regime()
        assert result.regime == MarketRegime.BULLISH
        assert result.threshold == config.BULLISH_SCORE_THRESHOLD  # 65
        assert result.emit_signals is True

    @pytest.mark.asyncio
    async def test_bearish_all_five_below(self, regime_analyzer, mock_api_client):
        mock_api_client.fetch_stock_data.return_value = make_spy([90, 90, 90, 90, 90])
        result = await regime_analyzer.analyze_regime()
        assert result.regime == MarketRegime.BEARISH
        assert result.emit_signals is False  # zero signals in bear market

    @pytest.mark.asyncio
    async def test_neutral_four_of_five_above_not_bullish(self, regime_analyzer, mock_api_client):
        # current close above SMA200 but one of the last 5 is below → NEUTRAL, not BULLISH
        mock_api_client.fetch_stock_data.return_value = make_spy([90, 110, 110, 110, 110])
        result = await regime_analyzer.analyze_regime()
        assert result.regime == MarketRegime.NEUTRAL
        assert result.threshold == config.NEUTRAL_SCORE_THRESHOLD  # 75
        assert result.emit_signals is True

    @pytest.mark.asyncio
    async def test_neutral_four_of_five_below_not_bearish(self, regime_analyzer, mock_api_client):
        # current close below SMA200 but one of the last 5 is above → NEUTRAL, not BEARISH
        mock_api_client.fetch_stock_data.return_value = make_spy([110, 90, 90, 90, 90])
        result = await regime_analyzer.analyze_regime()
        assert result.regime == MarketRegime.NEUTRAL
        assert result.emit_signals is True

    @pytest.mark.asyncio
    async def test_fetch_uses_extended_history_window(self, regime_analyzer, mock_api_client):
        mock_api_client.fetch_stock_data.return_value = make_spy([110, 110, 110, 110, 110])
        await regime_analyzer.analyze_regime(as_of_date="2025-01-01")
        mock_api_client.fetch_stock_data.assert_called_once_with(
            "SPY", days=config.HISTORY_FETCH_DAYS, as_of_date="2025-01-01"
        )
        assert config.HISTORY_FETCH_DAYS >= config.MIN_TRADING_BARS


class TestRegimeFallbacks:
    @pytest.mark.asyncio
    async def test_api_failure_defaults_to_neutral(self, regime_analyzer, mock_api_client):
        mock_api_client.fetch_stock_data.side_effect = ApiError("boom")
        result = await regime_analyzer.analyze_regime()
        assert result.regime == MarketRegime.NEUTRAL
        assert result.threshold == config.NEUTRAL_SCORE_THRESHOLD
        assert result.emit_signals is True

    @pytest.mark.asyncio
    async def test_unexpected_error_defaults_to_neutral(self, regime_analyzer, mock_api_client):
        mock_api_client.fetch_stock_data.side_effect = RuntimeError("unexpected")
        result = await regime_analyzer.analyze_regime()
        assert result.regime == MarketRegime.NEUTRAL
        assert result.emit_signals is True

    @pytest.mark.asyncio
    async def test_insufficient_history_defaults_to_neutral(self, regime_analyzer, mock_api_client):
        # Only 100 bars → SMA200 incomputable → NEUTRAL fallback
        short = StockData(
            ticker="SPY",
            prices=np.full(100, 100.0),
            volumes=np.full(100, 1.0),
            timestamps=np.arange(100),
        )
        mock_api_client.fetch_stock_data.return_value = short
        result = await regime_analyzer.analyze_regime()
        assert result.regime == MarketRegime.NEUTRAL
        assert result.emit_signals is True


class TestRegimeResultType:
    @pytest.mark.asyncio
    async def test_returns_regime_result(self, regime_analyzer, mock_api_client):
        mock_api_client.fetch_stock_data.return_value = make_spy([110, 110, 110, 110, 110])
        result = await regime_analyzer.analyze_regime()
        assert isinstance(result, RegimeResult)
