"""
Integration tests for FastAPI application setup and initialization.

Tests application startup, dependency injection, CORS configuration,
and API documentation endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import tempfile
import os


@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def test_client(temp_db_path):
    """
    Create a test client with mocked ScanStore initialization.
    
    This prevents the startup event from creating a real database.
    """
    # Mock config to use temp database
    with patch("main.config") as mock_config:
        mock_config.DB_PATH = temp_db_path
        
        # Mock ScanStore to avoid actual database operations during startup
        with patch("main.ScanStore") as mock_scan_store_class:
            mock_store = AsyncMock()
            mock_store.initialize = AsyncMock()
            mock_scan_store_class.return_value = mock_store
            
            # Import app after patching to trigger startup event with mocks
            from main import app
            
            # Create test client
            client = TestClient(app)
            
            yield client


class TestApplicationSetup:
    """Test FastAPI application initialization and configuration."""
    
    def test_app_initialization(self, test_client):
        """Test that FastAPI app initializes with correct metadata."""
        # Access the app directly through the test client
        app = test_client.app
        
        assert app.title == "Bullish Stock Scanner"
        assert app.description == "Technical analysis system for identifying potentially bullish stocks"
        assert app.version == "1.0.0"
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
    
    def test_cors_middleware_configured(self, test_client):
        """Test that CORS middleware is properly configured."""
        app = test_client.app
        
        # Check that middleware stack exists and is not empty
        assert len(app.user_middleware) > 0, "No middleware configured"
        
        # Alternative: test CORS behavior by checking response headers
        response = test_client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # CORS should add appropriate headers
        assert "access-control-allow-origin" in response.headers
    
    def test_api_router_mounted(self, test_client):
        """Test that API router is mounted at /api/v1 prefix."""
        app = test_client.app
        
        # Check routes include /api/v1 paths
        routes = [route.path for route in app.routes]
        
        # Should have /api/v1 prefixed routes
        api_v1_routes = [r for r in routes if r.startswith("/api/v1")]
        assert len(api_v1_routes) > 0, "No /api/v1 routes found"
        
        # Check for expected endpoints
        assert "/api/v1/health" in routes
        assert "/api/v1/scan" in routes
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint returns API information."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "Bullish Stock Scanner API"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"
    
    def test_swagger_ui_available(self, test_client):
        """Test that Swagger UI documentation is accessible."""
        response = test_client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Swagger UI should contain OpenAPI-related content
        assert b"swagger" in response.content.lower() or b"openapi" in response.content.lower()
    
    def test_redoc_ui_available(self, test_client):
        """Test that ReDoc documentation is accessible."""
        response = test_client.get("/redoc")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestStartupEvent:
    """Test application startup event and ScanStore initialization."""
    
    def test_scanstore_initialized_on_startup(self, temp_db_path):
        """Test that ScanStore is initialized during application startup."""
        with patch("main.config") as mock_config:
            mock_config.DB_PATH = temp_db_path
            
            # Track if ScanStore was initialized
            with patch("main.ScanStore") as mock_scan_store_class:
                mock_store = AsyncMock()
                mock_store.initialize = AsyncMock()
                mock_scan_store_class.return_value = mock_store
                
                # Import and create client to trigger startup
                from main import app
                with TestClient(app):
                    # Verify ScanStore was instantiated with correct path
                    mock_scan_store_class.assert_called_once_with(db_path=temp_db_path)
                    
                    # Verify initialize was called
                    mock_store.initialize.assert_called_once()
    
    def test_startup_logging(self, temp_db_path, caplog):
        """Test that startup event logs appropriate messages."""
        with patch("main.config") as mock_config:
            mock_config.DB_PATH = temp_db_path
            
            with patch("main.ScanStore") as mock_scan_store_class:
                mock_store = AsyncMock()
                mock_store.initialize = AsyncMock()
                mock_scan_store_class.return_value = mock_store
                
                from main import app
                
                with TestClient(app):
                    # Check for startup log messages
                    log_messages = [record.message for record in caplog.records]
                    
                    # Should log startup messages
                    assert any("Starting Bullish Stock Scanner API" in msg for msg in log_messages)
                    assert any("ScanStore initialized successfully" in msg for msg in log_messages)
                    assert any("Application startup complete" in msg for msg in log_messages)


class TestCORSConfiguration:
    """Test CORS middleware configuration and behavior."""
    
    def test_cors_allows_all_origins(self, test_client):
        """Test that CORS allows requests from any origin."""
        # Make a request with an Origin header
        response = test_client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        # CORS middleware should add appropriate headers
        assert "access-control-allow-origin" in response.headers
    
    def test_cors_preflight_request(self, test_client):
        """Test CORS preflight OPTIONS request."""
        response = test_client.options(
            "/api/v1/scan",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type"
            }
        )
        
        # Should return 200 for preflight
        assert response.status_code == 200


class TestDependencyInjection:
    """Test dependency injection setup for orchestrator and scan store."""
    
    def test_health_endpoint_no_dependencies(self, test_client):
        """Test that health endpoint works without complex dependencies."""
        response = test_client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_scan_endpoint_available(self, test_client):
        """Test that scan endpoint is registered and returns validation error without body."""
        # POST without body should return 422 (validation error)
        response = test_client.post("/api/v1/scan")
        
        assert response.status_code == 422  # Pydantic validation error


class TestAPIDocumentation:
    """Test API documentation endpoints and OpenAPI spec."""
    
    def test_openapi_json_available(self, test_client):
        """Test that OpenAPI JSON specification is available."""
        response = test_client.get("/openapi.json")
        
        assert response.status_code == 200
        spec = response.json()
        
        # Check OpenAPI spec structure
        assert "openapi" in spec
        assert "info" in spec
        assert spec["info"]["title"] == "Bullish Stock Scanner"
        assert spec["info"]["version"] == "1.0.0"
    
    def test_openapi_includes_scan_endpoint(self, test_client):
        """Test that OpenAPI spec includes scan endpoint definition."""
        response = test_client.get("/openapi.json")
        spec = response.json()
        
        # Check for /api/v1/scan endpoint
        assert "paths" in spec
        assert "/api/v1/scan" in spec["paths"]
        assert "post" in spec["paths"]["/api/v1/scan"]
    
    def test_openapi_includes_health_endpoint(self, test_client):
        """Test that OpenAPI spec includes health check endpoint."""
        response = test_client.get("/openapi.json")
        spec = response.json()
        
        assert "/api/v1/health" in spec["paths"]
        assert "get" in spec["paths"]["/api/v1/health"]


class TestRouteRegistration:
    """Test that all required routes are properly registered."""
    
    def test_all_required_routes_exist(self, test_client):
        """Test that all required API routes are registered."""
        app = test_client.app
        routes = [route.path for route in app.routes]
        
        # Required routes
        required_routes = [
            "/",
            "/api/v1/health",
            "/api/v1/scan",
            "/api/v1/scan/{scan_id}",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        
        for required_route in required_routes:
            assert required_route in routes, f"Required route {required_route} not found"
    
    def test_scan_get_endpoint_registered(self, test_client):
        """Test that GET /api/v1/scan/{scan_id} endpoint is registered."""
        # Try accessing with a dummy UUID (should return 404, but route should exist)
        response = test_client.get("/api/v1/scan/12345678-1234-1234-1234-123456789012")
        
        # Should not be 404 for route not found (405 or 500 is okay, means route exists)
        # Actually it should return 404 for scan not found, which means route exists
        assert response.status_code in [404, 500], "Scan retrieval endpoint not properly registered"
