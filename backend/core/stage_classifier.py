"""
Stage 2 Classifier

Identifies stocks in Mark Minervini's Stage 2 institutional uptrend.
Stage 2 is the optimal phase for buying breakouts.

Stage 2 requires ALL:
- close > SMA50 > SMA200
- SMA50 slope > +0.3% (rising over 21 bars)
- SMA200 slope >= 0% (not falling)
- close >= 1.30 × 52-week low (at least 30% above low)
- close >= 0.75 × 52-week high (within 25% of high)
"""

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StageResult:
    """Result of stage classification."""

    stage: int  # 1, 2, 3, or 4
    is_stage_2: bool
    checks_passed: int  # out of 5
    details: dict


class StageClassifier:
    """Classifies stock into Minervini's 4 stages."""

    def classify(
        self,
        prices: np.ndarray,
        current_price: float,
    ) -> StageResult:
        """
        Classify the stock's current stage.

        Args:
            prices: Historical closing prices (at least 252 bars)
            current_price: Most recent close

        Returns:
            StageResult with stage number and details
        """
        details = {}
        checks_passed = 0

        # Need at least 252 bars for 52-week analysis
        if len(prices) < 252:
            return StageResult(
                stage=0,
                is_stage_2=False,
                checks_passed=0,
                details={"error": "Insufficient data (need 252 bars)"},
            )

        # Calculate SMAs
        sma_50 = float(np.mean(prices[-50:]))
        sma_200 = float(np.mean(prices[-200:]))

        # Calculate 52-week high and low
        high_52w = float(np.max(prices[-252:]))
        low_52w = float(np.min(prices[-252:]))

        # Check 1: close > SMA50 > SMA200
        ma_order = current_price > sma_50 > sma_200
        details["close_above_sma50_above_sma200"] = ma_order
        if ma_order:
            checks_passed += 1

        # Check 2: SMA50 slope > +0.3% over 21 bars
        if len(prices) >= 71:  # Need 50 + 21 extra bars
            sma_50_21_ago = float(np.mean(prices[-71:-21]))
            sma_50_slope = ((sma_50 - sma_50_21_ago) / sma_50_21_ago) * 100
            details["sma50_slope_pct"] = round(sma_50_slope, 3)
            details["sma50_rising"] = sma_50_slope > 0.3
            if sma_50_slope > 0.3:
                checks_passed += 1
        else:
            details["sma50_rising"] = False

        # Check 3: SMA200 slope >= 0% over 21 bars
        if len(prices) >= 221:
            sma_200_21_ago = float(np.mean(prices[-221:-21]))
            sma_200_slope = ((sma_200 - sma_200_21_ago) / sma_200_21_ago) * 100
            details["sma200_slope_pct"] = round(sma_200_slope, 3)
            details["sma200_not_falling"] = sma_200_slope >= 0
            if sma_200_slope >= 0:
                checks_passed += 1
        else:
            details["sma200_not_falling"] = False

        # Check 4: close >= 1.30 × 52-week low (30% above low)
        pct_above_low = ((current_price - low_52w) / low_52w) * 100 if low_52w > 0 else 0
        details["pct_above_52w_low"] = round(pct_above_low, 1)
        details["above_30pct_from_low"] = pct_above_low >= 30
        if pct_above_low >= 30:
            checks_passed += 1

        # Check 5: close >= 0.75 × 52-week high (within 25% of high)
        pct_from_high = ((high_52w - current_price) / high_52w) * 100 if high_52w > 0 else 100
        details["pct_below_52w_high"] = round(pct_from_high, 1)
        details["within_25pct_of_high"] = pct_from_high <= 25
        if pct_from_high <= 25:
            checks_passed += 1

        # Stage 2 requires ALL 5 checks
        is_stage_2 = checks_passed == 5

        # Determine stage
        if is_stage_2:
            stage = 2
        elif current_price < sma_200:
            stage = 4  # Below 200-day = Stage 4 (decline)
        elif current_price < sma_50:
            stage = 1  # Below 50-day but above 200 = Stage 1 (basing)
        else:
            stage = 3  # Above both but not meeting all Stage 2 criteria = Stage 3 (topping)

        details["sma_50"] = round(sma_50, 2)
        details["sma_200"] = round(sma_200, 2)
        details["high_52w"] = round(high_52w, 2)
        details["low_52w"] = round(low_52w, 2)

        return StageResult(
            stage=stage, is_stage_2=is_stage_2, checks_passed=checks_passed, details=details
        )
