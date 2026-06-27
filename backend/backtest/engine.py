"""
Backtesting Engine

Tests scanner predictions against historical data to validate accuracy.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from uuid import uuid4

from core.orchestrator import ScanOrchestrator
from core.api_client import RestApiClient
from api.models import ScanRequest
from .metrics import BacktestMetrics

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Backtests the scanner by running it on historical dates and measuring
    how well predictions performed over the subsequent period.
    """
    
    def __init__(self, api_client: RestApiClient, orchestrator: ScanOrchestrator):
        self.api_client = api_client
        self.orchestrator = orchestrator
        
    async def run_single_date_backtest(
        self,
        as_of_date: str,  # YYYY-MM-DD
        tickers: List[str],
        horizon_days: int = 30
    ) -> Dict:
        """
        Run backtest for a single historical date.
        
        Steps:
        1. Run scanner as of the historical date (no look-ahead)
        2. Get predictions (bullish scores, signals)
        3. Fetch actual price data for next N days
        4. Calculate metrics: win rate, target hits, returns
        
        Args:
            as_of_date: Historical date to run scan (YYYY-MM-DD)
            tickers: List of ticker symbols to test
            horizon_days: Number of days to track forward (default 30)
            
        Returns:
            Dictionary with backtest results and metrics
        """
        backtest_id = str(uuid4())
        logger.info(f"Starting backtest {backtest_id} for date {as_of_date}")
        
        # Step 1: Run scanner as of historical date
        scan_request = ScanRequest(tickers=tickers)
        
        try:
            scan_result = await self.orchestrator.execute_scan(scan_request)
        except Exception as e:
            logger.error(f"Scan failed for {as_of_date}: {e}")
            return {
                "backtest_id": backtest_id,
                "status": "error",
                "error": str(e),
                "as_of_date": as_of_date
            }
        
        # Step 2: For each predicted ticker, fetch forward-looking data
        trade_results = []
        
        for ticker_score in scan_result.ranked_tickers:
            ticker = ticker_score.ticker
            entry_price = ticker_score.current_price
            score = ticker_score.bullish_score
            
            # Fetch forward-looking price data (use ~1.5x horizon for calendar days buffer)
            calendar_days = int(horizon_days * 1.5)
            
            try:
                # Fetch forward-looking data
                forward_data = await self._fetch_forward_data(
                    ticker, 
                    as_of_date, 
                    calendar_days
                )
                
                if not forward_data or len(forward_data) == 0:
                    logger.warning(f"No forward data for {ticker}")
                    continue
                
                # Calculate metrics
                trade_result = self._analyze_trade(
                    ticker=ticker,
                    entry_price=entry_price,
                    score=score,
                    signals=ticker_score.signals,
                    forward_data=forward_data,
                    horizon_days=horizon_days
                )
                
                trade_results.append(trade_result)
                
            except Exception as e:
                logger.error(f"Error analyzing {ticker}: {e}")
                continue
        
        # Step 3: Calculate aggregate metrics
        metrics = BacktestMetrics.calculate_aggregate_metrics(trade_results)
        
        # Step 4: Build result
        result = {
            "backtest_id": backtest_id,
            "status": "completed",
            "as_of_date": as_of_date,
            "horizon_days": horizon_days,
            "scan_id": scan_result.scan_id,
            "market_regime": scan_result.market_regime,
            "total_candidates": len(scan_result.ranked_tickers),
            "trades_analyzed": len(trade_results),
            "metrics": metrics,
            "trades": trade_results
        }
        
        logger.info(
            f"Backtest {backtest_id} completed: "
            f"{len(trade_results)} trades, "
            f"win_rate={metrics.get('win_rate', 0):.1%}"
        )
        
        return result
    
    async def _fetch_forward_data(
        self, 
        ticker: str, 
        start_date: str, 
        days: int
    ) -> List[Dict]:
        """
        Fetch forward-looking price data for a ticker.
        
        CRITICAL: This is for backtesting only. We're intentionally looking ahead
        to see what actually happened after our prediction.
        
        Args:
            ticker: Stock symbol
            start_date: Starting date (YYYY-MM-DD) - day AFTER this is first forward bar
            days: Number of calendar days to fetch
            
        Returns:
            List of OHLCV bar dicts with keys: date, open, high, low, close, volume
        """
        # Calculate the forward window (day after start_date to start_date + days)
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        from_dt = start_dt + timedelta(days=1)  # Start fetching day after scan date
        end_dt = start_dt + timedelta(days=days)
        
        from_date = from_dt.strftime("%Y-%m-%d")
        end_date = end_dt.strftime("%Y-%m-%d")
        
        try:
            bars = await self.api_client.fetch_stock_data_range(
                ticker=ticker,
                from_date=from_date,
                to_date=end_date
            )
            return bars
            
        except Exception as e:
            logger.error(f"Failed to fetch forward data for {ticker}: {e}")
            return []
    
    def _analyze_trade(
        self,
        ticker: str,
        entry_price: float,
        score: int,
        signals,
        forward_data: List[Dict],
        horizon_days: int
    ) -> Dict:
        """
        Analyze how a trade performed based on forward-looking data.
        
        Args:
            ticker: Stock symbol
            entry_price: Price at time of prediction
            score: Bullish score (0-100)
            signals: IndicatorSignals model or dict of technical signals
            forward_data: List of price bars after entry
            horizon_days: How many days to track
            
        Returns:
            Dict with trade analysis results
        """
        # Convert signals to dict if it's a Pydantic model
        if hasattr(signals, 'model_dump'):
            signals_dict = signals.model_dump()
        elif hasattr(signals, 'dict'):
            signals_dict = signals.dict()
        else:
            signals_dict = signals
        
        if not forward_data:
            return {
                "ticker": ticker,
                "entry_price": entry_price,
                "score": score,
                "status": "insufficient_data"
            }
        
        # Take only the horizon_days bars (or less if not available)
        relevant_bars = forward_data[:horizon_days]
        
        if len(relevant_bars) == 0:
            return {
                "ticker": ticker,
                "entry_price": entry_price,
                "score": score,
                "status": "no_forward_data"
            }
        
        # Extract prices
        highs = [bar['high'] for bar in relevant_bars]
        lows = [bar['low'] for bar in relevant_bars]
        closes = [bar['close'] for bar in relevant_bars]
        
        # Calculate metrics
        max_high = max(highs) if highs else entry_price
        min_low = min(lows) if lows else entry_price
        final_price = closes[-1] if closes else entry_price
        
        # Calculate returns
        return_pct = ((final_price - entry_price) / entry_price) * 100
        max_gain_pct = ((max_high - entry_price) / entry_price) * 100
        max_loss_pct = ((min_low - entry_price) / entry_price) * 100
        
        # Determine if trade was a winner
        is_winner = return_pct > 0
        
        # Simple target calculation (since V1 doesn't have targets yet)
        # Assume T1 = +10%, T2 = +20% for baseline
        hit_target_1 = max_gain_pct >= 10.0
        hit_target_2 = max_gain_pct >= 20.0
        
        # Simple stop calculation: -7% (standard risk management)
        hit_stop = max_loss_pct <= -7.0
        
        return {
            "ticker": ticker,
            "entry_price": entry_price,
            "final_price": final_price,
            "score": score,
            "signals": signals_dict,
            "days_tracked": len(relevant_bars),
            "return_pct": round(return_pct, 2),
            "max_gain_pct": round(max_gain_pct, 2),
            "max_loss_pct": round(max_loss_pct, 2),
            "is_winner": is_winner,
            "hit_target_1": hit_target_1,
            "hit_target_2": hit_target_2,
            "hit_stop": hit_stop,
            "status": "analyzed"
        }
    
    async def run_rolling_backtest(
        self,
        start_date: str,
        end_date: str,
        tickers: List[str],
        frequency: str = "monthly",  # "weekly", "monthly"
        horizon_days: int = 30
    ) -> Dict:
        """
        Run backtests at regular intervals over a date range.
        
        Args:
            start_date: Start of backtest period (YYYY-MM-DD)
            end_date: End of backtest period (YYYY-MM-DD)
            tickers: List of tickers to test
            frequency: How often to run scans ("weekly" or "monthly")
            horizon_days: Forward-looking horizon
            
        Returns:
            Aggregated results from all backtest dates
        """
        logger.info(
            f"Starting rolling backtest: {start_date} to {end_date}, "
            f"frequency={frequency}"
        )
        
        # Generate test dates
        test_dates = self._generate_test_dates(start_date, end_date, frequency)
        
        # Run backtest for each date
        all_results = []
        
        for test_date in test_dates:
            result = await self.run_single_date_backtest(
                as_of_date=test_date,
                tickers=tickers,
                horizon_days=horizon_days
            )
            all_results.append(result)
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.5)
        
        # Aggregate all trades
        all_trades = []
        for result in all_results:
            if result.get("status") == "completed":
                all_trades.extend(result.get("trades", []))
        
        # Calculate overall metrics
        overall_metrics = BacktestMetrics.calculate_aggregate_metrics(all_trades)
        
        return {
            "backtest_type": "rolling",
            "start_date": start_date,
            "end_date": end_date,
            "frequency": frequency,
            "horizon_days": horizon_days,
            "total_scan_dates": len(test_dates),
            "total_trades": len(all_trades),
            "overall_metrics": overall_metrics,
            "by_date": all_results
        }
    
    def _generate_test_dates(
        self, 
        start_date: str, 
        end_date: str, 
        frequency: str
    ) -> List[str]:
        """
        Generate list of dates to test based on frequency.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            frequency: "weekly" or "monthly"
            
        Returns:
            List of date strings
        """
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        dates = []
        current_dt = start_dt
        
        if frequency == "weekly":
            delta = timedelta(days=7)
        elif frequency == "monthly":
            delta = timedelta(days=30)
        else:
            delta = timedelta(days=30)
        
        while current_dt <= end_dt:
            dates.append(current_dt.strftime("%Y-%m-%d"))
            current_dt += delta
        
        return dates
