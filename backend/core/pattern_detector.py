"""
Pattern Detector

Detects chart patterns from the Phoenix spec:
- VCP (Volatility Contraction Pattern)
- Flat Base
- Darvas Box
- Tight Flag

Each pattern returns a confidence score (0-1) and pivot price.
Priority on tie: VCP > Darvas > Flat Base > Tight Flag.
"""

import numpy as np
from typing import Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


def clamp01(x: float) -> float:
    """Clamp value between 0 and 1."""
    return max(0.0, min(1.0, x))


@dataclass
class PatternResult:
    """Result of pattern detection."""
    name: str  # "VCP", "Flat Base", "Darvas Box", "Tight Flag", or "None"
    detected: bool
    confirmed: bool
    confidence: float  # 0.0 to 1.0
    pivot: Optional[float]  # Breakout price level
    base_height: Optional[float]  # For target calculation
    details: dict


class PatternDetector:
    """Detects bullish chart patterns."""

    def detect_best_pattern(
        self,
        prices: np.ndarray,
        volumes: np.ndarray,
        current_price: float,
        current_volume: float,
        avg_volume_20: float,
    ) -> PatternResult:
        """
        Detect the best (highest confidence) pattern.
        
        Priority: VCP > Darvas > Flat Base > Tight Flag
        
        Args:
            prices: Array of daily closing prices (at least 120 bars)
            volumes: Array of daily volumes
            current_price: Most recent close
            current_volume: Most recent volume
            avg_volume_20: 20-day average volume
            
        Returns:
            PatternResult for the best detected pattern
        """
        if len(prices) < 30:
            return PatternResult(name="None", detected=False, confirmed=False,
                               confidence=0.0, pivot=None, base_height=None,
                               details={"error": "Insufficient data"})

        # Detect all patterns
        patterns = [
            self._detect_vcp(prices, volumes, current_price, current_volume, avg_volume_20),
            self._detect_darvas(prices, volumes, current_price, current_volume, avg_volume_20),
            self._detect_flat_base(prices, volumes, current_price, current_volume, avg_volume_20),
            self._detect_tight_flag(prices, volumes, current_price, current_volume, avg_volume_20),
        ]

        # Filter to detected patterns with confidence >= 0.4
        valid = [p for p in patterns if p.detected and p.confidence >= 0.4]

        if not valid:
            # Return best attempt even if below threshold
            best_attempt = max(patterns, key=lambda p: p.confidence)
            if best_attempt.confidence > 0:
                return best_attempt
            return PatternResult(name="None", detected=False, confirmed=False,
                               confidence=0.0, pivot=None, base_height=None,
                               details={"patterns_checked": 4, "none_qualified": True})

        # Return highest confidence (priority order already handled by detection order)
        return max(valid, key=lambda p: p.confidence)

    def _detect_vcp(
        self, prices: np.ndarray, volumes: np.ndarray,
        current_price: float, current_volume: float, avg_volume_20: float
    ) -> PatternResult:
        """
        Detect Volatility Contraction Pattern.
        
        VCP: >= 30 bars, up to 3 contractions, each >= 10% deep,
        each <= 50% the depth of the prior.
        Confirmed when close > pivot AND volume >= 2.0x avg_volume_20.
        """
        if len(prices) < 30:
            return PatternResult(name="VCP", detected=False, confirmed=False,
                               confidence=0.0, pivot=None, base_height=None, details={})

        # Look at last 120 bars (or available)
        lookback = min(120, len(prices))
        window = prices[-lookback:]
        vol_window = volumes[-lookback:]

        # Find swing highs and lows to identify contractions
        contractions = []
        i = 0
        while i < len(window) - 10:
            # Find local high
            seg = window[i:min(i+30, len(window))]
            if len(seg) < 10:
                break
            high_idx = np.argmax(seg)
            high_val = seg[high_idx]
            
            # Find subsequent low
            remaining = window[i+high_idx:min(i+high_idx+30, len(window))]
            if len(remaining) < 5:
                break
            low_idx = np.argmin(remaining)
            low_val = remaining[low_idx]
            
            # Calculate depth
            if high_val > 0:
                depth_pct = ((high_val - low_val) / high_val) * 100
                if depth_pct >= 10:
                    contractions.append({
                        "depth_pct": depth_pct,
                        "high": high_val,
                        "low": low_val,
                        "bar_idx": i + high_idx
                    })
            
            i += high_idx + low_idx + 5  # Move past this contraction
            if len(contractions) >= 3:
                break

        if len(contractions) < 1:
            return PatternResult(name="VCP", detected=False, confirmed=False,
                               confidence=0.0, pivot=None, base_height=None,
                               details={"contractions_found": 0})

        # Check contraction quality (each <= 50% of prior)
        valid_contractions = [contractions[0]]
        for j in range(1, len(contractions)):
            if contractions[j]["depth_pct"] <= contractions[j-1]["depth_pct"] * 0.5:
                valid_contractions.append(contractions[j])
            elif contractions[j]["depth_pct"] < contractions[j-1]["depth_pct"]:
                valid_contractions.append(contractions[j])

        num_contractions = len(valid_contractions)
        
        # Pivot = most recent recovery high
        pivot = float(np.max(window[-20:]))
        base_height = float(pivot - np.min(window[-30:]))

        # Volume decline quality
        if len(vol_window) >= 40:
            first_half_vol = float(np.mean(vol_window[:len(vol_window)//2]))
            second_half_vol = float(np.mean(vol_window[len(vol_window)//2:]))
            vol_decline = clamp01(1 - (second_half_vol / first_half_vol)) if first_half_vol > 0 else 0
        else:
            vol_decline = 0.3

        # Recency factor
        if contractions:
            bars_since = lookback - contractions[-1]["bar_idx"]
            recency = clamp01(1 - (bars_since / 30))
        else:
            recency = 0

        # Confidence calculation
        confidence = clamp01(
            0.40 * (num_contractions / 3) +
            0.30 * vol_decline +
            0.30 * recency
        )

        # Confirmed if close > pivot AND volume >= 2.0x
        confirmed = (current_price > pivot) and (current_volume >= 2.0 * avg_volume_20)
        detected = num_contractions >= 1 and confidence >= 0.3

        return PatternResult(
            name="VCP",
            detected=detected,
            confirmed=confirmed,
            confidence=confidence,
            pivot=round(pivot, 2),
            base_height=round(base_height, 2),
            details={
                "contractions": num_contractions,
                "volume_decline_quality": round(vol_decline, 3),
                "recency_factor": round(recency, 3),
            }
        )

    def _detect_flat_base(
        self, prices: np.ndarray, volumes: np.ndarray,
        current_price: float, current_volume: float, avg_volume_20: float
    ) -> PatternResult:
        """
        Detect Flat Base pattern.
        
        20-120 bar sideways range, high-low range <= 15% of midpoint,
        volume in second half lower than first half.
        Confirmed when close > base_top AND volume >= 1.5x avg.
        """
        # Try different base lengths
        best_confidence = 0.0
        best_result = None

        for base_len in [60, 45, 30, 20, 80, 100]:
            if len(prices) < base_len:
                continue
            
            base = prices[-base_len:]
            base_vol = volumes[-base_len:]
            
            base_high = float(np.max(base))
            base_low = float(np.min(base))
            midpoint = (base_high + base_low) / 2
            
            if midpoint == 0:
                continue
            
            range_pct = (base_high - base_low) / midpoint
            
            # Must be <= 15% range
            if range_pct > 0.15:
                continue
            
            # Volume dryup: second half volume < first half
            half = base_len // 2
            first_half_vol = float(np.mean(base_vol[:half]))
            second_half_vol = float(np.mean(base_vol[half:]))
            
            if first_half_vol == 0:
                continue
            
            vol_dryup = clamp01(1 - (second_half_vol / first_half_vol))
            tightness = clamp01(1 - (range_pct / 0.15))
            duration_factor = min(base_len, 60) / 60
            
            confidence = clamp01(
                0.50 * tightness +
                0.30 * vol_dryup +
                0.20 * duration_factor
            )
            
            if confidence > best_confidence:
                best_confidence = confidence
                pivot = base_high
                confirmed = (current_price > base_high) and (current_volume >= 1.5 * avg_volume_20)
                best_result = PatternResult(
                    name="Flat Base",
                    detected=confidence >= 0.3,
                    confirmed=confirmed,
                    confidence=confidence,
                    pivot=round(pivot, 2),
                    base_height=round(base_high - base_low, 2),
                    details={
                        "base_length": base_len,
                        "range_pct": round(range_pct * 100, 1),
                        "tightness": round(tightness, 3),
                        "volume_dryup": round(vol_dryup, 3),
                    }
                )

        if best_result:
            return best_result

        return PatternResult(name="Flat Base", detected=False, confirmed=False,
                           confidence=0.0, pivot=None, base_height=None,
                           details={"no_flat_base_found": True})

    def _detect_darvas(
        self, prices: np.ndarray, volumes: np.ndarray,
        current_price: float, current_volume: float, avg_volume_20: float
    ) -> PatternResult:
        """
        Detect Darvas Box pattern.
        
        Prior 8% advance into the box; box length 3-40 bars, depth 1-15%.
        Confirmed when close > box_top AND volume >= 1.5x box_avg_volume.
        """
        if len(prices) < 50:
            return PatternResult(name="Darvas Box", detected=False, confirmed=False,
                               confidence=0.0, pivot=None, base_height=None, details={})

        # Look for a box in the last 40 bars
        for box_len in [20, 15, 10, 25, 30, 35, 40]:
            if len(prices) < box_len + 15:
                continue
            
            box = prices[-box_len:]
            box_vol = volumes[-box_len:]
            pre_box = prices[-(box_len + 15):-box_len]
            
            box_top = float(np.max(box))
            box_bottom = float(np.min(box))
            
            if box_top == 0:
                continue
            
            box_depth = (box_top - box_bottom) / box_top * 100
            
            # Box depth must be 1-15%
            if not (1 <= box_depth <= 15):
                continue
            
            # Must have prior advance of >= 8% into the box
            pre_low = float(np.min(pre_box))
            if pre_low == 0:
                continue
            advance_pct = (box_top - pre_low) / pre_low * 100
            
            if advance_pct < 8:
                continue
            
            # Volume decline in box
            if len(box_vol) > 5:
                first_vol = float(np.mean(box_vol[:len(box_vol)//2]))
                second_vol = float(np.mean(box_vol[len(box_vol)//2:]))
                vol_decline = clamp01(1 - (second_vol / first_vol)) if first_vol > 0 else 0
            else:
                vol_decline = 0.3
            
            # Confidence
            depth_factor = clamp01(1 - box_depth / 15)
            confidence = clamp01(0.50 * depth_factor + 0.50 * vol_decline)
            
            if confidence >= 0.3:
                box_avg_vol = float(np.mean(box_vol))
                confirmed = (current_price > box_top) and (current_volume >= 1.5 * box_avg_vol)
                
                return PatternResult(
                    name="Darvas Box",
                    detected=True,
                    confirmed=confirmed,
                    confidence=confidence,
                    pivot=round(box_top, 2),
                    base_height=round(box_top - box_bottom, 2),
                    details={
                        "box_length": box_len,
                        "box_depth_pct": round(box_depth, 1),
                        "prior_advance_pct": round(advance_pct, 1),
                        "volume_decline": round(vol_decline, 3),
                    }
                )

        return PatternResult(name="Darvas Box", detected=False, confirmed=False,
                           confidence=0.0, pivot=None, base_height=None,
                           details={"no_darvas_box_found": True})

    def _detect_tight_flag(
        self, prices: np.ndarray, volumes: np.ndarray,
        current_price: float, current_volume: float, avg_volume_20: float
    ) -> PatternResult:
        """
        Detect Tight Flag pattern.
        
        Flagpole >= 8% within last 15 bars; flag retraces <= 50% of pole;
        flag body <= 20 bars.
        Confirmed when close > flag_high on volume >= 1.5x avg.
        """
        if len(prices) < 20:
            return PatternResult(name="Tight Flag", detected=False, confirmed=False,
                               confidence=0.0, pivot=None, base_height=None, details={})

        # Look for a flagpole (strong advance) followed by consolidation
        for pole_end in range(len(prices) - 5, max(len(prices) - 25, 14), -1):
            # Check for pole: 8%+ gain in preceding 15 bars
            pole_start = max(0, pole_end - 15)
            pole_low = float(np.min(prices[pole_start:pole_end]))
            pole_high = float(np.max(prices[pole_start:pole_end+1]))
            
            if pole_low == 0:
                continue
            
            pole_pct = (pole_high - pole_low) / pole_low * 100
            
            if pole_pct < 8:
                continue
            
            # Flag = bars after pole_end
            flag = prices[pole_end:]
            if len(flag) < 3 or len(flag) > 20:
                continue
            
            flag_high = float(np.max(flag))
            flag_low = float(np.min(flag))
            
            # Flag must retrace <= 50% of pole
            pole_height = pole_high - pole_low
            retrace = pole_high - flag_low
            retrace_pct = retrace / pole_height if pole_height > 0 else 1.0
            
            if retrace_pct > 0.50:
                continue
            
            # Confidence calculation
            pole_strength = clamp01(min(pole_pct, 25) / 25)
            retrace_quality = clamp01(1 - retrace_pct / 0.50)
            flag_compactness = clamp01(1 - len(flag) / 20)
            
            confidence = clamp01(
                0.40 * pole_strength +
                0.30 * retrace_quality +
                0.30 * flag_compactness
            )
            
            if confidence >= 0.3:
                pivot = flag_high
                confirmed = (current_price > flag_high) and (current_volume >= 1.5 * avg_volume_20)
                
                return PatternResult(
                    name="Tight Flag",
                    detected=True,
                    confirmed=confirmed,
                    confidence=confidence,
                    pivot=round(pivot, 2),
                    base_height=round(pole_height, 2),
                    details={
                        "pole_pct": round(pole_pct, 1),
                        "retrace_pct": round(retrace_pct * 100, 1),
                        "flag_bars": len(flag),
                        "pole_strength": round(pole_strength, 3),
                    }
                )

        return PatternResult(name="Tight Flag", detected=False, confirmed=False,
                           confidence=0.0, pivot=None, base_height=None,
                           details={"no_tight_flag_found": True})
