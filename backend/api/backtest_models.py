"""
Backtest API Models

Pydantic models for backtest request and response validation.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum


class BacktestFrequency(str, Enum):
    """Rolling backtest frequency."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SingleBacktestRequest(BaseModel):
    """Request model for a single-date backtest."""
    as_of_date: str = Field(
        ...,
        description="Historical date to run scan (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    tickers: List[str] = Field(
        ...,
        min_length=1,
        description="List of ticker symbols to backtest"
    )
    horizon_days: int = Field(
        default=30,
        ge=5,
        le=90,
        description="Number of trading days to track forward (5-90)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "as_of_date": "2025-01-15",
                "tickers": ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"],
                "horizon_days": 30
            }
        }


class RollingBacktestRequest(BaseModel):
    """Request model for a rolling (multi-date) backtest."""
    start_date: str = Field(
        ...,
        description="Start of backtest period (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    end_date: str = Field(
        ...,
        description="End of backtest period (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    tickers: List[str] = Field(
        ...,
        min_length=1,
        description="List of ticker symbols to backtest"
    )
    frequency: BacktestFrequency = Field(
        default=BacktestFrequency.MONTHLY,
        description="How often to run scans (weekly or monthly)"
    )
    horizon_days: int = Field(
        default=30,
        ge=5,
        le=90,
        description="Number of trading days to track forward (5-90)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2025-01-01",
                "end_date": "2025-06-01",
                "tickers": ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"],
                "frequency": "monthly",
                "horizon_days": 30
            }
        }


class TradeResult(BaseModel):
    """Individual trade result from backtest."""
    ticker: str = Field(description="Stock ticker symbol")
    entry_price: float = Field(description="Price at time of prediction")
    final_price: Optional[float] = Field(default=None, description="Price at end of horizon")
    score: int = Field(description="Bullish score at prediction time")
    signals: Optional[Dict] = Field(default=None, description="Technical signals at prediction")
    days_tracked: Optional[int] = Field(default=None, description="Number of trading days tracked")
    return_pct: Optional[float] = Field(default=None, description="Total return percentage")
    max_gain_pct: Optional[float] = Field(default=None, description="Maximum gain during period")
    max_loss_pct: Optional[float] = Field(default=None, description="Maximum loss during period")
    max_price: Optional[float] = Field(default=None, description="Maximum price reached in forward window")
    is_winner: Optional[bool] = Field(default=None, description="Whether trade ended in profit")
    predicted_bullish: Optional[bool] = Field(default=None, description="True if score >= 70")
    actually_went_up: Optional[bool] = Field(default=None, description="True if max gain >= 5%")
    classification: Optional[str] = Field(default=None, description="Confusion matrix class: true_positive, false_positive, false_negative, true_negative")
    hit_target_1: Optional[bool] = Field(default=None, description="Hit +10% target")
    hit_target_2: Optional[bool] = Field(default=None, description="Hit +20% target")
    hit_stop: Optional[bool] = Field(default=None, description="Hit -7% stop loss")
    status: str = Field(description="Trade analysis status")


class ScoreBucketMetrics(BaseModel):
    """Metrics for a specific score bucket."""
    count: int = Field(description="Number of trades in bucket")
    win_rate: float = Field(description="Win rate for this bucket")
    avg_return: float = Field(description="Average return for this bucket")


class BacktestMetricsResponse(BaseModel):
    """Aggregate metrics from backtest."""
    total_trades: int = Field(description="Total number of trades analyzed")
    win_count: Optional[int] = Field(default=None, description="Number of winning trades")
    loss_count: Optional[int] = Field(default=None, description="Number of losing trades")
    win_rate: Optional[float] = Field(default=None, description="Win rate (0-1)")
    avg_return: Optional[float] = Field(default=None, description="Average return percentage")
    avg_winner: Optional[float] = Field(default=None, description="Average winner return")
    avg_loser: Optional[float] = Field(default=None, description="Average loser return")
    reward_risk_ratio: Optional[float] = Field(default=None, description="Reward-to-risk ratio")
    expectancy: Optional[float] = Field(default=None, description="Expected return per trade")
    best_trade: Optional[float] = Field(default=None, description="Best single trade return")
    worst_trade: Optional[float] = Field(default=None, description="Worst single trade return")
    target_1_hit_count: Optional[int] = Field(default=None, description="Trades hitting +10%")
    target_1_hit_rate: Optional[float] = Field(default=None, description="Rate of +10% target hits")
    target_2_hit_count: Optional[int] = Field(default=None, description="Trades hitting +20%")
    target_2_hit_rate: Optional[float] = Field(default=None, description="Rate of +20% target hits")
    stop_hit_count: Optional[int] = Field(default=None, description="Trades hitting -7% stop")
    stop_hit_rate: Optional[float] = Field(default=None, description="Rate of -7% stop hits")
    confusion_matrix: Optional[Dict[str, int]] = Field(default=None, description="TP/FP/FN/TN counts (score>=70 vs max_gain>=5%)")
    accuracy: Optional[float] = Field(default=None, description="(TP+TN)/Total - overall correctness")
    precision: Optional[float] = Field(default=None, description="TP/(TP+FP) - when we say bullish, how often correct")
    recall: Optional[float] = Field(default=None, description="TP/(TP+FN) - of all actual bullish stocks, how many we caught")
    f1_score: Optional[float] = Field(default=None, description="Harmonic mean of precision and recall")
    by_score_bucket: Optional[Dict[str, ScoreBucketMetrics]] = Field(
        default=None, description="Metrics broken down by score bucket"
    )
    error: Optional[str] = Field(default=None, description="Error message if metrics failed")


class SingleBacktestResponse(BaseModel):
    """Response for a single-date backtest."""
    backtest_id: str = Field(description="Unique identifier for this backtest")
    status: str = Field(description="Backtest status (completed/error)")
    as_of_date: str = Field(description="Date the scan was run for")
    horizon_days: Optional[int] = Field(default=None, description="Forward-looking horizon")
    scan_id: Optional[str] = Field(default=None, description="Scanner scan_id reference")
    market_regime: Optional[str] = Field(default=None, description="Market regime at scan time")
    total_candidates: Optional[int] = Field(default=None, description="Tickers scanned")
    trades_analyzed: Optional[int] = Field(default=None, description="Trades with forward data")
    metrics: Optional[BacktestMetricsResponse] = Field(default=None, description="Aggregate metrics")
    trades: Optional[List[TradeResult]] = Field(default=None, description="Individual trade results")
    error: Optional[str] = Field(default=None, description="Error message if failed")

    class Config:
        json_schema_extra = {
            "example": {
                "backtest_id": "bt-a1b2c3d4",
                "status": "completed",
                "as_of_date": "2025-01-15",
                "horizon_days": 30,
                "market_regime": "bullish",
                "total_candidates": 5,
                "trades_analyzed": 4,
                "metrics": {
                    "total_trades": 4,
                    "win_count": 3,
                    "loss_count": 1,
                    "win_rate": 0.75,
                    "avg_return": 5.2,
                    "expectancy": 3.8
                }
            }
        }


class RollingBacktestResponse(BaseModel):
    """Response for a rolling backtest."""
    backtest_type: str = Field(default="rolling", description="Type of backtest")
    start_date: str = Field(description="Start of backtest period")
    end_date: str = Field(description="End of backtest period")
    frequency: str = Field(description="Scan frequency used")
    horizon_days: int = Field(description="Forward-looking horizon")
    total_scan_dates: int = Field(description="Number of scan dates tested")
    total_trades: int = Field(description="Total number of trades across all dates")
    overall_metrics: BacktestMetricsResponse = Field(description="Aggregated metrics")
    by_date: List[SingleBacktestResponse] = Field(description="Results per scan date")

    class Config:
        json_schema_extra = {
            "example": {
                "backtest_type": "rolling",
                "start_date": "2025-01-01",
                "end_date": "2025-06-01",
                "frequency": "monthly",
                "horizon_days": 30,
                "total_scan_dates": 6,
                "total_trades": 25,
                "overall_metrics": {
                    "total_trades": 25,
                    "win_rate": 0.52,
                    "avg_return": 2.1,
                    "expectancy": 1.5
                }
            }
        }
