"""
Unit tests for RankingService

Tests the ranking and sorting of tickers by bullish score.
"""

import pytest

from api.models import IndicatorSignals, TickerScore
from core.ranking_service import RankingService


@pytest.fixture
def ranking_service():
    """Fixture for RankingService instance."""
    return RankingService()


@pytest.fixture
def sample_signals():
    """Fixture for sample indicator signals."""
    return IndicatorSignals(
        price_above_sma50=True,
        price_above_ema20=True,
        macd_above_signal=True,
        macd_histogram_positive=True,
        volume_above_average=True,
        relative_strength_positive=True,
    )


@pytest.fixture
def sample_indicators():
    """Fixture for sample indicator values."""
    return {
        "sma_50": 100.0,
        "ema_20": 105.0,
        "macd_line": 1.5,
        "macd_signal": 1.0,
        "macd_histogram": 0.5,
        "avg_volume_20": 1000000.0,
        "relative_strength": 2.5,
    }


class TestRankingService:
    """Test suite for RankingService."""

    def test_descending_sort_by_score(self, ranking_service, sample_signals, sample_indicators):
        """Test that tickers are sorted in descending order by bullish_score."""
        # Create tickers with different scores
        tickers = [
            TickerScore(
                ticker="LOW",
                bullish_score=30,
                signals=sample_signals,
                current_price=100.0,
                indicators=sample_indicators,
            ),
            TickerScore(
                ticker="HIGH",
                bullish_score=90,
                signals=sample_signals,
                current_price=150.0,
                indicators=sample_indicators,
            ),
            TickerScore(
                ticker="MID",
                bullish_score=60,
                signals=sample_signals,
                current_price=120.0,
                indicators=sample_indicators,
            ),
        ]

        # Rank the tickers
        ranked = ranking_service.rank_tickers(tickers)

        # Verify descending order
        assert ranked[0].ticker == "HIGH"
        assert ranked[0].bullish_score == 90
        assert ranked[1].ticker == "MID"
        assert ranked[1].bullish_score == 60
        assert ranked[2].ticker == "LOW"
        assert ranked[2].bullish_score == 30

    def test_stable_sort_for_equal_scores(self, ranking_service, sample_signals, sample_indicators):
        """Test that stable sort maintains original order for equal scores."""
        # Create tickers with identical scores in a specific order
        tickers = [
            TickerScore(
                ticker="FIRST",
                bullish_score=50,
                signals=sample_signals,
                current_price=100.0,
                indicators=sample_indicators,
            ),
            TickerScore(
                ticker="SECOND",
                bullish_score=50,
                signals=sample_signals,
                current_price=105.0,
                indicators=sample_indicators,
            ),
            TickerScore(
                ticker="THIRD",
                bullish_score=50,
                signals=sample_signals,
                current_price=110.0,
                indicators=sample_indicators,
            ),
        ]

        # Rank the tickers
        ranked = ranking_service.rank_tickers(tickers)

        # Verify stable sort - original order is maintained
        assert ranked[0].ticker == "FIRST"
        assert ranked[1].ticker == "SECOND"
        assert ranked[2].ticker == "THIRD"
        # All should have the same score
        assert ranked[0].bullish_score == 50
        assert ranked[1].bullish_score == 50
        assert ranked[2].bullish_score == 50

    def test_all_tickers_included_in_output(
        self, ranking_service, sample_signals, sample_indicators
    ):
        """Test that all tickers are included in output (no filtering)."""
        # Create a list of tickers
        tickers = [
            TickerScore(
                ticker=f"TICK{i}",
                bullish_score=i * 10,
                signals=sample_signals,
                current_price=100.0 + i,
                indicators=sample_indicators,
            )
            for i in range(10)
        ]

        # Rank the tickers
        ranked = ranking_service.rank_tickers(tickers)

        # Verify all tickers are present
        assert len(ranked) == len(tickers)
        assert len(ranked) == 10

        # Verify no tickers were lost
        original_tickers = {t.ticker for t in tickers}
        ranked_tickers = {t.ticker for t in ranked}
        assert original_tickers == ranked_tickers

    def test_empty_list_handling(self, ranking_service):
        """Test handling of empty list."""
        # Rank an empty list
        ranked = ranking_service.rank_tickers([])

        # Should return empty list
        assert ranked == []
        assert len(ranked) == 0

    def test_single_ticker_handling(self, ranking_service, sample_signals, sample_indicators):
        """Test handling of single ticker."""
        # Create a single ticker
        tickers = [
            TickerScore(
                ticker="ONLY",
                bullish_score=75,
                signals=sample_signals,
                current_price=100.0,
                indicators=sample_indicators,
            )
        ]

        # Rank the single ticker
        ranked = ranking_service.rank_tickers(tickers)

        # Should return the same single ticker
        assert len(ranked) == 1
        assert ranked[0].ticker == "ONLY"
        assert ranked[0].bullish_score == 75

    def test_mixed_scores_with_ties(self, ranking_service, sample_signals, sample_indicators):
        """Test ranking with mixed scores including ties."""
        # Create tickers with some ties
        tickers = [
            TickerScore(
                ticker="A",
                bullish_score=80,
                signals=sample_signals,
                current_price=100.0,
                indicators=sample_indicators,
            ),
            TickerScore(
                ticker="B",
                bullish_score=60,
                signals=sample_signals,
                current_price=100.0,
                indicators=sample_indicators,
            ),
            TickerScore(
                ticker="C",
                bullish_score=80,
                signals=sample_signals,
                current_price=100.0,
                indicators=sample_indicators,
            ),
            TickerScore(
                ticker="D",
                bullish_score=90,
                signals=sample_signals,
                current_price=100.0,
                indicators=sample_indicators,
            ),
            TickerScore(
                ticker="E",
                bullish_score=60,
                signals=sample_signals,
                current_price=100.0,
                indicators=sample_indicators,
            ),
        ]

        # Rank the tickers
        ranked = ranking_service.rank_tickers(tickers)

        # Verify correct ordering
        assert ranked[0].ticker == "D"  # 90
        assert ranked[1].ticker == "A"  # 80 (first in original order)
        assert ranked[2].ticker == "C"  # 80 (second in original order)
        assert ranked[3].ticker == "B"  # 60 (first in original order)
        assert ranked[4].ticker == "E"  # 60 (second in original order)

    def test_extreme_score_values(self, ranking_service, sample_signals, sample_indicators):
        """Test with extreme score values (0 and 100)."""
        tickers = [
            TickerScore(
                ticker="MIN",
                bullish_score=0,
                signals=sample_signals,
                current_price=100.0,
                indicators=sample_indicators,
            ),
            TickerScore(
                ticker="MAX",
                bullish_score=100,
                signals=sample_signals,
                current_price=100.0,
                indicators=sample_indicators,
            ),
            TickerScore(
                ticker="MID",
                bullish_score=50,
                signals=sample_signals,
                current_price=100.0,
                indicators=sample_indicators,
            ),
        ]

        # Rank the tickers
        ranked = ranking_service.rank_tickers(tickers)

        # Verify correct ordering
        assert ranked[0].ticker == "MAX"
        assert ranked[0].bullish_score == 100
        assert ranked[1].ticker == "MID"
        assert ranked[1].bullish_score == 50
        assert ranked[2].ticker == "MIN"
        assert ranked[2].bullish_score == 0

    def test_original_list_not_modified(self, ranking_service, sample_signals, sample_indicators):
        """Test that the original list is not modified."""
        # Create original list
        original_tickers = [
            TickerScore(
                ticker="C",
                bullish_score=30,
                signals=sample_signals,
                current_price=100.0,
                indicators=sample_indicators,
            ),
            TickerScore(
                ticker="A",
                bullish_score=90,
                signals=sample_signals,
                current_price=100.0,
                indicators=sample_indicators,
            ),
            TickerScore(
                ticker="B",
                bullish_score=60,
                signals=sample_signals,
                current_price=100.0,
                indicators=sample_indicators,
            ),
        ]

        # Store original order
        original_order = [t.ticker for t in original_tickers]

        # Rank the tickers
        ranked = ranking_service.rank_tickers(original_tickers)

        # Verify original list is unchanged
        assert [t.ticker for t in original_tickers] == original_order
        assert original_tickers[0].ticker == "C"
        assert original_tickers[1].ticker == "A"
        assert original_tickers[2].ticker == "B"

        # Verify ranked list is different
        assert ranked[0].ticker == "A"
        assert ranked[1].ticker == "B"
        assert ranked[2].ticker == "C"
