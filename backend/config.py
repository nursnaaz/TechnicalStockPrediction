"""
Configuration Management

Reads configuration from environment variables with sensible defaults.
POLYGON_TOKEN is already set globally in the system shell (no .env file required).
"""

import os
from typing import Optional

class Config:
    """Application configuration."""
    
    # API Configuration
    POLYGON_TOKEN: str = os.getenv("POLYGON_TOKEN", "")
    API_BASE_URL: str = os.getenv("API_BASE_URL", "https://api.polygon.io")
    
    # Server Configuration
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # API Client Configuration
    MAX_CONCURRENT_REQUESTS: int = 5
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 2.0  # Exponential backoff: 1s, 2s, 4s

    # History window (V3): fetch_stock_data `days` is CALENDAR days. ~365 calendar days
    # guarantees >= 252 trading bars so SMA(200), the 20-bar SMA200 slope, and 52-week
    # high/low are all computable for the Minervini hard filters.
    HISTORY_FETCH_DAYS: int = 365
    MIN_TRADING_BARS: int = 252

    # V3 regime-based BUY thresholds (R1/R7)
    BULLISH_SCORE_THRESHOLD: int = 65
    NEUTRAL_SCORE_THRESHOLD: int = 75
    REGIME_PERSISTENCE_DAYS: int = 5  # consecutive closes above/below SMA200
    
    # Database Configuration
    DB_PATH: str = os.getenv("DB_PATH", "scanner.db")
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        if not cls.POLYGON_TOKEN:
            raise ValueError(
                "POLYGON_TOKEN environment variable is required. "
                "It should be set globally in your shell configuration."
            )


# Create global config instance
config = Config()
