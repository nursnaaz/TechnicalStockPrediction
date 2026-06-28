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

from core.models import TechnicalIndicators, StockData
from core.stage_classifier import StageClassifier, StageResult
from core.pattern_detector import PatternDetector, PatternResult
from api.models import IndicatorSignals
import numpy as np


class ScoringEngine:
    """Assigns bullish scores using gradient-based technical indicators."""

    def __init__(self):
        self.stage_classifier = StageClassifier()
        self.pattern_detector = PatternDetector()

    def calculate_score(
        self,
        current_price: float,
        current_volume: float,
        indicators: TechnicalIndicators
    ) -> tuple[int, IndicatorSignals]:
        """
        Calculate bullish score with gradient scoring.

        Scoring Components (max 100 points):
        1. Trend Position (SMA50 + EMA20): 0-20 points (gradient)
        2. Momentum (MACD + ROC): 0-20 points (gradient)
        3. Strength (RSI + Relative Strength): 0-20 points (gradient)
        4. Confirmation (Volume + Breakout Proximity): 0-20 points (gradient)
        5. Stage & Pattern Bonus: 0-20 points

        Args:
            current_price: Latest closing price
            current_volume: Latest daily volume
            indicators: Calculated technical indicators

        Returns:
            Tuple of (bullish_score 0-100, signals)
        """
        total_score = 0.0

        # === COMPONENT 1: TREND POSITION (0-20 pts) ===
        # How well positioned is the stock relative to moving averages?
        trend_score = 0.0

        # SMA(50) proximity: 0-10 points (gradient)
        price_above_sma50 = False
        if indicators.sma_50 is not None and indicators.sma_50 > 0:
            distance_pct = ((current_price - indicators.sma_50) / indicators.sma_50) * 100
            if distance_pct > 5:
                trend_score += 10      # Well above — strong uptrend
                price_above_sma50 = True
            elif distance_pct > 2:
                trend_score += 8       # Clearly above
                price_above_sma50 = True
            elif distance_pct > 0:
                trend_score += 6       # Slightly above
                price_above_sma50 = True
            elif distance_pct > -2:
                trend_score += 4       # Near (within 2%) — about to cross
            elif distance_pct > -5:
                trend_score += 2       # Approaching from below

        # EMA(20) proximity: 0-10 points (gradient)
        price_above_ema20 = False
        if indicators.ema_20 is not None and indicators.ema_20 > 0:
            distance_pct = ((current_price - indicators.ema_20) / indicators.ema_20) * 100
            if distance_pct > 3:
                trend_score += 10      # Strong short-term trend
                price_above_ema20 = True
            elif distance_pct > 1:
                trend_score += 8       # Above
                price_above_ema20 = True
            elif distance_pct > 0:
                trend_score += 6       # Slightly above
                price_above_ema20 = True
            elif distance_pct > -1:
                trend_score += 4       # Near — testing support
            elif distance_pct > -3:
                trend_score += 2       # Approaching

        total_score += min(trend_score, 20)

        # === RECOVERY BONUS (0-25 pts) ===
        # Catches oversold bounces — stocks below MAs but showing recovery signals
        # This is the PRIMARY mechanism for reducing false negatives in pullbacks
        recovery_score = 0.0
        if indicators.sma_50 is not None and indicators.sma_50 > 0:
            dist_from_sma50 = ((current_price - indicators.sma_50) / indicators.sma_50) * 100
            # Only apply recovery logic if stock is BELOW SMA50
            if dist_from_sma50 < 0 and dist_from_sma50 > -30:
                # The further below SMA50, the more potential for bounce (contrarian)
                # But only if there's some recovery signal
                
                # RSI recovery signal (0-10 pts)
                if indicators.rsi_14 is not None:
                    if 30 <= indicators.rsi_14 <= 45:
                        recovery_score += 10  # Recovering from oversold - strongest signal
                    elif indicators.rsi_14 < 30:
                        recovery_score += 7   # Deeply oversold - high bounce potential
                    elif 45 < indicators.rsi_14 <= 55:
                        recovery_score += 5   # Neutral but below MA - building
                
                # Positive ROC while below MA = early recovery momentum (0-8 pts)
                if indicators.roc_10 is not None:
                    if indicators.roc_10 > 5:
                        recovery_score += 8   # Strong bounce underway
                    elif indicators.roc_10 > 2:
                        recovery_score += 6   # Good recovery momentum
                    elif indicators.roc_10 > 0:
                        recovery_score += 4   # Price turning up
                    elif indicators.roc_10 > -2:
                        recovery_score += 2   # Stabilizing (not falling anymore)
                
                # Proximity to SMA50 from below (0-7 pts)
                if dist_from_sma50 > -3:
                    recovery_score += 7   # Very close to reclaiming - breakout imminent
                elif dist_from_sma50 > -7:
                    recovery_score += 5   # Moderate pullback - healthy
                elif dist_from_sma50 > -12:
                    recovery_score += 3   # Deeper pullback
                elif dist_from_sma50 > -20:
                    recovery_score += 1   # Far below but not catastrophic

        total_score += min(recovery_score, 25)

        # === EXTENSION PENALTY (0 to -15 pts) ===
        # Penalizes stocks that are TOO far above their MAs (exhausted/overbought)
        # These are the false positives: KO, PG, JNJ at peak with all signals TRUE
        extension_penalty = 0.0
        if indicators.sma_50 is not None and indicators.sma_50 > 0:
            dist_above = ((current_price - indicators.sma_50) / indicators.sma_50) * 100
            if dist_above > 15:
                extension_penalty += 8   # Very extended above SMA50
            elif dist_above > 10:
                extension_penalty += 5   # Extended
            
            # RSI overbought penalty
            if indicators.rsi_14 is not None:
                if indicators.rsi_14 > 75:
                    extension_penalty += 7  # Overbought - likely to pull back
                elif indicators.rsi_14 > 70:
                    extension_penalty += 4  # Getting overbought
            
            # Negative ROC despite being above MAs = momentum fading
            if indicators.roc_10 is not None and dist_above > 5:
                if indicators.roc_10 < -2:
                    extension_penalty += 5  # Losing momentum while extended
                elif indicators.roc_10 < 0:
                    extension_penalty += 2  # Slowing down

        total_score -= min(extension_penalty, 15)

        # === COMPONENT 2: MOMENTUM (0-20 pts) ===
        # Is momentum building or fading?
        momentum_score = 0.0

        # MACD: 0-12 points (gradient)
        macd_above_signal = False
        macd_histogram_positive = False
        if indicators.macd_line is not None and indicators.macd_signal is not None:
            macd_diff = indicators.macd_line - indicators.macd_signal
            if macd_diff > 0:
                macd_above_signal = True
                macd_histogram_positive = True
                if indicators.sma_50 and indicators.sma_50 > 0:
                    macd_strength = abs(macd_diff) / indicators.sma_50 * 1000
                    if macd_strength > 5:
                        momentum_score += 12
                    elif macd_strength > 2:
                        momentum_score += 9
                    else:
                        momentum_score += 7
                else:
                    momentum_score += 8
            elif macd_diff > -0.5:
                momentum_score += 3
                if indicators.macd_histogram is not None and indicators.macd_histogram > 0:
                    macd_histogram_positive = True
                    momentum_score += 2
        elif indicators.macd_histogram is not None and indicators.macd_histogram > 0:
            macd_histogram_positive = True
            momentum_score += 4

        # Rate of Change (10-day): 0-8 points (gradient)
        if indicators.roc_10 is not None:
            if indicators.roc_10 > 5:
                momentum_score += 8
            elif indicators.roc_10 > 2:
                momentum_score += 6
            elif indicators.roc_10 > 0:
                momentum_score += 4
            elif indicators.roc_10 > -2:
                momentum_score += 2

        total_score += min(momentum_score, 20)

        # === COMPONENT 3: STRENGTH (0-20 pts) ===
        # Is the stock showing relative strength and healthy RSI?
        strength_score = 0.0

        # RSI(14): 0-10 points (gradient — favors 40-70 "healthy" zone)
        if indicators.rsi_14 is not None:
            rsi = indicators.rsi_14
            if 50 <= rsi <= 70:
                strength_score += 10   # Ideal bullish zone
            elif 40 <= rsi < 50:
                strength_score += 8    # Recovering — about to turn bullish
            elif 30 <= rsi < 40:
                strength_score += 5    # Oversold bounce potential
            elif 70 < rsi <= 80:
                strength_score += 6    # Strong but overbought risk
            elif rsi < 30:
                strength_score += 3    # Deeply oversold — high risk but bounce possible

        # Relative Strength vs market: 0-10 points (gradient)
        relative_strength_positive = False
        if indicators.relative_strength is not None:
            rs = indicators.relative_strength
            if rs > 5:
                strength_score += 10   # Significantly outperforming market
                relative_strength_positive = True
            elif rs > 2:
                strength_score += 8    # Outperforming
                relative_strength_positive = True
            elif rs > 0:
                strength_score += 6    # Slightly outperforming
                relative_strength_positive = True
            elif rs > -2:
                strength_score += 3    # In line with market
            elif rs > -5:
                strength_score += 1    # Slightly underperforming

        total_score += min(strength_score, 20)

        # === COMPONENT 4: CONFIRMATION (0-20 pts) ===
        # Volume and breakout proximity
        confirmation_score = 0.0

        # Volume: 0-10 points (gradient — relaxed)
        volume_above_average = False
        if indicators.avg_volume_20 is not None and indicators.avg_volume_20 > 0:
            vol_ratio = current_volume / indicators.avg_volume_20
            if vol_ratio > 1.5:
                confirmation_score += 10   # High volume — strong confirmation
                volume_above_average = True
            elif vol_ratio > 1.2:
                confirmation_score += 8    # Above average
                volume_above_average = True
            elif vol_ratio > 0.8:
                confirmation_score += 5    # Normal volume (not bearish)
            elif vol_ratio > 0.5:
                confirmation_score += 2    # Below average but not dead

        # Breakout proximity (distance to 20-day high): 0-10 points
        if indicators.proximity_to_20d_high is not None:
            prox = indicators.proximity_to_20d_high
            if prox >= 98:
                confirmation_score += 10   # At or near high — breakout!
            elif prox >= 95:
                confirmation_score += 8    # Very close to high
            elif prox >= 92:
                confirmation_score += 6    # Within striking distance
            elif prox >= 88:
                confirmation_score += 4    # Moderate pullback
            elif prox >= 85:
                confirmation_score += 2    # Deeper pullback

        total_score += min(confirmation_score, 20)

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

    def calculate_enhanced_score(
        self,
        current_price: float,
        current_volume: float,
        indicators: TechnicalIndicators,
        prices: np.ndarray,
        volumes: np.ndarray,
    ) -> tuple[int, IndicatorSignals, StageResult, PatternResult]:
        """
        Calculate enhanced score with Stage 2 + Pattern Detection bonus.
        
        This method calls the base calculate_score then adds up to 20 bonus
        points for Stage 2 classification and pattern detection.
        
        Args:
            current_price: Latest closing price
            current_volume: Latest daily volume
            indicators: Calculated technical indicators
            prices: Full price history (for stage/pattern analysis)
            volumes: Full volume history (for pattern analysis)
            
        Returns:
            Tuple of (score, signals, stage_result, pattern_result)
        """
        # Get base score (0-80 max from 4 components of 20 each)
        base_score, signals = self.calculate_score(current_price, current_volume, indicators)
        
        # === COMPONENT 5: STAGE & PATTERN BONUS (0-20 pts) ===
        bonus = 0.0
        
        # Stage 2 classification (0-10 pts)
        stage_result = self.stage_classifier.classify(prices, current_price)
        if stage_result.is_stage_2:
            bonus += 10  # Full Stage 2 bonus
        elif stage_result.checks_passed >= 4:
            bonus += 7   # Almost Stage 2
        elif stage_result.checks_passed >= 3:
            bonus += 4   # Partial Stage 2
        
        # Pattern detection (0-10 pts)
        avg_vol_20 = float(np.mean(volumes[-20:])) if len(volumes) >= 20 else current_volume
        pattern_result = self.pattern_detector.detect_best_pattern(
            prices, volumes, current_price, current_volume, avg_vol_20
        )
        
        if pattern_result.confirmed:
            bonus += 10  # Confirmed breakout pattern
        elif pattern_result.detected and pattern_result.confidence >= 0.6:
            bonus += 7   # High-confidence pattern detected
        elif pattern_result.detected and pattern_result.confidence >= 0.4:
            bonus += 4   # Moderate pattern
        
        # Calculate final enhanced score
        enhanced_score = int(min(round(base_score + bonus), 100))
        
        return enhanced_score, signals, stage_result, pattern_result
