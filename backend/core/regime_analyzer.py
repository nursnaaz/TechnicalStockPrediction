"""
Market Regime Analyzer (V3)

Analyzes broad-market conditions via SPY using a 200-day SMA gate with 5-day
persistence (plus EMA21 for context). Returns a RegimeResult carrying the regime,
the score threshold to apply, and whether any BUY signals should be emitted.

Gate logic (R1):
- BULLISH: SPY close > SMA200 AND all last 5 closes > SMA200  → threshold 65, emit
- BEARISH: SPY close < SMA200 AND all last 5 closes < SMA200  → emit NOTHING
- NEUTRAL: otherwise                                          → threshold 75, emit
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from api.models import MarketRegime
from config import config
from core.api_client import ApiError, RestApiClient

logger = logging.getLogger(__name__)


@dataclass
class RegimeResult:
    """Outcome of regime analysis consumed by the orchestrator."""

    regime: MarketRegime
    threshold: int  # score threshold for a BUY (ignored when emit_signals is False)
    emit_signals: bool  # False in BEARISH → orchestrator returns zero candidates


class MarketRegimeAnalyzer:
    """Analyzes current market conditions via the SPY 200-day SMA gate."""

    def __init__(self, api_client: RestApiClient):
        """
        Initialize with API client dependency.

        Args:
            api_client: RestApiClient instance for fetching market data
        """
        self.api_client = api_client
        logger.debug("MarketRegimeAnalyzer initialized")

    async def analyze_regime(self, as_of_date: str = None) -> RegimeResult:
        """
        Determine the current market regime via the SPY 200-day SMA gate.

        Args:
            as_of_date: Optional cutoff date (YYYY-MM-DD). If provided, only uses
                        data available up to this date (point-in-time, no look-ahead).

        Returns:
            RegimeResult(regime, threshold, emit_signals).
            Defaults to NEUTRAL (emit, threshold 75) on insufficient data or API error.
        """
        try:
            logger.info("Fetching SPY data for market regime analysis")
            spy_data = await self.api_client.fetch_stock_data(
                "SPY", days=config.HISTORY_FETCH_DAYS, as_of_date=as_of_date
            )

            closes = np.asarray(spy_data.prices, dtype=float)
            sma_200 = self._calculate_sma(closes, 200)
            persistence = config.REGIME_PERSISTENCE_DAYS

            if sma_200 is None or len(closes) < persistence:
                logger.warning(
                    "Insufficient SPY history for regime gate "
                    f"({len(closes)} bars); defaulting to NEUTRAL"
                )
                return self._neutral()

            # EMA21 computed for trend context (logged, not part of the gate decision).
            ema_21 = self._calculate_ema(closes, 21)

            current_close = float(closes[-1])
            last_n = closes[-persistence:]
            spy_above_200 = current_close > sma_200
            last_n_above = bool(np.all(last_n > sma_200))
            last_n_below = bool(np.all(last_n < sma_200))

            if spy_above_200 and last_n_above:
                logger.info(
                    f"Market regime: BULLISH (close={current_close:.2f}, "
                    f"SMA200={sma_200:.2f}, EMA21={ema_21}, last{persistence} all above)"
                )
                return RegimeResult(
                    regime=MarketRegime.BULLISH,
                    threshold=config.BULLISH_SCORE_THRESHOLD,
                    emit_signals=True,
                )

            if (not spy_above_200) and last_n_below:
                logger.info(
                    f"Market regime: BEARISH (close={current_close:.2f}, "
                    f"SMA200={sma_200:.2f}, last{persistence} all below) — emitting zero signals"
                )
                return RegimeResult(
                    regime=MarketRegime.BEARISH,
                    threshold=config.NEUTRAL_SCORE_THRESHOLD,  # unused (emit False)
                    emit_signals=False,
                )

            logger.info(f"Market regime: NEUTRAL (close={current_close:.2f}, SMA200={sma_200:.2f})")
            return self._neutral()

        except ApiError as e:
            logger.error(f"API error during market regime analysis: {e}")
            logger.warning("Defaulting to NEUTRAL regime due to API failure")
            return self._neutral()
        except Exception as e:
            logger.error(f"Unexpected error during market regime analysis: {e}")
            logger.warning("Defaulting to NEUTRAL regime due to unexpected error")
            return self._neutral()

    @staticmethod
    def _neutral() -> RegimeResult:
        """Build the default NEUTRAL result (emit, threshold 75)."""
        return RegimeResult(
            regime=MarketRegime.NEUTRAL,
            threshold=config.NEUTRAL_SCORE_THRESHOLD,
            emit_signals=True,
        )

    @staticmethod
    def _calculate_sma(prices: "np.ndarray", period: int) -> Optional[float]:
        """Calculate Simple Moving Average, or None if insufficient data."""
        if len(prices) < period:
            return None
        return float(np.mean(prices[-period:]))

    @staticmethod
    def _calculate_ema(prices: "np.ndarray", period: int) -> Optional[float]:
        """Calculate Exponential Moving Average (context only), or None if insufficient."""
        if len(prices) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = float(np.mean(prices[:period]))
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return float(ema)
