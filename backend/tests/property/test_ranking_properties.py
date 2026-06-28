"""
Property-Based Tests for Ranking Service

Tests mathematical properties and invariants for ticker ranking.
"""

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from api.models import IndicatorSignals, TickerScore
from core.ranking_service import RankingService


# Custom strategies for realistic test data
def ticker_symbol_strategy():
    """Generate realistic ticker symbols (1-5 uppercase letters/digits)."""
    return st.text(
        alphabet=st.characters(whitelist_categories=("Lu",), max_codepoint=90),
        min_size=1,
        max_size=5,
    )


def bullish_score_strategy():
    """Generate valid bullish scores (0-100)."""
    return st.integers(min_value=0, max_value=100)


def price_strategy():
    """Generate realistic price values."""
    return st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False)


def indicator_signals_strategy():
    """Generate random indicator signals."""
    return st.builds(
        IndicatorSignals,
        price_above_sma50=st.booleans(),
        price_above_ema20=st.booleans(),
        macd_above_signal=st.booleans(),
        macd_histogram_positive=st.booleans(),
        volume_above_average=st.booleans(),
        relative_strength_positive=st.booleans(),
    )


def ticker_score_strategy():
    """Generate a valid TickerScore object."""
    return st.builds(
        TickerScore,
        ticker=ticker_symbol_strategy(),
        bullish_score=bullish_score_strategy(),
        signals=indicator_signals_strategy(),
        current_price=price_strategy(),
        indicators=st.fixed_dictionaries(
            {
                "sma_50": st.floats(
                    min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False
                ),
                "ema_20": st.floats(
                    min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False
                ),
                "macd_line": st.floats(
                    min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False
                ),
                "macd_signal": st.floats(
                    min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False
                ),
                "macd_histogram": st.floats(
                    min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False
                ),
                "avg_volume_20": st.floats(
                    min_value=1000.0, max_value=1000000000.0, allow_nan=False, allow_infinity=False
                ),
                "relative_strength": st.floats(
                    min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False
                ),
            }
        ),
    )


class TestDescendingScoreSortWithCompletePreservation:
    """Property-based tests for ranking correctness."""

    @settings(max_examples=20)
    @given(ticker_list=st.lists(ticker_score_strategy(), min_size=0, max_size=50))
    def test_property_18_descending_score_sort(self, ticker_list):
        """
        Property 18: Descending Score Sort with Complete Preservation
        **Validates: Requirements 6.1, 6.2, 6.4**

        Property: The ranking service SHALL sort all tickers in descending
        order by bullish_score. The sort SHALL be stable, meaning tickers
        with identical scores maintain their relative order from the input.
        All tickers SHALL be preserved in the output (no filtering).
        """
        service = RankingService()

        # Rank the tickers
        ranked_tickers = service.rank_tickers(ticker_list)

        # Property 1: Complete preservation - all tickers included
        assert len(ranked_tickers) == len(
            ticker_list
        ), "Ranking must preserve all tickers without filtering"

        # Property 2: Descending order by score
        for i in range(len(ranked_tickers) - 1):
            assert (
                ranked_tickers[i].bullish_score >= ranked_tickers[i + 1].bullish_score
            ), f"Scores must be in descending order: {ranked_tickers[i].bullish_score} >= {ranked_tickers[i + 1].bullish_score}"

        # Property 3: Stable sort - tickers with same score maintain relative order
        # Create a mapping of ticker to original position
        original_positions = {id(ticker): idx for idx, ticker in enumerate(ticker_list)}

        # Check that for equal scores, original order is maintained
        for i in range(len(ranked_tickers) - 1):
            if ranked_tickers[i].bullish_score == ranked_tickers[i + 1].bullish_score:
                # If scores are equal, check that original relative order is preserved
                orig_pos_i = original_positions.get(id(ranked_tickers[i]))
                orig_pos_i_plus_1 = original_positions.get(id(ranked_tickers[i + 1]))

                if orig_pos_i is not None and orig_pos_i_plus_1 is not None:
                    assert (
                        orig_pos_i < orig_pos_i_plus_1
                    ), "Stable sort violated: tickers with equal scores must maintain original order"

    @settings(max_examples=20)
    @given(
        ticker_list=st.lists(ticker_score_strategy(), min_size=2, max_size=20),
        duplicate_score=bullish_score_strategy(),
    )
    def test_property_18_stable_sort_with_ties(self, ticker_list, duplicate_score):
        """
        Property 18: Descending Score Sort with Complete Preservation (Stable Sort)
        **Validates: Requirements 6.2**

        Property: When multiple tickers have the same bullish_score, the
        ranking service SHALL maintain their relative order from the original
        input list (stable sort property).
        """
        assume(len(ticker_list) >= 2)

        service = RankingService()

        # Force at least 2 tickers to have the same score with UNIQUE ticker symbols
        ticker_list[0] = TickerScore(
            ticker="TEST0",  # Unique ticker for first test item
            bullish_score=duplicate_score,
            signals=ticker_list[0].signals,
            current_price=ticker_list[0].current_price,
            indicators=ticker_list[0].indicators,
        )

        ticker_list[1] = TickerScore(
            ticker="TEST1",  # Unique ticker for second test item
            bullish_score=duplicate_score,
            signals=ticker_list[1].signals,
            current_price=ticker_list[1].current_price,
            indicators=ticker_list[1].indicators,
        )

        # Rank the tickers
        ranked_tickers = service.rank_tickers(ticker_list)

        # Find the positions of our two test tickers in the result
        test_ticker_0_idx = None
        test_ticker_1_idx = None

        for idx, ticker in enumerate(ranked_tickers):
            if ticker.ticker == "TEST0":
                test_ticker_0_idx = idx
            elif ticker.ticker == "TEST1":
                test_ticker_1_idx = idx

        # Verify they are both present
        assert (
            test_ticker_0_idx is not None and test_ticker_1_idx is not None
        ), "Both test tickers must be present in results"

        # Verify stable sort: TEST0 should appear before TEST1
        # since they have the same score and 0 came before 1 in the original list
        assert (
            test_ticker_0_idx < test_ticker_1_idx
        ), "Stable sort violated: ticker at index 0 should appear before ticker at index 1 when scores are equal"

    @settings(max_examples=20)
    @given(ticker_list=st.lists(ticker_score_strategy(), min_size=0, max_size=20))
    def test_property_18_all_tickers_preserved(self, ticker_list):
        """
        Property 18: Descending Score Sort with Complete Preservation (Completeness)
        **Validates: Requirements 6.4**

        Property: The ranking service SHALL include ALL tickers in the output
        without filtering. The size of the output list SHALL equal the size
        of the input list.
        """
        service = RankingService()

        # Rank the tickers
        ranked_tickers = service.rank_tickers(ticker_list)

        # Verify count matches
        assert len(ranked_tickers) == len(
            ticker_list
        ), f"All tickers must be preserved: expected {len(ticker_list)}, got {len(ranked_tickers)}"

        # Verify all input tickers are present in output (by ticker symbol)
        input_tickers = {ticker.ticker for ticker in ticker_list}
        output_tickers = {ticker.ticker for ticker in ranked_tickers}

        # Note: This assumes ticker symbols are unique in the input.
        # If not unique, check by object identity or index position instead.
        if len(input_tickers) == len(ticker_list):  # All unique
            assert input_tickers == output_tickers, "All input ticker symbols must appear in output"

    def test_property_18_empty_list(self):
        """
        Property 18: Descending Score Sort with Complete Preservation (Edge Case)
        **Validates: Requirements 6.1, 6.4**

        Property: When given an empty list, the ranking service SHALL return
        an empty list without error.
        """
        service = RankingService()

        ranked_tickers = service.rank_tickers([])

        assert ranked_tickers == [], "Empty list should return empty list"
        assert len(ranked_tickers) == 0, "Empty list length should be 0"

    def test_property_18_single_ticker(self):
        """
        Property 18: Descending Score Sort with Complete Preservation (Edge Case)
        **Validates: Requirements 6.1, 6.4**

        Property: When given a single ticker, the ranking service SHALL return
        a list containing that single ticker.
        """
        service = RankingService()

        single_ticker = TickerScore(
            ticker="AAPL",
            bullish_score=75,
            signals=IndicatorSignals(
                price_above_sma50=True,
                price_above_ema20=True,
                macd_above_signal=False,
                macd_histogram_positive=True,
                volume_above_average=False,
                relative_strength_positive=True,
            ),
            current_price=150.0,
            indicators={
                "sma_50": 145.0,
                "ema_20": 148.0,
                "macd_line": -0.5,
                "macd_signal": -0.2,
                "macd_histogram": 0.3,
                "avg_volume_20": 50000000.0,
                "relative_strength": 2.5,
            },
        )

        ranked_tickers = service.rank_tickers([single_ticker])

        assert len(ranked_tickers) == 1, "Single ticker list should return list of length 1"
        assert ranked_tickers[0] == single_ticker, "Single ticker should be returned unchanged"
        assert ranked_tickers[0].ticker == "AAPL", "Ticker symbol should match"
        assert ranked_tickers[0].bullish_score == 75, "Score should match"

    @settings(max_examples=20)
    @given(score=bullish_score_strategy(), count=st.integers(min_value=2, max_value=20))
    def test_property_18_all_equal_scores(self, score, count):
        """
        Property 18: Descending Score Sort with Complete Preservation (All Equal)
        **Validates: Requirements 6.1, 6.2, 6.4**

        Property: When all tickers have the same score, the ranking service
        SHALL maintain the exact original order (stable sort).
        """
        service = RankingService()

        # Create list of tickers with same score but different symbols
        ticker_list = []
        for i in range(count):
            ticker_list.append(
                TickerScore(
                    ticker=f"TICK{i}",
                    bullish_score=score,
                    signals=IndicatorSignals(
                        price_above_sma50=True,
                        price_above_ema20=True,
                        macd_above_signal=True,
                        macd_histogram_positive=True,
                        volume_above_average=True,
                        relative_strength_positive=True,
                    ),
                    current_price=100.0 + i,
                    indicators={
                        "sma_50": 95.0,
                        "ema_20": 98.0,
                        "macd_line": 1.0,
                        "macd_signal": 0.5,
                        "macd_histogram": 0.5,
                        "avg_volume_20": 1000000.0,
                        "relative_strength": 1.5,
                    },
                )
            )

        # Rank the tickers
        ranked_tickers = service.rank_tickers(ticker_list)

        # All scores should be equal
        assert all(t.bullish_score == score for t in ranked_tickers), "All scores should be equal"

        # Order should be preserved
        for i in range(count):
            assert (
                ranked_tickers[i].ticker == f"TICK{i}"
            ), f"Original order must be preserved: expected TICK{i}, got {ranked_tickers[i].ticker}"

    @settings(max_examples=20)
    @given(st.lists(bullish_score_strategy(), min_size=1, max_size=20))
    def test_property_18_descending_order_invariant(self, scores):
        """
        Property 18: Descending Score Sort with Complete Preservation (Order Invariant)
        **Validates: Requirements 6.1**

        Property: For any list of scores, the output SHALL be in descending
        order. This is an invariant that must hold for all inputs.
        """
        service = RankingService()

        # Create tickers with the given scores
        ticker_list = []
        for i, score in enumerate(scores):
            ticker_list.append(
                TickerScore(
                    ticker=f"TICK{i}",
                    bullish_score=score,
                    signals=IndicatorSignals(
                        price_above_sma50=True,
                        price_above_ema20=True,
                        macd_above_signal=True,
                        macd_histogram_positive=True,
                        volume_above_average=True,
                        relative_strength_positive=True,
                    ),
                    current_price=100.0,
                    indicators={
                        "sma_50": 95.0,
                        "ema_20": 98.0,
                        "macd_line": 1.0,
                        "macd_signal": 0.5,
                        "macd_histogram": 0.5,
                        "avg_volume_20": 1000000.0,
                        "relative_strength": 1.5,
                    },
                )
            )

        # Rank the tickers
        ranked_tickers = service.rank_tickers(ticker_list)

        # Extract scores from ranked list
        ranked_scores = [t.bullish_score for t in ranked_tickers]

        # Verify descending order
        for i in range(len(ranked_scores) - 1):
            assert (
                ranked_scores[i] >= ranked_scores[i + 1]
            ), f"Scores must be in descending order: {ranked_scores[i]} >= {ranked_scores[i + 1]}"

        # Also verify that sorted descending matches our result
        expected_sorted = sorted(scores, reverse=True)
        assert (
            ranked_scores == expected_sorted
        ), "Ranked scores should match descending sort of input scores"
