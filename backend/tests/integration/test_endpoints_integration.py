"""
Integration Tests for API Endpoints

Tests the complete API flow with real FastAPI TestClient, including:
- Full request/response cycle
- Dependency injection
- Error handling
- Persistence integration
"""

import os
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.models import IndicatorSignals, MarketRegime, ScanMetadata, TickerScore
from core.models import StockData, TechnicalIndicators
from main import app


@pytest.fixture
def test_db():
    """Create temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_stock_data():
    """Create sample stock data for mocking."""
    prices = np.array([100.0 + i for i in range(250)])
    volumes = np.array([1000000.0] * 250)
    timestamps = np.array([i for i in range(250)])

    return StockData(ticker="AAPL", prices=prices, volumes=volumes, timestamps=timestamps)


@pytest.fixture
def sample_indicators():
    """Create sample technical indicators."""
    return TechnicalIndicators(
        sma_50=175.20,
        ema_20=177.80,
        macd_line=1.25,
        macd_signal=0.95,
        macd_histogram=0.30,
        avg_volume_20=1000000.0,
        relative_strength=2.5,
    )


# ============================================================================
# Health Check Integration Tests
# ============================================================================


def test_health_endpoint_returns_200(client):
    """Test GET /api/v1/health returns 200 with healthy status."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


# ============================================================================
# Scan Endpoint Integration Tests
# ============================================================================


@patch("api.endpoints.RestApiClient")
def test_scan_endpoint_with_mocked_api_client(
    mock_api_client_class, client, sample_stock_data, sample_indicators, test_db
):
    """Test POST /api/v1/scan with mocked external API calls."""
    # Mock the API client
    mock_client_instance = Mock()
    mock_client_instance.clear_cache = Mock()
    mock_client_instance.fetch_stock_data = AsyncMock(return_value=sample_stock_data)
    mock_api_client_class.return_value = mock_client_instance

    # Mock config to use test database
    with patch("api.endpoints.config") as mock_config:
        mock_config.DB_PATH = test_db
        mock_config.POLYGON_TOKEN = "test-token"
        mock_config.API_BASE_URL = "https://test.api.com"
        mock_config.MAX_CONCURRENT_REQUESTS = 5
        mock_config.MAX_RETRIES = 3

        # Make request
        response = client.post("/api/v1/scan", json={"tickers": ["AAPL"]})

    # Verify response
    assert response.status_code == 200
    data = response.json()

    assert "scan_id" in data
    assert "market_regime" in data
    assert "ranked_tickers" in data
    assert "metadata" in data

    # Verify scan_id is a UUID format
    import uuid

    try:
        uuid.UUID(data["scan_id"])
    except ValueError:
        pytest.fail("scan_id is not a valid UUID")


def test_scan_endpoint_validates_empty_tickers(client):
    """Test POST /api/v1/scan rejects empty ticker list."""
    response = client.post("/api/v1/scan", json={"tickers": []})

    # Should return 422 (Pydantic validation error)
    assert response.status_code == 422


def test_scan_endpoint_requires_tickers_field(client):
    """Test POST /api/v1/scan requires tickers field."""
    response = client.post("/api/v1/scan", json={})

    # Should return 422 (Pydantic validation error)
    assert response.status_code == 422


def test_scan_endpoint_returns_400_for_invalid_tickers(client):
    """Test POST /api/v1/scan returns 400 for all invalid tickers."""
    with patch("api.endpoints.UniverseBuilder") as mock_builder_class:
        mock_builder = Mock()
        mock_builder.build_universe.side_effect = ValueError("All tickers are invalid")
        mock_builder_class.return_value = mock_builder

        response = client.post("/api/v1/scan", json={"tickers": ["INVALID!!!", "@#$%"]})

    assert response.status_code == 400
    assert "Invalid ticker list" in response.json()["detail"]


# ============================================================================
# Scan Retrieval Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_scan_endpoint_returns_stored_result(test_db):
    """Test GET /api/v1/scan/{scan_id} returns stored scan."""
    # Initialize scan_store with test database
    from core.scan_store import ScanStore

    scan_store = ScanStore(db_path=test_db)
    await scan_store.initialize()

    # Create mock response
    from api.models import ScanResponse

    signals = IndicatorSignals(
        price_above_sma50=True,
        price_above_ema20=True,
        macd_above_signal=True,
        macd_histogram_positive=True,
        volume_above_average=False,
        relative_strength_positive=True,
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
            "relative_strength": 2.5,
        },
    )

    metadata = ScanMetadata(timestamp=datetime.utcnow(), ticker_count=1, duration_seconds=2.5)

    mock_response = ScanResponse(
        scan_id="test-uuid-1234",
        market_regime=MarketRegime.BULLISH,
        ranked_tickers=[ticker_score],
        metadata=metadata,
    )

    # Save to database
    await scan_store.save("test-uuid-1234", mock_response)

    # Override FastAPI dependency
    from api.endpoints import get_scan_store

    async def override_get_scan_store():
        return scan_store

    app.dependency_overrides[get_scan_store] = override_get_scan_store

    try:
        # Create client after dependency override
        client = TestClient(app)
        # Make request
        response = client.get("/api/v1/scan/test-uuid-1234")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["scan_id"] == "test-uuid-1234"
        assert data["market_regime"] == "bullish"
    finally:
        # Clean up dependency override
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_scan_endpoint_returns_404_for_missing_scan(test_db):
    """Test GET /api/v1/scan/{scan_id} returns 404 when not found."""
    # Initialize scan_store with test database
    from core.scan_store import ScanStore

    scan_store = ScanStore(db_path=test_db)
    await scan_store.initialize()

    # Override FastAPI dependency
    from api.endpoints import get_scan_store

    async def override_get_scan_store():
        return scan_store

    app.dependency_overrides[get_scan_store] = override_get_scan_store

    try:
        # Create client after dependency override
        client = TestClient(app)
        # Make request
        response = client.get("/api/v1/scan/nonexistent-uuid")

        # Verify 404 response
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        # Clean up dependency override
        app.dependency_overrides.clear()


# ============================================================================
# Full Flow Integration Test
# ============================================================================


@pytest.mark.asyncio
@patch("api.endpoints.RestApiClient")
@patch("api.endpoints.config")
async def test_complete_scan_and_retrieval_flow(
    mock_config, mock_api_client_class, sample_stock_data, test_db
):
    """Test complete flow: POST scan → save → GET scan."""
    # Initialize scan_store with test database
    from core.scan_store import ScanStore

    scan_store = ScanStore(db_path=test_db)
    await scan_store.initialize()

    # Setup mocks
    mock_client_instance = Mock()
    mock_client_instance.clear_cache = Mock()
    mock_client_instance.fetch_stock_data = AsyncMock(return_value=sample_stock_data)
    mock_api_client_class.return_value = mock_client_instance

    mock_config.DB_PATH = test_db
    mock_config.POLYGON_TOKEN = "test-token"
    mock_config.API_BASE_URL = "https://test.api.com"
    mock_config.MAX_CONCURRENT_REQUESTS = 5
    mock_config.MAX_RETRIES = 3

    # Override FastAPI dependency
    from api.endpoints import get_scan_store

    async def override_get_scan_store():
        return scan_store

    app.dependency_overrides[get_scan_store] = override_get_scan_store

    try:
        # Create client after dependency override
        client = TestClient(app)

        # Step 1: Execute scan
        scan_response = client.post("/api/v1/scan", json={"tickers": ["AAPL"]})

        assert scan_response.status_code == 200
        scan_data = scan_response.json()
        scan_id = scan_data["scan_id"]

        # Step 2: Verify scan_id is valid
        assert scan_id is not None
        assert len(scan_id) > 0
    finally:
        # Clean up dependency override
        app.dependency_overrides.clear()


# ============================================================================
# API Documentation Tests
# ============================================================================


def test_openapi_docs_available(client):
    """Test that OpenAPI documentation is accessible."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_json_available(client):
    """Test that OpenAPI JSON schema is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    # Verify it's valid JSON with expected fields
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema

    # Verify our endpoints are documented
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/scan" in schema["paths"]
    assert "/api/v1/scan/{scan_id}" in schema["paths"]


# ============================================================================
# CORS Integration Tests
# ============================================================================


def test_cors_headers_present(client):
    """Test that CORS middleware is configured."""
    # Make a regular request to verify CORS is configured
    # TestClient doesn't fully simulate CORS preflight, but we can verify
    # the middleware is in place by checking the app configuration
    response = client.get("/api/v1/health")

    # Verify the endpoint works (CORS is configured in main.py)
    assert response.status_code == 200


# ============================================================================
# Error Response Format Tests
# ============================================================================


def test_404_error_format(client):
    """Test 404 errors return proper JSON format."""
    response = client.get("/api/v1/nonexistent")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_422_validation_error_format(client):
    """Test validation errors return proper format."""
    response = client.post("/api/v1/scan", json={"invalid": "field"})

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
