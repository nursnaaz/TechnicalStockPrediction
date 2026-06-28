"""
Backtest API Models

Pydantic models for backtest request and response validation.
"""

from enum import Enum

from pydantic import BaseModel, Field


class BacktestFrequency(str, Enum):
    """Rolling backtest frequency."""

    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SingleBacktestRequest(BaseModel):
    """Request model for a single-date backtest."""

    as_of_date: str = Field(
        ..., description="Historical date to run scan (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    tickers: list[str] = Field(..., min_length=1, description="List of ticker symbols to backtest")
    horizon_days: int = Field(
        default=30, ge=5, le=90, description="Number of trading days to track forward (5-90)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "as_of_date": "2025-01-15",
                "tickers": ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"],
                "horizon_days": 30,
            }
        }


class RollingBacktestRequest(BaseModel):
    """Request model for a rolling (multi-date) backtest."""

    start_date: str = Field(
        ..., description="Start of backtest period (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    end_date: str = Field(
        ..., description="End of backtest period (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    tickers: list[str] = Field(..., min_length=1, description="List of ticker symbols to backtest")
    frequency: BacktestFrequency = Field(
        default=BacktestFrequency.MONTHLY, description="How often to run scans (weekly or monthly)"
    )
    horizon_days: int = Field(
        default=30, ge=5, le=90, description="Number of trading days to track forward (5-90)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2025-01-01",
                "end_date": "2025-06-01",
                "tickers": ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"],
                "frequency": "monthly",
                "horizon_days": 30,
            }
        }


class TradeResult(BaseModel):
    """Individual trade result from backtest."""

    ticker: str = Field(description="Stock ticker symbol")
    entry_price: float = Field(description="Price at time of prediction")
    final_price: float | None = Field(default=None, description="Price at end of horizon")
    score: int = Field(description="Bullish score at prediction time")
    signals: dict | None = Field(default=None, description="Technical signals at prediction")
    days_tracked: int | None = Field(default=None, description="Number of trading days tracked")
    return_pct: float | None = Field(default=None, description="Total return percentage")
    max_gain_pct: float | None = Field(default=None, description="Maximum gain during period")
    max_loss_pct: float | None = Field(default=None, description="Maximum loss during period")
    max_price: float | None = Field(
        default=None, description="Maximum price reached in forward window"
    )
    is_winner: bool | None = Field(default=None, description="Whether trade ended in profit")
    predicted_bullish: bool | None = Field(
        default=None,
        description="True if a BUY: regime tradeable (not bearish) AND score >= regime threshold (65/75)",
    )
    actually_went_up: bool | None = Field(default=None, description="True if max gain >= 5%")
    classification: str | None = Field(
        default=None,
        description="Confusion matrix class: true_positive, false_positive, false_negative, true_negative",
    )
    hit_target_1: bool | None = Field(default=None, description="Hit +10% target")
    hit_target_2: bool | None = Field(default=None, description="Hit +20% target")
    hit_stop: bool | None = Field(default=None, description="Hit -7% stop loss")
    status: str = Field(description="Trade analysis status")


class ScoreBucketMetrics(BaseModel):
    """Metrics for a specific score bucket."""

    count: int = Field(description="Number of trades in bucket")
    win_rate: float = Field(description="Win rate for this bucket")
    avg_return: float = Field(description="Average return for this bucket")


class BacktestMetricsResponse(BaseModel):
    """Aggregate metrics from backtest."""

    total_trades: int = Field(description="Total number of trades analyzed")
    win_count: int | None = Field(default=None, description="Number of winning trades")
    loss_count: int | None = Field(default=None, description="Number of losing trades")
    win_rate: float | None = Field(default=None, description="Win rate (0-1)")
    avg_return: float | None = Field(default=None, description="Average return percentage")
    avg_winner: float | None = Field(default=None, description="Average winner return")
    avg_loser: float | None = Field(default=None, description="Average loser return")
    reward_risk_ratio: float | None = Field(default=None, description="Reward-to-risk ratio")
    expectancy: float | None = Field(default=None, description="Expected return per trade")
    best_trade: float | None = Field(default=None, description="Best single trade return")
    worst_trade: float | None = Field(default=None, description="Worst single trade return")
    target_1_hit_count: int | None = Field(default=None, description="Trades hitting +10%")
    target_1_hit_rate: float | None = Field(default=None, description="Rate of +10% target hits")
    target_2_hit_count: int | None = Field(default=None, description="Trades hitting +20%")
    target_2_hit_rate: float | None = Field(default=None, description="Rate of +20% target hits")
    stop_hit_count: int | None = Field(default=None, description="Trades hitting -7% stop")
    stop_hit_rate: float | None = Field(default=None, description="Rate of -7% stop hits")
    confusion_matrix: dict[str, int] | None = Field(
        default=None, description="TP/FP/FN/TN counts (regime-aware BUY vs max_gain>=5%)"
    )
    accuracy: float | None = Field(default=None, description="(TP+TN)/Total - overall correctness")
    precision: float | None = Field(
        default=None, description="TP/(TP+FP) - when we say bullish, how often correct"
    )
    recall: float | None = Field(
        default=None, description="TP/(TP+FN) - of all actual bullish stocks, how many we caught"
    )
    f1_score: float | None = Field(
        default=None, description="Harmonic mean of precision and recall"
    )
    by_score_bucket: dict[str, ScoreBucketMetrics] | None = Field(
        default=None, description="Metrics broken down by score bucket"
    )
    error: str | None = Field(default=None, description="Error message if metrics failed")


class SingleBacktestResponse(BaseModel):
    """Response for a single-date backtest."""

    backtest_id: str = Field(description="Unique identifier for this backtest")
    status: str = Field(description="Backtest status (completed/error)")
    as_of_date: str = Field(description="Date the scan was run for")
    horizon_days: int | None = Field(default=None, description="Forward-looking horizon")
    scan_id: str | None = Field(default=None, description="Scanner scan_id reference")
    market_regime: str | None = Field(default=None, description="Market regime at scan time")
    total_candidates: int | None = Field(default=None, description="Tickers scanned")
    trades_analyzed: int | None = Field(default=None, description="Trades with forward data")
    metrics: BacktestMetricsResponse | None = Field(default=None, description="Aggregate metrics")
    trades: list[TradeResult] | None = Field(default=None, description="Individual trade results")
    error: str | None = Field(default=None, description="Error message if failed")

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
                    "expectancy": 3.8,
                },
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
    by_date: list[SingleBacktestResponse] = Field(description="Results per scan date")

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
                    "expectancy": 1.5,
                },
            }
        }
