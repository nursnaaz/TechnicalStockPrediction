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
