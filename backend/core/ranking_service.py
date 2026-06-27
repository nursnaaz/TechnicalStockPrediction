"""
Ranking Service

Ranks tickers by bullish score in descending order.
"""

from typing import List
from api.models import TickerScore


class RankingService:
    """Ranks tickers by bullish score."""

    def rank_tickers(self, scored_tickers: List[TickerScore]) -> List[TickerScore]:
        """
        Sort tickers by score in descending order.

        Uses Python's stable sort to maintain the original order for tickers
        with identical scores.

        Args:
            scored_tickers: List of tickers with scores

        Returns:
            Sorted list (descending by score, stable for ties)
        """
        # Python's sorted() is stable - maintains original order for equal elements
        return sorted(scored_tickers, key=lambda t: t.bullish_score, reverse=True)
