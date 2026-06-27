"""
Unit Tests for API Endpoints

Tests FastAPI route handlers including successful scans, validation errors,
retrieval, not found scenarios, and health checks.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException
from datetime import datetime

from api.endpoints import (
    router,
    health_check,
    scan,
    get_scan,
    get_orchestrator,
    get_scan_store
)
from api.models import (
    ScanRequest,
    ScanResponse,
    HealthResponse,
    MarketRegime,
    TickerScore,
    IndicatorSignals,
    ScanMetadata
)
from core.orchestrator import ScanError


@pytest.fixture
def sample_scan_request():
    """Create sample scan request."""
    return ScanRequest(tickers=["AAPL", "MSFT", "GOOGL"])


@pytest.fixture
def sample_scan_response():
    """Create sample scan response."""
    signals = IndicatorSignals(
        price_above_sma50=True,
        price_above_ema20=True,
        macd_above_signal=True,
        macd_histogram_positive=True,
        volume_above_average=False,
        relative_strength_positive=True
    )
    
    ticker_score = TickerScore(
        ticker="AAPL",
        bullish_score=85,
        signals=signals,
        current_price=178.50,
        indicators={
            "sma_50": 175.20,
            "ema_20": 177.80,
            "macd_line": 1.25,
            "macd_signal": 0.95,
            "macd_histogram": 0.30,
            "avg_volume_20": 52000000.0,
            "relative_strength": 2.5
        }
    )
    
    metadata = ScanMetadata(
        timestamp=datetime.utcnow(),
        ticker_count=1,
        duration_seconds=2.5
    )
    
    return ScanResponse(
        scan_id="test-uuid-1234",
        market_regime=MarketRegime.BULLISH,
        ranked_tickers=[ticker_score],
        metadata=metadata
    )


@pytest.fixture
def mock_orchestrator(sample_scan_response):
    """Create mock orchestrator."""
    orchestrator = Mock()
    orchestrator.execute_scan = AsyncMock(return_value=sample_scan_response)
    return orchestrator


@pytest.fixture
def mock_scan_store():
    """Create mock scan store."""
    store = Mock()
    store.save = AsyncMock()
    store.get = AsyncMock()
    return store


# ============================================================================
# Health Check Tests
# ============================================================================

@pytest.mark.asyncio
async def test_health_check_returns_healthy_status():
    """Test health check endpoint returns healthy status."""
    response = await health_check()
    
    assert isinstance(response, HealthResponse)
    assert response.status == "healthy"


# ============================================================================
# POST /scan Tests
# ============================================================================

@pytest.mark.asyncio
async def test_scan_successful_execution(
    sample_scan_request,
    sample_scan_response,
    mock_orchestrator,
    mock_scan_store
):
    """Test successful scan execution returns results and saves to store."""
    response = await scan(
        request=sample_scan_request,
        orchestrator=mock_orchestrator,
        scan_store=mock_scan_store
    )
    
    # Verify orchestrator was called with request
    mock_orchestrator.execute_scan.assert_called_once_with(sample_scan_request)
    
    # Verify result was saved
    mock_scan_store.save.assert_called_once_with(
        sample_scan_response.scan_id,
        sample_scan_response
    )
    
    # Verify response
    assert response == sample_scan_response
    assert response.scan_id == "test-uuid-1234"
    assert response.market_regime == MarketRegime.BULLISH
    assert len(response.ranked_tickers) == 1
    assert response.ranked_tickers[0].ticker == "AAPL"


@pytest.mark.asyncio
async def test_scan_handles_validation_error(
    sample_scan_request,
    mock_orchestrator,
    mock_scan_store
):
    """Test scan returns 400 for validation errors (invalid ticker list)."""
    # Mock orchestrator to raise ScanError with validation message
    mock_orchestrator.execute_scan.side_effect = ScanError(
        "Invalid ticker list: No valid tickers provided"
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await scan(
            request=sample_scan_request,
            orchestrator=mock_orchestrator,
            scan_store=mock_scan_store
        )
    
    assert exc_info.value.status_code == 400
    assert "Invalid ticker list" in exc_info.value.detail


@pytest.mark.asyncio
async def test_scan_handles_scan_error(
    sample_scan_request,
    mock_orchestrator,
    mock_scan_store
):
    """Test scan returns 500 for general scan errors."""
    # Mock orchestrator to raise ScanError without validation message
    mock_orchestrator.execute_scan.side_effect = ScanError(
        "Failed to fetch market data"
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await scan(
            request=sample_scan_request,
            orchestrator=mock_orchestrator,
            scan_store=mock_scan_store
        )
    
    assert exc_info.value.status_code == 500
    assert "Failed to fetch market data" in exc_info.value.detail


@pytest.mark.asyncio
async def test_scan_handles_value_error(
    sample_scan_request,
    mock_orchestrator,
    mock_scan_store
):
    """Test scan returns 400 for ValueError from universe builder."""
    # Mock orchestrator to raise ValueError
    mock_orchestrator.execute_scan.side_effect = ValueError(
        "All tickers are invalid"
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await scan(
            request=sample_scan_request,
            orchestrator=mock_orchestrator,
            scan_store=mock_scan_store
        )
    
    assert exc_info.value.status_code == 400
    assert "Invalid ticker list" in exc_info.value.detail
    assert "All tickers are invalid" in exc_info.value.detail


@pytest.mark.asyncio
async def test_scan_handles_unexpected_error(
    sample_scan_request,
    mock_orchestrator,
    mock_scan_store
):
    """Test scan returns 500 for unexpected errors."""
    # Mock orchestrator to raise unexpected exception
    mock_orchestrator.execute_scan.side_effect = RuntimeError(
        "Unexpected database error"
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await scan(
            request=sample_scan_request,
            orchestrator=mock_orchestrator,
            scan_store=mock_scan_store
        )
    
    assert exc_info.value.status_code == 500
    assert "Scan failed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_scan_saves_result_after_successful_execution(
    sample_scan_request,
    sample_scan_response,
    mock_orchestrator,
    mock_scan_store
):
    """Test scan persists result to database after successful execution."""
    await scan(
        request=sample_scan_request,
        orchestrator=mock_orchestrator,
        scan_store=mock_scan_store
    )
    
    # Verify save was called with correct arguments
    mock_scan_store.save.assert_called_once()
    call_args = mock_scan_store.save.call_args
    assert call_args[0][0] == sample_scan_response.scan_id
    assert call_args[0][1] == sample_scan_response


# ============================================================================
# GET /scan/{scan_id} Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_scan_successful_retrieval(
    sample_scan_response,
    mock_scan_store
):
    """Test successful scan retrieval returns stored result."""
    scan_id = "test-uuid-1234"
    mock_scan_store.get.return_value = sample_scan_response
    
    response = await get_scan(
        scan_id=scan_id,
        scan_store=mock_scan_store
    )
    
    # Verify store was queried
    mock_scan_store.get.assert_called_once_with(scan_id)
    
    # Verify response
    assert response == sample_scan_response
    assert response.scan_id == scan_id


@pytest.mark.asyncio
async def test_get_scan_returns_404_when_not_found(mock_scan_store):
    """Test get_scan returns 404 when scan ID not found."""
    scan_id = "nonexistent-uuid"
    mock_scan_store.get.return_value = None
    
    with pytest.raises(HTTPException) as exc_info:
        await get_scan(
            scan_id=scan_id,
            scan_store=mock_scan_store
        )
    
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()
    assert scan_id in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_scan_handles_database_error(mock_scan_store):
    """Test get_scan returns 500 for database errors."""
    scan_id = "test-uuid-1234"
    mock_scan_store.get.side_effect = RuntimeError("Database connection failed")
    
    with pytest.raises(HTTPException) as exc_info:
        await get_scan(
            scan_id=scan_id,
            scan_store=mock_scan_store
        )
    
    assert exc_info.value.status_code == 500
    assert "Failed to retrieve scan" in exc_info.value.detail


# ============================================================================
# Dependency Injection Tests
# ============================================================================

def test_get_orchestrator_creates_valid_instance():
    """Test get_orchestrator creates orchestrator with all dependencies."""
    orchestrator = get_orchestrator()
    
    # Verify it's the right type
    from core.orchestrator import ScanOrchestrator
    assert isinstance(orchestrator, ScanOrchestrator)
    
    # Verify dependencies are set
    assert orchestrator.api_client is not None
    assert orchestrator.universe_builder is not None
    assert orchestrator.regime_analyzer is not None
    assert orchestrator.indicator_calc is not None
    assert orchestrator.scoring_engine is not None
    assert orchestrator.ranking_service is not None


@pytest.mark.asyncio
async def test_get_scan_store_initializes_database():
    """Test get_scan_store creates and initializes store."""
    # Reset global store
    import api.endpoints
    api.endpoints._scan_store = None
    
    store = await get_scan_store()
    
    # Verify it's the right type
    from core.scan_store import ScanStore
    assert isinstance(store, ScanStore)
    
    # Verify subsequent calls return same instance
    store2 = await get_scan_store()
    assert store is store2


# ============================================================================
# Integration-Style Tests (verifying request/response flow)
# ============================================================================

@pytest.mark.asyncio
async def test_scan_endpoint_validates_empty_ticker_list(
    mock_orchestrator,
    mock_scan_store
):
    """Test scan endpoint rejects empty ticker list via Pydantic validation."""
    # This test verifies Pydantic's min_length validation
    # In practice, FastAPI would reject this before reaching the handler
    # But we test the handler's error handling for consistency
    
    with pytest.raises(Exception):  # Pydantic will raise ValidationError
        invalid_request = ScanRequest(tickers=[])


@pytest.mark.asyncio
async def test_complete_scan_flow(
    sample_scan_request,
    sample_scan_response,
    mock_orchestrator,
    mock_scan_store
):
    """Test complete flow: request → orchestration → persistence → response."""
    # Execute scan
    response = await scan(
        request=sample_scan_request,
        orchestrator=mock_orchestrator,
        scan_store=mock_scan_store
    )
    
    # Verify complete flow
    assert mock_orchestrator.execute_scan.called
    assert mock_scan_store.save.called
    assert response.scan_id == sample_scan_response.scan_id
    assert response.market_regime == MarketRegime.BULLISH
    assert len(response.ranked_tickers) > 0


@pytest.mark.asyncio
async def test_retrieve_flow(
    sample_scan_response,
    mock_scan_store
):
    """Test complete retrieval flow: scan_id → query → response."""
    scan_id = "test-uuid-1234"
    mock_scan_store.get.return_value = sample_scan_response
    
    # Retrieve scan
    response = await get_scan(
        scan_id=scan_id,
        scan_store=mock_scan_store
    )
    
    # Verify complete flow
    assert mock_scan_store.get.called
    assert response.scan_id == scan_id
    assert response.market_regime == MarketRegime.BULLISH
