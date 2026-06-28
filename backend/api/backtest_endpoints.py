"""
Backtest API Endpoints

REST API routes for backtesting scanner predictions against historical data.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from api.backtest_models import (
    RollingBacktestRequest,
    RollingBacktestResponse,
    SingleBacktestRequest,
    SingleBacktestResponse,
)
from backtest.engine import BacktestEngine
from config import config
from core.api_client import RestApiClient
from core.indicator_calculator import IndicatorCalculator
from core.orchestrator import ScanOrchestrator
from core.ranking_service import RankingService
from core.regime_analyzer import MarketRegimeAnalyzer
from core.scoring_engine import ScoringEngine
from core.universe_builder import UniverseBuilder
from utils.logging import get_logger

logger = get_logger(__name__)
backtest_router = APIRouter(prefix="/backtest", tags=["backtest"])


def _create_backtest_engine() -> BacktestEngine:
    """
    Create a BacktestEngine with all required dependencies.

    Returns:
        Configured BacktestEngine instance
    """
    api_client = RestApiClient(
        api_key=config.POLYGON_TOKEN,
        base_url=config.API_BASE_URL,
        max_concurrent=config.MAX_CONCURRENT_REQUESTS,
        max_retries=config.MAX_RETRIES,
    )

    orchestrator = ScanOrchestrator(
        api_client=api_client,
        universe_builder=UniverseBuilder(),
        regime_analyzer=MarketRegimeAnalyzer(api_client),
        indicator_calc=IndicatorCalculator(),
        scoring_engine=ScoringEngine(),
        ranking_service=RankingService(),
    )

    return BacktestEngine(api_client=api_client, orchestrator=orchestrator)


def _validate_date(date_str: str, field_name: str) -> None:
    """Validate date string format and reasonableness."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format. Use YYYY-MM-DD.",
        )

    # Don't allow future dates
    if dt.date() > datetime.now().date():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field_name} cannot be in the future."
        )

    # Don't allow dates too far in the past (polygon free tier limits)
    min_date = datetime(2020, 1, 1)
    if dt < min_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be after 2020-01-01.",
        )


@backtest_router.post(
    "/single",
    response_model=SingleBacktestResponse,
    summary="Run single-date backtest",
    description=(
        "Run the scanner as of a historical date and measure how predictions "
        "performed over the following period. This tells you: 'If the scanner "
        "said bullish on date X, did the stock actually go up?'"
    ),
)
async def run_single_backtest(request: SingleBacktestRequest):
    """
    Execute a single-date backtest.

    Runs the full scanner pipeline for a historical date, then checks
    actual price movement over the specified horizon to validate predictions.

    Args:
        request: SingleBacktestRequest with date, tickers, and horizon

    Returns:
        SingleBacktestResponse with trade results and aggregate metrics
    """
    logger.info(
        f"Single backtest requested: date={request.as_of_date}, "
        f"tickers={len(request.tickers)}, horizon={request.horizon_days}d"
    )

    # Validate date
    _validate_date(request.as_of_date, "as_of_date")

    # Ensure horizon doesn't extend past today
    as_of_dt = datetime.strptime(request.as_of_date, "%Y-%m-%d")
    days_since = (datetime.now() - as_of_dt).days
    if days_since < request.horizon_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Not enough time has passed. as_of_date is {days_since} days ago "
                f"but horizon requires {request.horizon_days} days of forward data. "
                f"Choose an earlier date or shorter horizon."
            ),
        )

    try:
        engine = _create_backtest_engine()
        result = await engine.run_single_date_backtest(
            as_of_date=request.as_of_date,
            tickers=request.tickers,
            horizon_days=request.horizon_days,
        )

        return result

    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Backtest failed: {e!s}"
        )


@backtest_router.post(
    "/rolling",
    response_model=RollingBacktestResponse,
    summary="Run rolling backtest over date range",
    description=(
        "Run backtests at regular intervals (weekly/monthly) over a date range. "
        "This provides a comprehensive view of scanner accuracy across different "
        "market conditions over time."
    ),
)
async def run_rolling_backtest(request: RollingBacktestRequest):
    """
    Execute a rolling backtest over a date range.

    Runs the scanner at regular intervals and tracks forward performance
    for each scan date. Aggregates results for overall accuracy measurement.

    Args:
        request: RollingBacktestRequest with date range, frequency, tickers

    Returns:
        RollingBacktestResponse with per-date and aggregate results
    """
    logger.info(
        f"Rolling backtest requested: {request.start_date} to {request.end_date}, "
        f"frequency={request.frequency}, tickers={len(request.tickers)}"
    )

    # Validate dates
    _validate_date(request.start_date, "start_date")
    _validate_date(request.end_date, "end_date")

    # Ensure start < end
    start_dt = datetime.strptime(request.start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(request.end_date, "%Y-%m-%d")

    if start_dt >= end_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="start_date must be before end_date."
        )

    # Ensure enough forward data for last scan date
    days_since_end = (datetime.now() - end_dt).days
    if days_since_end < request.horizon_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Not enough time has passed since end_date. "
                f"end_date is {days_since_end} days ago but horizon requires "
                f"{request.horizon_days} days. Choose an earlier end_date."
            ),
        )

    try:
        engine = _create_backtest_engine()
        result = await engine.run_rolling_backtest(
            start_date=request.start_date,
            end_date=request.end_date,
            tickers=request.tickers,
            frequency=request.frequency.value,
            horizon_days=request.horizon_days,
        )

        return result

    except Exception as e:
        logger.error(f"Rolling backtest failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rolling backtest failed: {e!s}",
        )
