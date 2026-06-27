"""
Market Regime Analyzer

Analyzes current market conditions by examining broad market index (SPY).
Classifies market regime as bullish, bearish, or neutral based on SMA crossover.
"""

import logging
from typing import Optional

from api.models import MarketRegime
from core.api_client import RestApiClient, ApiError
from core.models import StockData


logger = logging.getLogger(__name__)


class MarketRegimeAnalyzer:
    """Analyzes current market conditions."""
    
    def __init__(self, api_client: RestApiClient):
        """
        Initialize with API client dependency.
        
        Args:
            api_client: RestApiClient instance for fetching market data
        """
        self.api_client = api_client
        logger.debug("MarketRegimeAnalyzer initialized")
    
    async def analyze_regime(self, as_of_date: str = None) -> MarketRegime:
        """
        Determine current market regime.
        
        Fetches SPY (S&P 500 ETF) data and calculates 50-day and 200-day SMAs.
        Classification logic:
        - Bullish: SMA_50 > SMA_200
        - Bearish: SMA_50 < SMA_200 * 0.98 (more than 2% below)
        - Neutral: SMA_50 within 2% of SMA_200
        
        Args:
            as_of_date: Optional cutoff date (YYYY-MM-DD). If provided, only uses
                        data available up to this date for regime classification.
        
        Returns:
            MarketRegime enum (BULLISH, BEARISH, or NEUTRAL)
        """
        try:
            # Fetch SPY data (need at least 200 days for 200-day SMA)
            logger.info("Fetching SPY data for market regime analysis")
            spy_data = await self.api_client.fetch_stock_data(
                "SPY", days=250, as_of_date=as_of_date
            )
            
            # Calculate SMAs
            sma_50 = self._calculate_sma(spy_data.prices, 50)
            sma_200 = self._calculate_sma(spy_data.prices, 200)
            
            if sma_50 is None or sma_200 is None:
                logger.warning("Insufficient data for market regime analysis, defaulting to NEUTRAL")
                return MarketRegime.NEUTRAL
            
            # Classification logic
            ratio = sma_50 / sma_200
            
            if ratio > 1.0:
                regime = MarketRegime.BULLISH
                logger.info(f"Market regime: BULLISH (SMA_50={sma_50:.2f}, SMA_200={sma_200:.2f}, ratio={ratio:.4f})")
            elif ratio < 0.98:
                regime = MarketRegime.BEARISH
                logger.info(f"Market regime: BEARISH (SMA_50={sma_50:.2f}, SMA_200={sma_200:.2f}, ratio={ratio:.4f})")
            else:
                regime = MarketRegime.NEUTRAL
                logger.info(f"Market regime: NEUTRAL (SMA_50={sma_50:.2f}, SMA_200={sma_200:.2f}, ratio={ratio:.4f})")
            
            return regime
            
        except ApiError as e:
            logger.error(f"API error during market regime analysis: {e}")
            logger.warning("Defaulting to NEUTRAL regime due to API failure")
            return MarketRegime.NEUTRAL
        except Exception as e:
            logger.error(f"Unexpected error during market regime analysis: {e}")
            logger.warning("Defaulting to NEUTRAL regime due to unexpected error")
            return MarketRegime.NEUTRAL
    
    @staticmethod
    def _calculate_sma(prices: 'np.ndarray', period: int) -> Optional[float]:
        """
        Calculate Simple Moving Average.
        
        Args:
            prices: Array of closing prices
            period: Number of periods for SMA calculation
            
        Returns:
            SMA value or None if insufficient data
        """
        if len(prices) < period:
            return None
        
        # Use the last 'period' prices
        return float(prices[-period:].mean())
