"""
API Models

Pydantic models for API request and response validation.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime


class ScanRequest(BaseModel):
    """Request model for initiating a scan."""
    tickers: List[str] = Field(
        ..., 
        min_length=1, 
        description="List of ticker symbols to analyze"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "tickers": ["AAPL", "MSFT", "GOOGL"]
            }
        }


class MarketRegime(str, Enum):
    """Market regime classification."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class IndicatorSignals(BaseModel):
    """Individual indicator signals contributing to score."""
    price_above_sma50: bool = Field(description="Current price above 50-day SMA")
    price_above_ema20: bool = Field(description="Current price above 20-day EMA")
    macd_above_signal: bool = Field(description="MACD line above signal line")
    macd_histogram_positive: bool = Field(description="MACD histogram is positive")
    volume_above_average: bool = Field(description="Volume 20% above 20-day average")
    relative_strength_positive: bool = Field(description="Relative strength vs market is positive")

    class Config:
        json_schema_extra = {
            "example": {
                "price_above_sma50": True,
                "price_above_ema20": True,
                "macd_above_signal": True,
                "macd_histogram_positive": True,
                "volume_above_average": False,
                "relative_strength_positive": True
            }
        }


class TickerScore(BaseModel):
    """Scored ticker with details."""
    ticker: str = Field(description="Stock ticker symbol")
    bullish_score: int = Field(ge=0, le=100, description="Bullish score (0-100)")
    signals: IndicatorSignals = Field(description="Individual indicator signals")
    current_price: float = Field(description="Current stock price")
    indicators: Dict[str, Optional[float]] = Field(description="Raw indicator values")

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "bullish_score": 85,
                "signals": {
                    "price_above_sma50": True,
                    "price_above_ema20": True,
                    "macd_above_signal": True,
                    "macd_histogram_positive": True,
                    "volume_above_average": False,
                    "relative_strength_positive": True
                },
                "current_price": 178.50,
                "indicators": {
                    "sma_50": 175.20,
                    "ema_20": 177.80,
                    "macd_line": 1.25,
                    "macd_signal": 0.95,
                    "macd_histogram": 0.30,
                    "avg_volume_20": 52000000.0,
                    "relative_strength": 2.5
                }
            }
        }


class ScanMetadata(BaseModel):
    """Metadata about the scan execution."""
    timestamp: datetime = Field(description="Scan execution timestamp")
    ticker_count: int = Field(description="Number of tickers analyzed")
    duration_seconds: float = Field(description="Scan duration in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2024-01-15T10:30:00Z",
                "ticker_count": 3,
                "duration_seconds": 2.5
            }
        }


class ScanResponse(BaseModel):
    """Complete scan results."""
    scan_id: str = Field(description="Unique identifier for this scan")
    market_regime: MarketRegime = Field(description="Current market regime")
    ranked_tickers: List[TickerScore] = Field(description="Tickers ranked by bullish score")
    metadata: ScanMetadata = Field(description="Scan execution metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "market_regime": "bullish",
                "ranked_tickers": [
                    {
                        "ticker": "AAPL",
                        "bullish_score": 85,
                        "signals": {
                            "price_above_sma50": True,
                            "price_above_ema20": True,
                            "macd_above_signal": True,
                            "macd_histogram_positive": True,
                            "volume_above_average": False,
                            "relative_strength_positive": True
                        },
                        "current_price": 178.50,
                        "indicators": {
                            "sma_50": 175.20,
                            "ema_20": 177.80,
                            "macd_line": 1.25,
                            "macd_signal": 0.95,
                            "macd_histogram": 0.30,
                            "avg_volume_20": 52000000.0,
                            "relative_strength": 2.5
                        }
                    }
                ],
                "metadata": {
                    "timestamp": "2024-01-15T10:30:00Z",
                    "ticker_count": 3,
                    "duration_seconds": 2.5
                }
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(description="Service health status")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy"
            }
        }
