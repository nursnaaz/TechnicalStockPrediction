"""
Integration Test: Scoring Pipeline

Tests the complete flow: Indicator Calculator → Scoring Engine → Ranking Service

Requirements: 4.7, 5.10, 6.4
"""

import pytest
import numpy as np
from core.indicator_calculator import IndicatorCalculator
from core.scoring_engine import ScoringEngine
from core.ranking_service import RankingService
from core.models import StockData
from api.models import TickerScore


class TestScoringPipeline:
    """Test complete flow from indicator calculation to ranking."""

    def test_complete_flow_with_valid_indicators(self):
        """
        Test complete pipeline flow: calculate indicators → score → rank.
        
        Requirements:
        - 4.7: Indicator Calculator returns all calculated indicators for each ticker
        - 5.10: Scoring Engine returns Bullish_Score and contributing indicator signals
        - 6.4: Ranking Service includes ticker symbol, Bullish_Score, and indicator breakdown
        """
        # Setup components
        calculator = IndicatorCalculator()
        scorer = ScoringEngine()
        ranker = RankingService()

        # Create synthetic stock data with clear bullish signals
        # Stock 1: Strong bullish (should score ~85-100)
        prices_bullish = np.concatenate([
            np.linspace(100, 150, 30),  # Uptrend
            np.linspace(150, 180, 20)
        ])
        volumes_bullish = np.concatenate([
            np.full(30, 1_000_000),
            np.full(20, 1_500_000)  # Volume surge
        ])
        stock1 = StockData(
            ticker="BULL",
            prices=prices_bullish,
            volumes=volumes_bullish,
            timestamps=np.arange(50)
        )

        # Stock 2: Moderate bullish (should score ~50-70)
        prices_moderate = np.concatenate([
            np.linspace(100, 120, 30),
            np.linspace(120, 125, 20)
        ])
        volumes_moderate = np.full(50, 1_000_000)
        stock2 = StockData(
            ticker="MODS",
            prices=prices_moderate,
            volumes=volumes_moderate,
            timestamps=np.arange(50)
        )

        # Stock 3: Bearish (should score low ~0-30)
        prices_bearish = np.concatenate([
            np.linspace(150, 100, 30),  # Downtrend
            np.linspace(100, 90, 20)
        ])
        volumes_bearish = np.full(50, 1_000_000)
        stock3 = StockData(
            ticker="BEAR",
            prices=prices_bearish,
            volumes=volumes_bearish,
            timestamps=np.arange(50)
        )

        # Market data (moderate performance for relative strength calculation)
        market_prices = np.linspace(100, 110, 50)
        market_data = StockData(
            ticker="SPY",
            prices=market_prices,
            volumes=np.full(50, 10_000_000),
            timestamps=np.arange(50)
        )

        # Step 1: Calculate indicators for all tickers
        indicators1 = calculator.calculate_all(stock1, market_data)
        indicators2 = calculator.calculate_all(stock2, market_data)
        indicators3 = calculator.calculate_all(stock3, market_data)

        # Verify indicators were calculated
        assert indicators1.sma_50 is not None
        assert indicators1.ema_20 is not None
        assert indicators1.macd_line is not None
        assert indicators2.sma_50 is not None
        assert indicators3.sma_50 is not None

        # Step 2: Score each ticker
        current_price1 = stock1.prices[-1]
        current_volume1 = stock1.volumes[-1]
        score1, signals1 = scorer.calculate_score(current_price1, current_volume1, indicators1)

        current_price2 = stock2.prices[-1]
        current_volume2 = stock2.volumes[-1]
        score2, signals2 = scorer.calculate_score(current_price2, current_volume2, indicators2)

        current_price3 = stock3.prices[-1]
        current_volume3 = stock3.volumes[-1]
        score3, signals3 = scorer.calculate_score(current_price3, current_volume3, indicators3)

        # Verify scoring produced valid results
        assert 0 <= score1 <= 100
        assert 0 <= score2 <= 100
        assert 0 <= score3 <= 100

        # Verify bullish stock scores higher than bearish
        assert score1 > score3
        assert score2 > score3

        # Step 3: Create TickerScore objects
        ticker_scores = [
            TickerScore(
                ticker=stock1.ticker,
                bullish_score=score1,
                signals=signals1,
                current_price=current_price1,
                indicators={
                    "sma_50": indicators1.sma_50,
                    "ema_20": indicators1.ema_20,
                    "macd_line": indicators1.macd_line,
                    "macd_signal": indicators1.macd_signal,
                    "macd_histogram": indicators1.macd_histogram,
                    "avg_volume_20": indicators1.avg_volume_20,
                    "relative_strength": indicators1.relative_strength
                }
            ),
            TickerScore(
                ticker=stock2.ticker,
                bullish_score=score2,
                signals=signals2,
                current_price=current_price2,
                indicators={
                    "sma_50": indicators2.sma_50,
                    "ema_20": indicators2.ema_20,
                    "macd_line": indicators2.macd_line,
                    "macd_signal": indicators2.macd_signal,
                    "macd_histogram": indicators2.macd_histogram,
                    "avg_volume_20": indicators2.avg_volume_20,
                    "relative_strength": indicators2.relative_strength
                }
            ),
            TickerScore(
                ticker=stock3.ticker,
                bullish_score=score3,
                signals=signals3,
                current_price=current_price3,
                indicators={
                    "sma_50": indicators3.sma_50,
                    "ema_20": indicators3.ema_20,
                    "macd_line": indicators3.macd_line,
                    "macd_signal": indicators3.macd_signal,
                    "macd_histogram": indicators3.macd_histogram,
                    "avg_volume_20": indicators3.avg_volume_20,
                    "relative_strength": indicators3.relative_strength
                }
            )
        ]

        # Step 4: Rank tickers
        ranked = ranker.rank_tickers(ticker_scores)

        # Verify ranking order (highest score first)
        assert len(ranked) == 3
        assert ranked[0].bullish_score >= ranked[1].bullish_score
        assert ranked[1].bullish_score >= ranked[2].bullish_score

        # Verify all required data is present in results (Requirement 6.4)
        for ticker_score in ranked:
            assert ticker_score.ticker is not None
            assert ticker_score.bullish_score is not None
            assert ticker_score.signals is not None
            assert ticker_score.current_price is not None
            assert ticker_score.indicators is not None

    def test_mixed_valid_invalid_indicators(self):
        """
        Test pipeline with some indicators unavailable (insufficient data).
        
        Requirement 5.10: If any indicator is unavailable, then the Scoring Engine 
        shall assign 0 points for that indicator and continue scoring with available indicators.
        """
        calculator = IndicatorCalculator()
        scorer = ScoringEngine()
        ranker = RankingService()

        # Stock with insufficient data for some indicators
        # Only 25 periods - insufficient for SMA(50) but sufficient for EMA(20)
        prices_short = np.linspace(100, 110, 25)
        volumes_short = np.full(25, 1_000_000)
        stock_short = StockData(
            ticker="SHORT",
            prices=prices_short,
            volumes=volumes_short,
            timestamps=np.arange(25)
        )

        # Stock with full data
        prices_full = np.linspace(100, 120, 60)
        volumes_full = np.full(60, 1_000_000)
        stock_full = StockData(
            ticker="FULL",
            prices=prices_full,
            volumes=volumes_full,
            timestamps=np.arange(60)
        )

        # Market data
        market_prices = np.linspace(100, 105, 60)
        market_data = StockData(
            ticker="SPY",
            prices=market_prices,
            volumes=np.full(60, 10_000_000),
            timestamps=np.arange(60)
        )

        # Calculate indicators
        indicators_short = calculator.calculate_all(stock_short, market_data)
        indicators_full = calculator.calculate_all(stock_full, market_data)

        # Verify some indicators are None for short data
        assert indicators_short.sma_50 is None  # Not enough data
        assert indicators_short.ema_20 is not None  # Enough data

        # Verify all indicators calculated for full data
        assert indicators_full.sma_50 is not None
        assert indicators_full.ema_20 is not None

        # Score both tickers
        score_short, signals_short = scorer.calculate_score(
            stock_short.prices[-1],
            stock_short.volumes[-1],
            indicators_short
        )
        score_full, signals_full = scorer.calculate_score(
            stock_full.prices[-1],
            stock_full.volumes[-1],
            indicators_full
        )

        # Verify scoring works despite missing indicators
        assert 0 <= score_short <= 100
        assert 0 <= score_full <= 100

        # Verify signals reflect missing indicators
        assert signals_short.price_above_sma50 is False  # Indicator unavailable → 0 points
        assert signals_short.price_above_ema20 in [True, False]  # Calculated

        # Create ticker scores and rank
        ticker_scores = [
            TickerScore(
                ticker=stock_short.ticker,
                bullish_score=score_short,
                signals=signals_short,
                current_price=stock_short.prices[-1],
                indicators={
                    "sma_50": indicators_short.sma_50,
                    "ema_20": indicators_short.ema_20,
                    "macd_line": indicators_short.macd_line,
                    "macd_signal": indicators_short.macd_signal,
                    "macd_histogram": indicators_short.macd_histogram,
                    "avg_volume_20": indicators_short.avg_volume_20,
                    "relative_strength": indicators_short.relative_strength
                }
            ),
            TickerScore(
                ticker=stock_full.ticker,
                bullish_score=score_full,
                signals=signals_full,
                current_price=stock_full.prices[-1],
                indicators={
                    "sma_50": indicators_full.sma_50,
                    "ema_20": indicators_full.ema_20,
                    "macd_line": indicators_full.macd_line,
                    "macd_signal": indicators_full.macd_signal,
                    "macd_histogram": indicators_full.macd_histogram,
                    "avg_volume_20": indicators_full.avg_volume_20,
                    "relative_strength": indicators_full.relative_strength
                }
            )
        ]

        ranked = ranker.rank_tickers(ticker_scores)

        # Verify ranking works with mixed indicators
        assert len(ranked) == 2
        assert ranked[0].bullish_score >= ranked[1].bullish_score

    def test_ranking_stability_with_tied_scores(self):
        """
        Test ranking preserves original order for tickers with identical scores.
        
        Requirement 6.2: When multiple tickers have identical Bullish_Score values, 
        the Ranking Service shall maintain their relative order from the original universe.
        """
        calculator = IndicatorCalculator()
        scorer = ScoringEngine()
        ranker = RankingService()

        # Create three stocks with identical price patterns (should produce same score)
        identical_prices = np.linspace(100, 120, 50)
        identical_volumes = np.full(50, 1_000_000)

        stock1 = StockData(
            ticker="AAA",
            prices=identical_prices.copy(),
            volumes=identical_volumes.copy(),
            timestamps=np.arange(50)
        )
        stock2 = StockData(
            ticker="BBB",
            prices=identical_prices.copy(),
            volumes=identical_volumes.copy(),
            timestamps=np.arange(50)
        )
        stock3 = StockData(
            ticker="CCC",
            prices=identical_prices.copy(),
            volumes=identical_volumes.copy(),
            timestamps=np.arange(50)
        )

        # Market data
        market_prices = np.linspace(100, 105, 50)
        market_data = StockData(
            ticker="SPY",
            prices=market_prices,
            volumes=np.full(50, 10_000_000),
            timestamps=np.arange(50)
        )

        # Calculate indicators for all (should be identical)
        indicators1 = calculator.calculate_all(stock1, market_data)
        indicators2 = calculator.calculate_all(stock2, market_data)
        indicators3 = calculator.calculate_all(stock3, market_data)

        # Score all (should be identical)
        score1, signals1 = scorer.calculate_score(
            stock1.prices[-1], stock1.volumes[-1], indicators1
        )
        score2, signals2 = scorer.calculate_score(
            stock2.prices[-1], stock2.volumes[-1], indicators2
        )
        score3, signals3 = scorer.calculate_score(
            stock3.prices[-1], stock3.volumes[-1], indicators3
        )

        # Verify scores are identical
        assert score1 == score2 == score3

        # Create ticker scores in specific order: AAA, BBB, CCC
        ticker_scores = [
            TickerScore(
                ticker="AAA",
                bullish_score=score1,
                signals=signals1,
                current_price=stock1.prices[-1],
                indicators={"sma_50": indicators1.sma_50}
            ),
            TickerScore(
                ticker="BBB",
                bullish_score=score2,
                signals=signals2,
                current_price=stock2.prices[-1],
                indicators={"sma_50": indicators2.sma_50}
            ),
            TickerScore(
                ticker="CCC",
                bullish_score=score3,
                signals=signals3,
                current_price=stock3.prices[-1],
                indicators={"sma_50": indicators3.sma_50}
            )
        ]

        # Rank tickers
        ranked = ranker.rank_tickers(ticker_scores)

        # Verify stable sort: original order preserved for tied scores
        assert len(ranked) == 3
        assert ranked[0].ticker == "AAA"
        assert ranked[1].ticker == "BBB"
        assert ranked[2].ticker == "CCC"
        assert ranked[0].bullish_score == ranked[1].bullish_score == ranked[2].bullish_score

    def test_ranking_with_mixed_scores_and_ties(self):
        """
        Test ranking with combination of different scores and ties.
        
        Verifies stable sort maintains order within tied groups while sorting overall.
        """
        ranker = RankingService()

        # Create ticker scores with some ties:
        # - Two tickers with score 85
        # - One ticker with score 70
        # - Two tickers with score 50
        from api.models import IndicatorSignals

        signals_high = IndicatorSignals(
            price_above_sma50=True,
            price_above_ema20=True,
            macd_above_signal=True,
            macd_histogram_positive=True,
            volume_above_average=True,
            relative_strength_positive=False
        )
        signals_mid = IndicatorSignals(
            price_above_sma50=True,
            price_above_ema20=True,
            macd_above_signal=True,
            macd_histogram_positive=False,
            volume_above_average=False,
            relative_strength_positive=True
        )
        signals_low = IndicatorSignals(
            price_above_sma50=True,
            price_above_ema20=True,
            macd_above_signal=False,
            macd_histogram_positive=False,
            volume_above_average=False,
            relative_strength_positive=False
        )

        ticker_scores = [
            TickerScore(ticker="FIRST85", bullish_score=85, signals=signals_high,
                       current_price=100.0, indicators={}),
            TickerScore(ticker="ONLY70", bullish_score=70, signals=signals_mid,
                       current_price=100.0, indicators={}),
            TickerScore(ticker="SECOND85", bullish_score=85, signals=signals_high,
                       current_price=100.0, indicators={}),
            TickerScore(ticker="FIRST50", bullish_score=50, signals=signals_low,
                       current_price=100.0, indicators={}),
            TickerScore(ticker="SECOND50", bullish_score=50, signals=signals_low,
                       current_price=100.0, indicators={}),
        ]

        # Rank
        ranked = ranker.rank_tickers(ticker_scores)

        # Verify correct ordering
        assert len(ranked) == 5

        # Top two should be 85s in original order
        assert ranked[0].ticker == "FIRST85"
        assert ranked[0].bullish_score == 85
        assert ranked[1].ticker == "SECOND85"
        assert ranked[1].bullish_score == 85

        # Middle should be 70
        assert ranked[2].ticker == "ONLY70"
        assert ranked[2].bullish_score == 70

        # Bottom two should be 50s in original order
        assert ranked[3].ticker == "FIRST50"
        assert ranked[3].bullish_score == 50
        assert ranked[4].ticker == "SECOND50"
        assert ranked[4].bullish_score == 50
