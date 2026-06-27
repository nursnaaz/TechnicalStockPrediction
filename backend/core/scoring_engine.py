"""
Scoring Engine

Assigns bullish scores based on technical indicator signals.
"""

from core.models import TechnicalIndicators
from api.models import IndicatorSignals


class ScoringEngine:
    """Assigns bullish scores based on technical indicators."""

    def calculate_score(
        self,
        current_price: float,
        current_volume: float,
        indicators: TechnicalIndicators
    ) -> tuple[int, IndicatorSignals]:
        """
        Calculate bullish score and signal breakdown.

        Scoring Rules:
        - Price above SMA(50): 20 points
        - Price above EMA(20): 15 points
        - MACD line above signal line: 20 points
        - MACD histogram positive: 10 points
        - Volume above average * 1.2: 15 points
        - Relative strength positive: 20 points
        Maximum total: 100 points

        Args:
            current_price: Latest price
            current_volume: Latest volume
            indicators: Calculated technical indicators

        Returns:
            Tuple of (bullish_score, signals)
        """
        total_score = 0

        # Check price above SMA(50) - 20 points
        price_above_sma50 = False
        if indicators.sma_50 is not None:
            if current_price > indicators.sma_50:
                price_above_sma50 = True
                total_score += 20

        # Check price above EMA(20) - 15 points
        price_above_ema20 = False
        if indicators.ema_20 is not None:
            if current_price > indicators.ema_20:
                price_above_ema20 = True
                total_score += 15

        # Check MACD line above signal line - 20 points
        macd_above_signal = False
        if indicators.macd_line is not None and indicators.macd_signal is not None:
            if indicators.macd_line > indicators.macd_signal:
                macd_above_signal = True
                total_score += 20

        # Check MACD histogram positive - 10 points
        macd_histogram_positive = False
        if indicators.macd_histogram is not None:
            if indicators.macd_histogram > 0:
                macd_histogram_positive = True
                total_score += 10

        # Check volume above average by at least 20% - 15 points
        volume_above_average = False
        if indicators.avg_volume_20 is not None:
            if current_volume > indicators.avg_volume_20 * 1.2:
                volume_above_average = True
                total_score += 15

        # Check relative strength positive - 20 points
        relative_strength_positive = False
        if indicators.relative_strength is not None:
            if indicators.relative_strength > 0:
                relative_strength_positive = True
                total_score += 20

        # Cap at 100 (though max possible is 100)
        total_score = min(total_score, 100)

        # Create signals object
        signals = IndicatorSignals(
            price_above_sma50=price_above_sma50,
            price_above_ema20=price_above_ema20,
            macd_above_signal=macd_above_signal,
            macd_histogram_positive=macd_histogram_positive,
            volume_above_average=volume_above_average,
            relative_strength_positive=relative_strength_positive
        )

        return total_score, signals
