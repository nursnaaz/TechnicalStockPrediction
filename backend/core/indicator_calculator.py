"""
Indicator Calculator

Computes technical indicators from price and volume data.
"""

import numpy as np
from typing import Optional
import logging
from core.models import StockData, TechnicalIndicators

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """Computes technical indicators from price/volume data."""
    
    @staticmethod
    def calculate_sma(prices: np.ndarray, period: int) -> Optional[float]:
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
        
        return float(np.mean(prices[-period:]))
    
    @staticmethod
    def calculate_ema(prices: np.ndarray, period: int) -> Optional[float]:
        """
        Calculate Exponential Moving Average.
        
        Args:
            prices: Array of closing prices
            period: Number of periods for EMA calculation
            
        Returns:
            EMA value or None if insufficient data
        """
        if len(prices) < period:
            return None
        
        # Calculate multiplier
        multiplier = 2 / (period + 1)
        
        # Initialize EMA with SMA of first 'period' prices
        ema = float(np.mean(prices[:period]))
        
        # Calculate EMA iteratively
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return float(ema)
    
    @staticmethod
    def calculate_macd(prices: np.ndarray) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate MACD indicator.
        
        MACD Line = EMA(12) - EMA(26)
        Signal Line = EMA(9) of MACD Line
        Histogram = MACD Line - Signal Line
        
        Args:
            prices: Array of closing prices
            
        Returns:
            Tuple of (macd_line, signal_line, histogram) or (None, None, None) if insufficient data
        """
        # Need at least 26 periods for EMA(26)
        if len(prices) < 26:
            return None, None, None
        
        # Calculate EMA(12) and EMA(26)
        ema_12 = IndicatorCalculator.calculate_ema(prices, 12)
        ema_26 = IndicatorCalculator.calculate_ema(prices, 26)
        
        if ema_12 is None or ema_26 is None:
            return None, None, None
        
        # MACD Line = EMA(12) - EMA(26)
        macd_line = ema_12 - ema_26
        
        # For signal line, we need to calculate EMA(9) of the MACD line values
        # We'll need to compute MACD for the last 34 periods (26 + 9 - 1)
        if len(prices) < 34:
            # Can compute MACD line but not signal line yet
            return float(macd_line), None, None
        
        # Calculate MACD values for EMA(9) calculation
        macd_values = []
        for i in range(len(prices) - 33, len(prices) + 1):
            ema_12_i = IndicatorCalculator.calculate_ema(prices[:i], 12)
            ema_26_i = IndicatorCalculator.calculate_ema(prices[:i], 26)
            if ema_12_i is not None and ema_26_i is not None:
                macd_values.append(ema_12_i - ema_26_i)
        
        if len(macd_values) < 9:
            return float(macd_line), None, None
        
        # Calculate signal line as EMA(9) of MACD values
        signal_line = IndicatorCalculator.calculate_ema(np.array(macd_values), 9)
        
        if signal_line is None:
            return float(macd_line), None, None
        
        # Calculate histogram
        histogram = macd_line - signal_line
        
        return float(macd_line), float(signal_line), float(histogram)
    
    @staticmethod
    def calculate_avg_volume(volumes: np.ndarray, period: int) -> Optional[float]:
        """
        Calculate average volume over a period.
        
        Args:
            volumes: Array of volume values
            period: Number of periods for average calculation
            
        Returns:
            Average volume or None if insufficient data
        """
        if len(volumes) < period:
            return None
        
        return float(np.mean(volumes[-period:]))
    
    @staticmethod
    def calculate_relative_strength(
        ticker_prices: np.ndarray, 
        market_prices: np.ndarray, 
        period: int
    ) -> Optional[float]:
        """
        Calculate relative strength vs market.
        
        RS = ticker_return - market_return (as percentage point difference)
        
        Args:
            ticker_prices: Array of closing prices for the ticker
            market_prices: Array of closing prices for market index
            period: Number of periods for return calculation
            
        Returns:
            Relative strength (percentage point difference) or None if insufficient data
        """
        if len(ticker_prices) < period + 1 or len(market_prices) < period + 1:
            return None
        
        # Calculate ticker return
        ticker_start = ticker_prices[-(period + 1)]
        ticker_end = ticker_prices[-1]
        
        if ticker_start == 0:
            return None
        
        ticker_return = ((ticker_end - ticker_start) / ticker_start) * 100
        
        # Calculate market return
        market_start = market_prices[-(period + 1)]
        market_end = market_prices[-1]
        
        if market_start == 0:
            return None
        
        market_return = ((market_end - market_start) / market_start) * 100
        
        # Relative strength is the percentage point difference
        relative_strength = ticker_return - market_return
        
        return float(relative_strength)
    
    def calculate_all(
        self, 
        stock_data: StockData, 
        market_data: StockData
    ) -> TechnicalIndicators:
        """
        Calculate all indicators for a ticker.
        
        Args:
            stock_data: Historical data for the ticker
            market_data: Historical data for market index (SPY)
            
        Returns:
            TechnicalIndicators with all computed values (None for unavailable)
        """
        indicators = TechnicalIndicators()
        
        # Calculate SMA(50)
        indicators.sma_50 = self.calculate_sma(stock_data.prices, 50)
        if indicators.sma_50 is None:
            logger.warning(f"Insufficient data to calculate SMA(50) for {stock_data.ticker}")
        
        # Calculate EMA(20)
        indicators.ema_20 = self.calculate_ema(stock_data.prices, 20)
        if indicators.ema_20 is None:
            logger.warning(f"Insufficient data to calculate EMA(20) for {stock_data.ticker}")
        
        # Calculate MACD
        macd_line, signal_line, histogram = self.calculate_macd(stock_data.prices)
        indicators.macd_line = macd_line
        indicators.macd_signal = signal_line
        indicators.macd_histogram = histogram
        if macd_line is None:
            logger.warning(f"Insufficient data to calculate MACD for {stock_data.ticker}")
        
        # Calculate average volume(20)
        indicators.avg_volume_20 = self.calculate_avg_volume(stock_data.volumes, 20)
        if indicators.avg_volume_20 is None:
            logger.warning(f"Insufficient data to calculate average volume for {stock_data.ticker}")
        
        # Calculate relative strength
        indicators.relative_strength = self.calculate_relative_strength(
            stock_data.prices,
            market_data.prices,
            20
        )
        if indicators.relative_strength is None:
            logger.warning(f"Insufficient data to calculate relative strength for {stock_data.ticker}")
        
        return indicators
