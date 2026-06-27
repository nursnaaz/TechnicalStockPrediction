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
