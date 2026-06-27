"""
Scoring Engine V2

Assigns bullish scores using GRADIENT scoring (not binary pass/fail).
Each indicator contributes partial points based on proximity/strength.

Designed to produce a meaningful distribution where:
- Score >= 70: Strong bullish signal (high confidence)
- Score 50-69: Moderate bullish signal
- Score 30-49: Weak/neutral
- Score < 30: Bearish/no signal

Optimized via backtesting on 495 trades across 5 dates:
- Target: Score threshold 70, Gain threshold 5%, Horizon 30 days
- Goal: Minimize False Negatives while keeping Precision >= 70%
"""

from core.models import TechnicalIndicators
from api.models import IndicatorSignals


class ScoringEngine:
    """Assigns bullish scores using gradient-based technical indicators."""

    def calculate_score(
        self,
        current_price: float,
        current_volume: float,
        indicators: TechnicalIndicators
    ) -> tuple[int, IndicatorSignals]:
        """
        Calculate bullish score with gradient scoring.

        Scoring Components (max 100 points):
        1. Trend Position (SMA50 + EMA20): 0-25 points (gradient)
        2. Momentum (MACD + ROC): 0-25 points (gradient)
        3. Strength (RSI + Relative Strength): 0-25 points (gradient)
        4. Confirmation (Volume + Breakout Proximity): 0-25 points (gradient)

        Args:
            current_price: Latest closing price
            current_volume: Latest daily volume
            indicators: Calculated technical indicators

        Returns:
            Tuple of (bullish_score 0-100, signals)
        """
        total_score = 0.0

        # === COMPONENT 1: TREND POSITION (0-25 pts) ===
        # How well positioned is the stock relative to moving averages?
        trend_score = 0.0

        # SMA(50) proximity: 0-13 points (gradient)
        price_above_sma50 = False
        if indicators.sma_50 is not None and indicators.sma_50 > 0:
            distance_pct = ((current_price - indicators.sma_50) / indicators.sma_50) * 100
            if distance_pct > 5:
                trend_score += 13      # Well above — strong uptrend
                price_above_sma50 = True
            elif distance_pct > 2:
                trend_score += 11      # Clearly above
                price_above_sma50 = True
            elif distance_pct > 0:
                trend_score += 9       # Slightly above
                price_above_sma50 = True
            elif distance_pct > -2:
                trend_score += 6       # Near (within 2%) — about to cross
            elif distance_pct > -5:
                trend_score += 3       # Approaching from below
            # else: 0 (far below)

        # EMA(20) proximity: 0-12 points (gradient)
        price_above_ema20 = False
        if indicators.ema_20 is not None and indicators.ema_20 > 0:
            distance_pct = ((current_price - indicators.ema_20) / indicators.ema_20) * 100
            if distance_pct > 3:
                trend_score += 12      # Strong short-term trend
                price_above_ema20 = True
            elif distance_pct > 1:
                trend_score += 10      # Above
                price_above_ema20 = True
            elif distance_pct > 0:
                trend_score += 8       # Slightly above
                price_above_ema20 = True
            elif distance_pct > -1:
                trend_score += 5       # Near — testing support
            elif distance_pct > -3:
                trend_score += 2       # Approaching
            # else: 0

        total_score += min(trend_score, 25)

        # === COMPONENT 2: MOMENTUM (0-25 pts) ===
        # Is momentum building or fading?
        momentum_score = 0.0

        # MACD: 0-15 points (gradient)
        macd_above_signal = False
        macd_histogram_positive = False
        if indicators.macd_line is not None and indicators.macd_signal is not None:
            macd_diff = indicators.macd_line - indicators.macd_signal
            if macd_diff > 0:
                macd_above_signal = True
                macd_histogram_positive = True
                # Scale by magnitude relative to price
                if indicators.sma_50 and indicators.sma_50 > 0:
                    macd_strength = abs(macd_diff) / indicators.sma_50 * 1000
                    if macd_strength > 5:
                        momentum_score += 15   # Strong MACD
                    elif macd_strength > 2:
                        momentum_score += 12   # Moderate MACD
                    else:
                        momentum_score += 9    # Weak but positive
                else:
                    momentum_score += 10
            elif macd_diff > -0.5:
                momentum_score += 4    # Nearly crossing (about to turn bullish)
                if indicators.macd_histogram is not None and indicators.macd_histogram > 0:
                    macd_histogram_positive = True
                    momentum_score += 2
        elif indicators.macd_histogram is not None and indicators.macd_histogram > 0:
            macd_histogram_positive = True
            momentum_score += 5

        # Rate of Change (10-day): 0-10 points (gradient)
        if indicators.roc_10 is not None:
            if indicators.roc_10 > 5:
                momentum_score += 10   # Strong upward momentum
            elif indicators.roc_10 > 2:
                momentum_score += 8    # Good momentum
            elif indicators.roc_10 > 0:
                momentum_score += 5    # Slight positive
            elif indicators.roc_10 > -2:
                momentum_score += 2    # Flat (not bearish)
            # else: 0 (falling)

        total_score += min(momentum_score, 25)

        # === COMPONENT 3: STRENGTH (0-25 pts) ===
        # Is the stock showing relative strength and healthy RSI?
        strength_score = 0.0

        # RSI(14): 0-13 points (gradient — favors 40-70 "healthy" zone)
        if indicators.rsi_14 is not None:
            rsi = indicators.rsi_14
            if 50 <= rsi <= 70:
                strength_score += 13   # Ideal bullish zone
            elif 40 <= rsi < 50:
                strength_score += 10   # Recovering — about to turn bullish
            elif 30 <= rsi < 40:
                strength_score += 7    # Oversold bounce potential
            elif 70 < rsi <= 80:
                strength_score += 8    # Strong but overbought risk
            elif rsi < 30:
                strength_score += 4    # Deeply oversold — high risk but bounce possible
            # else (RSI > 80): 0 — extremely overbought

        # Relative Strength vs market: 0-12 points (gradient)
        relative_strength_positive = False
        if indicators.relative_strength is not None:
            rs = indicators.relative_strength
            if rs > 5:
                strength_score += 12   # Significantly outperforming market
                relative_strength_positive = True
            elif rs > 2:
                strength_score += 10   # Outperforming
                relative_strength_positive = True
            elif rs > 0:
                strength_score += 7    # Slightly outperforming
                relative_strength_positive = True
            elif rs > -2:
                strength_score += 4    # In line with market
            elif rs > -5:
                strength_score += 1    # Slightly underperforming
            # else: 0 (significantly lagging)

        total_score += min(strength_score, 25)

        # === COMPONENT 4: CONFIRMATION (0-25 pts) ===
        # Volume and breakout proximity
        confirmation_score = 0.0

        # Volume: 0-12 points (gradient — relaxed)
        volume_above_average = False
        if indicators.avg_volume_20 is not None and indicators.avg_volume_20 > 0:
            vol_ratio = current_volume / indicators.avg_volume_20
            if vol_ratio > 1.5:
                confirmation_score += 12   # High volume — strong confirmation
                volume_above_average = True
            elif vol_ratio > 1.2:
                confirmation_score += 10   # Above average
                volume_above_average = True
            elif vol_ratio > 0.8:
                confirmation_score += 7    # Normal volume (not bearish)
            elif vol_ratio > 0.5:
                confirmation_score += 3    # Below average but not dead
            # else: 0 (very low volume — no interest)

        # Breakout proximity (distance to 20-day high): 0-13 points
        if indicators.proximity_to_20d_high is not None:
            prox = indicators.proximity_to_20d_high
            if prox >= 98:
                confirmation_score += 13   # At or near high — breakout!
            elif prox >= 95:
                confirmation_score += 11   # Very close to high
            elif prox >= 92:
                confirmation_score += 8    # Within striking distance
            elif prox >= 88:
                confirmation_score += 5    # Moderate pullback
            elif prox >= 85:
                confirmation_score += 2    # Deeper pullback
            # else: 0 (far from high)

        total_score += min(confirmation_score, 25)

        # === FINAL SCORE ===
        final_score = int(min(round(total_score), 100))

        # Create signals object (backward-compatible boolean signals)
        signals = IndicatorSignals(
            price_above_sma50=price_above_sma50,
            price_above_ema20=price_above_ema20,
            macd_above_signal=macd_above_signal,
            macd_histogram_positive=macd_histogram_positive,
            volume_above_average=volume_above_average,
            relative_strength_positive=relative_strength_positive
        )

        return final_score, signals
