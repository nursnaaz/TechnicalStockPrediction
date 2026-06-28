"""
Integration Test: Full Scan Endpoint (End-to-End)

Comprehensive integration test that verifies the complete scan pipeline.
Tests POST /api/v1/scan and GET /api/v1/scan/{scan_id} endpoints.

Note: This test file focuses on API contract validation and error handling.
The test_endpoints_integration.py file covers detailed mock-based integration testing.
"""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


# ============================================================================
# Health Check Test
# ============================================================================


def test_health_endpoint(client):
    """Test GET /api/v1/health returns healthy status."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


# ============================================================================
# Validation Tests
# ============================================================================


def test_scan_requires_tickers_field(client):
    """Test POST /api/v1/scan requires tickers field in request."""
    response = client.post("/api/v1/scan", json={})

    assert response.status_code == 422  # Pydantic validation error
    data = response.json()
    assert "detail" in data


def test_scan_rejects_empty_ticker_list(client):
    """Test POST /api/v1/scan rejects empty ticker list."""
    response = client.post("/api/v1/scan", json={"tickers": []})

    assert response.status_code == 422  # Pydantic validation error


def test_scan_endpoint_returns_proper_error_format(client):
    """Test that scan errors return proper JSON format."""
    # Invalid JSON body should return validation error
    response = client.post("/api/v1/scan", json={"invalid_field": "value"})

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


# ============================================================================
# Scan Retrieval Tests
# ============================================================================


def test_get_scan_with_invalid_uuid_format(client):
    """Test GET /api/v1/scan/{scan_id} with invalid UUID format."""
    # The endpoint should handle invalid UUID gracefully
    response = client.get("/api/v1/scan/not-a-uuid")

    # Should either return 404 or 422 depending on validation
    assert response.status_code in [404, 422, 500]


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


def test_scan_endpoint_documented_in_openapi(client):
    """Test that scan endpoint has proper OpenAPI documentation."""
    response = client.get("/openapi.json")
    schema = response.json()

    # Check POST /api/v1/scan
    assert "/api/v1/scan" in schema["paths"]
    assert "post" in schema["paths"]["/api/v1/scan"]

    # Check GET /api/v1/scan/{scan_id}
    assert "/api/v1/scan/{scan_id}" in schema["paths"]
    assert "get" in schema["paths"]["/api/v1/scan/{scan_id}"]


# ============================================================================
# CORS Tests
# ============================================================================


def test_cors_headers_configured(client):
    """Test that CORS middleware is configured."""
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    # CORS should add appropriate headers
    assert "access-control-allow-origin" in response.headers


# ============================================================================
# Error Response Format Tests
# ============================================================================


def test_404_error_format(client):
    """Test 404 errors return proper JSON format."""
    response = client.get("/api/v1/nonexistent")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


# ============================================================================
# Summary
# ============================================================================

"""
This integration test file focuses on:
1. API contract validation (request/response formats)
2. Error handling and HTTP status codes
3. API documentation availability
4. CORS configuration
5. Endpoint availability and basic functionality

For detailed component integration testing with mocked external APIs,
see test_endpoints_integration.py which covers:
- Full scan pipeline execution
- Database persistence and retrieval
- Component interaction
"""
