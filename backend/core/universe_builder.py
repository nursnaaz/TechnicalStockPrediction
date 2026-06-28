"""
Universe Builder

Constructs and validates the universe of tickers to analyze.
"""

import re

from utils.logging import get_logger

logger = get_logger(__name__)


class UniverseBuilder:
    """Constructs the universe of tickers to analyze."""

    @staticmethod
    def validate_ticker(ticker: str) -> bool:
        """
        Validate ticker is non-empty and alphanumeric.

        Args:
            ticker: Stock ticker symbol to validate

        Returns:
            True if ticker is valid, False otherwise
        """
        if not ticker:
            return False
        # Validate alphanumeric pattern (uppercase letters and digits only)
        pattern = r"^[A-Z0-9]+$"
        return bool(re.match(pattern, ticker))

    def build_universe(self, tickers: list[str]) -> list[str]:
        """
        Build and validate universe of tickers.

        Args:
            tickers: List of ticker symbols (required)

        Returns:
            List of valid ticker symbols

        Raises:
            ValueError: If tickers list is empty or all tickers are invalid
        """
        # Check if input list is empty
        if not tickers:
            logger.error("Input ticker list is empty")
            raise ValueError("Ticker list cannot be empty")

        # Validate each ticker and filter invalid ones
        valid_tickers = []
        for ticker in tickers:
            if self.validate_ticker(ticker):
                valid_tickers.append(ticker)
            else:
                logger.warning(f"Invalid ticker excluded from universe: '{ticker}'")

        # Check if all tickers were invalid
        if not valid_tickers:
            logger.error("All tickers in the input list are invalid")
            raise ValueError("All tickers are invalid")

        logger.info(f"Universe built with {len(valid_tickers)} valid tickers")
        return valid_tickers
