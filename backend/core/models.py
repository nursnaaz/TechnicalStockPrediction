"""
Internal Data Models

Data classes for internal use by core components.
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class StockData:
    """Raw stock data from API."""
    ticker: str
    prices: np.ndarray  # Close prices
    volumes: np.ndarray
    timestamps: np.ndarray


@dataclass
class TechnicalIndicators:
    """Calculated technical indicators."""
    sma_50: Optional[float] = None
    sma_150: Optional[float] = None          # V3: Minervini hard filter H3
    sma_200: Optional[float] = None          # V3: Minervini hard filters H1/H4
    sma_200_slope: Optional[float] = None    # V3: H2 (rising 200-day SMA over last 20 bars)
    week52_high: Optional[float] = None       # V3: H6 (within 25% of 52-week high)
    week52_low: Optional[float] = None        # V3: H5 (30% above 52-week low)
    ema_20: Optional[float] = None
    ema_9: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    avg_volume_20: Optional[float] = None
    relative_strength: Optional[float] = None
    rsi_14: Optional[float] = None
    roc_10: Optional[float] = None
    proximity_to_20d_high: Optional[float] = None
