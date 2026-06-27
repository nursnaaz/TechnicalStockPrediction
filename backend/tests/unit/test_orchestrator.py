"""
Unit Tests for Scan Orchestrator

Tests pipeline execution, error handling, and response formatting.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import numpy as np

from core.orchestrator import ScanOrchestrator, ScanError
from core.api_client import RestApiClient, ApiError
from core.universe_builder import UniverseBuilder
from core.regime_analyzer import MarketRegimeAnalyzer
from core.indicator_calculator import IndicatorCalculator
from core.scoring_engine import ScoringEngine
from core.ranking_service import RankingService
from api.models import (
    ScanRequest,
    MarketRegime,
    IndicatorSignals,
    TickerScore
)
from core.models import StockData, TechnicalIndicators


@pytest.fixture
def mock_api_client():
    """Create mock API client."""
    client = Mock(spec=RestApiClient)
    client.clear_cache = Mock()
    client.fetch_stock_data = AsyncMock()
    return client


@pytest.fixture
def mock_universe_builder():
    """Create mock universe builder."""
    builder = Mock(spec=UniverseBuilder)
    builder.build_universe = Mock()
    return builder


@pytest.fixture
def mock_regime_analyzer():
    """Create mock regime analyzer."""
    analyzer = Mock(spec=MarketRegimeAnalyzer)
    analyzer.analyze_regime = AsyncMock()
    return analyzer


@pytest.fixture
def mock_indicator_calc():
    """Create mock indicator calculator."""
    calc = Mock(spec=IndicatorCalculator)
    calc.calculate_all = Mock()
    return calc


@pytest.fixture
def mock_scoring_engine():
    """Create mock scoring engine."""
    engine = Mock(spec=ScoringEngine)
    engine.calculate_score = Mock()
    return engine


@pytest.fixture
def mock_ranking_service():
    """Create mock ranking service."""
    service = Mock(spec=RankingService)
    service.rank_tickers = Mock()
    return service


@pytest.fixture
def orchestrator(
    mock_api_client,
    mock_universe_builder,
    mock_regime_analyzer,
    mock_indicator_calc,
    mock_scoring_engine,
    mock_ranking_service
):
    """Create orchestrator with all mocked dependencies."""
    return ScanOrchestrator(
        api_client=mock_api_client,
        universe_builder=mock_universe_builder,
        regime_analyzer=mock_regime_analyzer,
        indicator_calc=mock_indicator_calc,
        scoring_engine=mock_scoring_engine,
        ranking_service=mock_ranking_service
    )


@pytest.fixture
def sample_stock_data():
    """Create sample stock data."""
    return StockData(
        ticker="AAPL",
        prices=np.array([100.0, 101.0, 102.0] * 100),  # 300 days
        volumes=np.array([1000000.0, 1100000.0, 1200000.0] * 100),
        timestamps=np.array([1640000000, 1640086400, 1640172800] * 100)
    )


@pytest.fixture
def sample_indicators():
    """Create sample technical indicators."""
    return TechnicalIndicators(
        sma_50=100.0,
        ema_20=101.0,
        macd_line=0.5,
        macd_signal=0.3,
        macd_histogram=0.2,
        avg_volume_20=1000000.0,
        relative_strength=2.5
    )


class TestOrchestratorInitialization:
    """Test orchestrator initialization."""
    
    def test_initialization_success(self, orchestrator):
        """Test successful initialization with all dependencies."""
        assert orchestrator.api_client is not None
        assert orchestrator.universe_builder is not None
        assert orchestrator.regime_analyzer is not None
        assert orchestrator.indicator_calc is not None
        assert orchestrator.scoring_engine is not None
        assert orchestrator.ranking_service is not None


class TestExecuteScan:
    """Test execute_scan method."""
    
    @pytest.mark.asyncio
    async def test_successful_scan_single_ticker(
        self,
        orchestrator,
        mock_api_client,
        mock_universe_builder,
        mock_regime_analyzer,
        mock_indicator_calc,
        mock_scoring_engine,
        mock_ranking_service,
        sample_stock_data,
        sample_indicators
    ):
        """Test successful scan with single ticker."""
        # Setup mocks
        mock_universe_builder.build_universe.return_value = ["AAPL"]
        mock_regime_analyzer.analyze_regime.return_value = MarketRegime.BULLISH
        mock_api_client.fetch_stock_data.return_value = sample_stock_data
        mock_indicator_calc.calculate_all.return_value = sample_indicators
        
        signals = IndicatorSignals(
            price_above_sma50=True,
            price_above_ema20=True,
            macd_above_signal=True,
            macd_histogram_positive=True,
            volume_above_average=False,
            relative_strength_positive=True
        )
        mock_scoring_engine.calculate_score.return_value = (85, signals)
        
        # Mock ranking service to return input as-is
        mock_ranking_service.rank_tickers.side_effect = lambda x: x
        
        # Execute scan
        request = ScanRequest(tickers=["AAPL"])
        response = await orchestrator.execute_scan(request)
        
        # Verify cache was cleared
        mock_api_client.clear_cache.assert_called_once()
        
        # Verify universe was built
        mock_universe_builder.build_universe.assert_called_once_with(["AAPL"])
        
        # Verify regime was analyzed
        mock_regime_analyzer.analyze_regime.assert_called_once()
        
        # Verify market data was fetched (SPY)
        spy_call = [call for call in mock_api_client.fetch_stock_data.call_args_list 
                    if call[0][0] == "SPY"]
        assert len(spy_call) == 1
        
        # Verify ticker data was fetched
        aapl_call = [call for call in mock_api_client.fetch_stock_data.call_args_list 
                     if call[0][0] == "AAPL"]
        assert len(aapl_call) == 1
        
        # Verify indicators were calculated
        mock_indicator_calc.calculate_all.assert_called_once()
        
        # Verify score was calculated
        mock_scoring_engine.calculate_score.assert_called_once()
        
        # Verify ranking was performed
        mock_ranking_service.rank_tickers.assert_called_once()
        
        # Verify response structure
        assert response.scan_id is not None
        assert len(response.scan_id) == 36  # UUID format
        assert response.market_regime == MarketRegime.BULLISH
        assert len(response.ranked_tickers) == 1
        assert response.ranked_tickers[0].ticker == "AAPL"
        assert response.ranked_tickers[0].bullish_score == 85
        assert response.metadata.ticker_count == 1
        assert response.metadata.duration_seconds >= 0
    
    @pytest.mark.asyncio
    async def test_successful_scan_multiple_tickers(
        self,
        orchestrator,
        mock_api_client,
        mock_universe_builder,
        mock_regime_analyzer,
        mock_indicator_calc,
        mock_scoring_engine,
        mock_ranking_service,
        sample_stock_data,
        sample_indicators
    ):
        """Test successful scan with multiple tickers."""
        # Setup mocks
        tickers = ["AAPL", "MSFT", "GOOGL"]
        mock_universe_builder.build_universe.return_value = tickers
        mock_regime_analyzer.analyze_regime.return_value = MarketRegime.NEUTRAL
        mock_api_client.fetch_stock_data.return_value = sample_stock_data
        mock_indicator_calc.calculate_all.return_value = sample_indicators
        
        signals = IndicatorSignals(
            price_above_sma50=True,
            price_above_ema20=True,
            macd_above_signal=True,
            macd_histogram_positive=True,
            volume_above_average=True,
            relative_strength_positive=True
        )
        mock_scoring_engine.calculate_score.return_value = (100, signals)
        
        # Mock ranking service to return sorted by score
        mock_ranking_service.rank_tickers.side_effect = lambda x: sorted(
            x, key=lambda t: t.bullish_score, reverse=True
        )
        
        # Execute scan
        request = ScanRequest(tickers=tickers)
        response = await orchestrator.execute_scan(request)
        
        # Verify all tickers were processed
        assert len(response.ranked_tickers) == 3
        assert response.metadata.ticker_count == 3
        assert {t.ticker for t in response.ranked_tickers} == set(tickers)
    
    @pytest.mark.asyncio
    async def test_scan_with_invalid_universe(
        self,
        orchestrator,
        mock_universe_builder
    ):
        """Test scan fails when universe building fails."""
        # Setup mock to raise ValueError
        mock_universe_builder.build_universe.side_effect = ValueError("All tickers are invalid")
        
        # Execute scan and expect ScanError
        request = ScanRequest(tickers=["!!!"])
        with pytest.raises(ScanError, match="Invalid ticker list"):
            await orchestrator.execute_scan(request)
    
    @pytest.mark.asyncio
    async def test_scan_handles_single_ticker_failure(
        self,
        orchestrator,
        mock_api_client,
        mock_universe_builder,
        mock_regime_analyzer,
        mock_indicator_calc,
        mock_scoring_engine,
        mock_ranking_service,
        sample_stock_data,
        sample_indicators
    ):
        """Test scan continues when single ticker fails."""
        # Setup mocks
        tickers = ["AAPL", "INVALID", "GOOGL"]
        mock_universe_builder.build_universe.return_value = tickers
        mock_regime_analyzer.analyze_regime.return_value = MarketRegime.BULLISH
        
        # Make INVALID ticker fail
        def fetch_side_effect(ticker, days=250, as_of_date=None):
            if ticker == "INVALID":
                raise ApiError(f"Failed to fetch {ticker}")
            return sample_stock_data
        
        mock_api_client.fetch_stock_data.side_effect = fetch_side_effect
        mock_indicator_calc.calculate_all.return_value = sample_indicators
        
        signals = IndicatorSignals(
            price_above_sma50=True,
            price_above_ema20=True,
            macd_above_signal=True,
            macd_histogram_positive=True,
            volume_above_average=False,
            relative_strength_positive=True
        )
        mock_scoring_engine.calculate_score.return_value = (85, signals)
        mock_ranking_service.rank_tickers.side_effect = lambda x: x
        
        # Execute scan
        request = ScanRequest(tickers=tickers)
        response = await orchestrator.execute_scan(request)
        
        # Verify only valid tickers were processed
        assert len(response.ranked_tickers) == 2
        assert all(t.ticker != "INVALID" for t in response.ranked_tickers)
    
    @pytest.mark.asyncio
    async def test_scan_fails_when_all_tickers_fail(
        self,
        orchestrator,
        mock_api_client,
        mock_universe_builder,
        mock_regime_analyzer
    ):
        """Test scan fails when all tickers fail to process."""
        # Setup mocks
        mock_universe_builder.build_universe.return_value = ["AAPL", "MSFT"]
        mock_regime_analyzer.analyze_regime.return_value = MarketRegime.BULLISH
        
        # Make all ticker fetches fail after SPY succeeds
        def fetch_side_effect(ticker, days=250, as_of_date=None):
            if ticker == "SPY":
                return StockData(
                    ticker="SPY",
                    prices=np.array([100.0] * 300),
                    volumes=np.array([1000000.0] * 300),
                    timestamps=np.array([1640000000] * 300)
                )
            raise ApiError(f"Failed to fetch {ticker}")
        
        mock_api_client.fetch_stock_data.side_effect = fetch_side_effect
        
        # Execute scan and expect ScanError
        request = ScanRequest(tickers=["AAPL", "MSFT"])
        with pytest.raises(ScanError, match="All tickers failed to process"):
            await orchestrator.execute_scan(request)
    
    @pytest.mark.asyncio
    async def test_scan_fails_when_market_data_unavailable(
        self,
        orchestrator,
        mock_api_client,
        mock_universe_builder,
        mock_regime_analyzer
    ):
        """Test scan fails when SPY market data cannot be fetched."""
        # Setup mocks
        mock_universe_builder.build_universe.return_value = ["AAPL"]
        mock_regime_analyzer.analyze_regime.return_value = MarketRegime.NEUTRAL
        
        # Make SPY fetch fail
        mock_api_client.fetch_stock_data.side_effect = ApiError("Failed to fetch SPY")
        
        # Execute scan and expect ScanError
        request = ScanRequest(tickers=["AAPL"])
        with pytest.raises(ScanError, match="Unable to fetch market data"):
            await orchestrator.execute_scan(request)
    
    @pytest.mark.asyncio
    async def test_scan_generates_unique_scan_id(
        self,
        orchestrator,
        mock_api_client,
        mock_universe_builder,
        mock_regime_analyzer,
        mock_indicator_calc,
        mock_scoring_engine,
        mock_ranking_service,
        sample_stock_data,
        sample_indicators
    ):
        """Test each scan generates a unique UUID."""
        # Setup mocks
        mock_universe_builder.build_universe.return_value = ["AAPL"]
        mock_regime_analyzer.analyze_regime.return_value = MarketRegime.BULLISH
        mock_api_client.fetch_stock_data.return_value = sample_stock_data
        mock_indicator_calc.calculate_all.return_value = sample_indicators
        
        signals = IndicatorSignals(
            price_above_sma50=True,
            price_above_ema20=True,
            macd_above_signal=True,
            macd_histogram_positive=True,
            volume_above_average=False,
            relative_strength_positive=True
        )
        mock_scoring_engine.calculate_score.return_value = (85, signals)
        mock_ranking_service.rank_tickers.side_effect = lambda x: x
        
        # Execute two scans
        request = ScanRequest(tickers=["AAPL"])
        response1 = await orchestrator.execute_scan(request)
        response2 = await orchestrator.execute_scan(request)
        
        # Verify scan IDs are unique
        assert response1.scan_id != response2.scan_id
        assert len(response1.scan_id) == 36
        assert len(response2.scan_id) == 36
    
    @pytest.mark.asyncio
    async def test_scan_metadata_accuracy(
        self,
        orchestrator,
        mock_api_client,
        mock_universe_builder,
        mock_regime_analyzer,
        mock_indicator_calc,
        mock_scoring_engine,
        mock_ranking_service,
        sample_stock_data,
        sample_indicators
    ):
        """Test scan metadata is accurate."""
        # Setup mocks
        tickers = ["AAPL", "MSFT"]
        mock_universe_builder.build_universe.return_value = tickers
        mock_regime_analyzer.analyze_regime.return_value = MarketRegime.BEARISH
        mock_api_client.fetch_stock_data.return_value = sample_stock_data
        mock_indicator_calc.calculate_all.return_value = sample_indicators
        
        signals = IndicatorSignals(
            price_above_sma50=False,
            price_above_ema20=False,
            macd_above_signal=False,
            macd_histogram_positive=False,
            volume_above_average=False,
            relative_strength_positive=False
        )
        mock_scoring_engine.calculate_score.return_value = (0, signals)
        mock_ranking_service.rank_tickers.side_effect = lambda x: x
        
        # Execute scan
        request = ScanRequest(tickers=tickers)
        response = await orchestrator.execute_scan(request)
        
        # Verify metadata
        assert response.metadata.ticker_count == 2
        assert response.metadata.duration_seconds >= 0
        assert response.metadata.duration_seconds < 10  # Should be fast with mocks
        assert isinstance(response.metadata.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_cache_cleared_at_scan_start(
        self,
        orchestrator,
        mock_api_client,
        mock_universe_builder,
        mock_regime_analyzer,
        mock_indicator_calc,
        mock_scoring_engine,
        mock_ranking_service,
        sample_stock_data,
        sample_indicators
    ):
        """Test API cache is cleared at the start of each scan."""
        # Setup mocks
        mock_universe_builder.build_universe.return_value = ["AAPL"]
        mock_regime_analyzer.analyze_regime.return_value = MarketRegime.BULLISH
        mock_api_client.fetch_stock_data.return_value = sample_stock_data
        mock_indicator_calc.calculate_all.return_value = sample_indicators
        
        signals = IndicatorSignals(
            price_above_sma50=True,
            price_above_ema20=True,
            macd_above_signal=True,
            macd_histogram_positive=True,
            volume_above_average=False,
            relative_strength_positive=True
        )
        mock_scoring_engine.calculate_score.return_value = (85, signals)
        mock_ranking_service.rank_tickers.side_effect = lambda x: x
        
        # Execute scan
        request = ScanRequest(tickers=["AAPL"])
        await orchestrator.execute_scan(request)
        
        # Verify cache was cleared before any API calls
        mock_api_client.clear_cache.assert_called_once()
        # clear_cache should be first call before fetch_stock_data
        assert mock_api_client.method_calls[0][0] == 'clear_cache'


class TestErrorHandling:
    """Test error handling in orchestrator."""
    
    @pytest.mark.asyncio
    async def test_unexpected_error_raises_scan_error(
        self,
        orchestrator,
        mock_universe_builder
    ):
        """Test unexpected errors are wrapped in ScanError."""
        # Setup mock to raise unexpected error
        mock_universe_builder.build_universe.side_effect = RuntimeError("Unexpected error")
        
        # Execute scan and expect ScanError
        request = ScanRequest(tickers=["AAPL"])
        with pytest.raises(ScanError, match="unexpected error"):
            await orchestrator.execute_scan(request)
