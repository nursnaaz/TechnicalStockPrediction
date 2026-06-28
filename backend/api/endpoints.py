"""
API Endpoints

Defines all REST API routes for the Bullish Stock Scanner.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from api.models import ScanRequest, ScanResponse, HealthResponse
from core.orchestrator import ScanOrchestrator, ScanError
from core.scan_store import ScanStore
from core.api_client import RestApiClient
from core.universe_builder import UniverseBuilder
from core.regime_analyzer import MarketRegimeAnalyzer
from core.indicator_calculator import IndicatorCalculator
from core.scoring_engine import ScoringEngine
from core.ranking_service import RankingService
from config import config
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Global scan store instance (initialized on startup)
_scan_store: ScanStore = None


async def get_scan_store() -> ScanStore:
    """Dependency injection for scan store."""
    global _scan_store
    if _scan_store is None:
        _scan_store = ScanStore(db_path=config.DB_PATH)
        await _scan_store.initialize()
        logger.info(f"ScanStore initialized with database: {config.DB_PATH}")
    return _scan_store


def get_orchestrator() -> ScanOrchestrator:
    """
    Dependency injection for scan orchestrator.
    
    Creates a new orchestrator instance with all required dependencies.
    """
    # Initialize components
    api_client = RestApiClient(
        api_key=config.POLYGON_TOKEN,
        base_url=config.API_BASE_URL,
        max_concurrent=config.MAX_CONCURRENT_REQUESTS,
        max_retries=config.MAX_RETRIES
    )
    
    universe_builder = UniverseBuilder()
    regime_analyzer = MarketRegimeAnalyzer(api_client)
    indicator_calc = IndicatorCalculator()
    scoring_engine = ScoringEngine()
    ranking_service = RankingService()
    
    # Create and return orchestrator
    return ScanOrchestrator(
        api_client=api_client,
        universe_builder=universe_builder,
        regime_analyzer=regime_analyzer,
        indicator_calc=indicator_calc,
        scoring_engine=scoring_engine,
        ranking_service=ranking_service
    )


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        HealthResponse indicating service is running
    """
    return HealthResponse(status="healthy")


@router.post("/scan", response_model=ScanResponse, tags=["scan"])
async def scan(
    request: ScanRequest,
    orchestrator: ScanOrchestrator = Depends(get_orchestrator),
    scan_store: ScanStore = Depends(get_scan_store)
):
    """
    Execute a stock scan.
    
    Args:
        request: ScanRequest with list of ticker symbols
        orchestrator: Injected ScanOrchestrator instance
        scan_store: Injected ScanStore instance
        
    Returns:
        ScanResponse with market regime, ranked tickers, and metadata
        
    Raises:
        HTTPException: 400 if validation fails, 500 if scan fails
    """
    logger.info(f"Scan requested for {len(request.tickers)} tickers: {request.tickers}")
    
    try:
        # Execute the scan
        # include_all -> return the whole scanned universe (candidates + below-threshold
        # + hard-filter failures) with status flags, instead of candidates only.
        response = await orchestrator.execute_scan(
            request, apply_signal_gate=not request.include_all
        )
        
        # Persist the result
        await scan_store.save(response.scan_id, response)
        logger.info(f"Scan {response.scan_id} saved to database")
        
        return response
        
    except ScanError as e:
        logger.error(f"Scan failed: {e}")
        # Check if it's a validation error (empty ticker list)
        if "Invalid ticker list" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    except ValueError as e:
        # Validation errors from universe builder
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ticker list: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during scan: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan failed: {str(e)}"
        )


@router.get("/scan/{scan_id}", response_model=ScanResponse, tags=["scan"])
async def get_scan(
    scan_id: str,
    scan_store: ScanStore = Depends(get_scan_store)
):
    """
    Retrieve a previously completed scan result.
    
    Args:
        scan_id: UUID of the scan to retrieve
        scan_store: Injected ScanStore instance
        
    Returns:
        ScanResponse with the stored scan results
        
    Raises:
        HTTPException: 404 if scan not found
    """
    logger.info(f"Retrieving scan: {scan_id}")
    
    try:
        result = await scan_store.get(scan_id)
        
        if result is None:
            logger.warning(f"Scan {scan_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scan result not found for ID: {scan_id}"
            )
        
        logger.info(f"Scan {scan_id} retrieved successfully")
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error retrieving scan {scan_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scan: {str(e)}"
        )
