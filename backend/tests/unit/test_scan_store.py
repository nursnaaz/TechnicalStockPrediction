"""
Unit Tests for Scan Store

Tests for SQLite persistence of completed scan results.
"""

import os
import tempfile
from datetime import datetime

import pytest

from api.models import IndicatorSignals, MarketRegime, ScanMetadata, ScanResponse, TickerScore
from core.scan_store import ScanStore


@pytest.fixture
def temp_db():
    """Yield a temporary database file path, removed on teardown.

    Sync fixture on purpose: it does no async work, so making it ``async`` risked
    pytest-asyncio handing tests the generator object instead of the path.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
async def store(temp_db):
    """Create and initialize a ScanStore instance."""
    store = ScanStore(db_path=temp_db)
    await store.initialize()
    return store


@pytest.fixture
def sample_scan_response():
    """Create a sample ScanResponse for testing."""
    return ScanResponse(
        scan_id="test-scan-123",
        market_regime=MarketRegime.BULLISH,
        ranked_tickers=[
            TickerScore(
                ticker="AAPL",
                bullish_score=85,
                signals=IndicatorSignals(
                    price_above_sma50=True,
                    price_above_ema20=True,
                    macd_above_signal=True,
                    macd_histogram_positive=True,
                    volume_above_average=False,
                    relative_strength_positive=True,
                ),
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
            ),
            TickerScore(
                ticker="MSFT",
                bullish_score=70,
                signals=IndicatorSignals(
                    price_above_sma50=True,
                    price_above_ema20=True,
                    macd_above_signal=True,
                    macd_histogram_positive=False,
                    volume_above_average=False,
                    relative_strength_positive=True,
                ),
                current_price=350.00,
                indicators={
                    "sma_50": 340.00,
                    "ema_20": 345.00,
                    "macd_line": 0.50,
                    "macd_signal": 0.45,
                    "macd_histogram": 0.05,
                    "avg_volume_20": 30000000.0,
                    "relative_strength": 1.8,
                },
            ),
        ],
        metadata=ScanMetadata(
            timestamp=datetime(2024, 1, 15, 10, 30, 0), ticker_count=2, duration_seconds=2.5
        ),
    )


class TestScanStoreInitialization:
    """Tests for ScanStore initialization and table creation."""

    @pytest.mark.asyncio
    async def test_initialize_creates_table(self, temp_db):
        """Test that initialize creates the scan_results table."""
        store = ScanStore(db_path=temp_db)
        await store.initialize()

        # Verify table exists by querying sqlite_master
        import aiosqlite

        async with aiosqlite.connect(temp_db) as db:
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='scan_results'"
            ) as cursor:
                result = await cursor.fetchone()
                assert result is not None
                assert result[0] == "scan_results"

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, temp_db):
        """Test that initialize can be called multiple times without error."""
        store = ScanStore(db_path=temp_db)
        await store.initialize()
        await store.initialize()  # Should not raise error

        # Verify table still exists
        import aiosqlite

        async with aiosqlite.connect(temp_db) as db:
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='scan_results'"
            ) as cursor:
                result = await cursor.fetchone()
                assert result is not None


class TestScanStoreSave:
    """Tests for saving scan results."""

    @pytest.mark.asyncio
    async def test_save_scan_result(self, store, sample_scan_response):
        """Test saving a scan result to the database."""
        scan_id = "test-scan-456"
        await store.save(scan_id, sample_scan_response)

        # Verify the record was saved
        import aiosqlite

        async with aiosqlite.connect(store.db_path) as db:
            async with db.execute(
                "SELECT scan_id, result_json, created_at FROM scan_results WHERE scan_id = ?",
                (scan_id,),
            ) as cursor:
                row = await cursor.fetchone()
                assert row is not None
                assert row[0] == scan_id
                assert row[1] is not None  # JSON data exists
                assert row[2] is not None  # created_at exists

    @pytest.mark.asyncio
    async def test_save_duplicate_scan_id_raises_error(self, store, sample_scan_response):
        """Test that saving with duplicate scan_id raises IntegrityError."""
        scan_id = "duplicate-scan-789"
        await store.save(scan_id, sample_scan_response)

        # Try to save again with same scan_id
        import aiosqlite

        with pytest.raises(aiosqlite.IntegrityError):
            await store.save(scan_id, sample_scan_response)

    @pytest.mark.asyncio
    async def test_save_multiple_scans(self, store, sample_scan_response):
        """Test saving multiple different scan results."""
        scan_id_1 = "scan-001"
        scan_id_2 = "scan-002"

        await store.save(scan_id_1, sample_scan_response)
        await store.save(scan_id_2, sample_scan_response)

        # Verify both were saved
        import aiosqlite

        async with aiosqlite.connect(store.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM scan_results") as cursor:
                count = await cursor.fetchone()
                assert count[0] == 2


class TestScanStoreGet:
    """Tests for retrieving scan results."""

    @pytest.mark.asyncio
    async def test_get_existing_scan(self, store, sample_scan_response):
        """Test retrieving an existing scan result."""
        scan_id = "retrieve-test-123"
        await store.save(scan_id, sample_scan_response)

        # Retrieve the scan
        result = await store.get(scan_id)

        assert result is not None
        assert isinstance(result, ScanResponse)
        assert result.scan_id == sample_scan_response.scan_id
        assert result.market_regime == sample_scan_response.market_regime
        assert len(result.ranked_tickers) == len(sample_scan_response.ranked_tickers)
        assert result.metadata.ticker_count == sample_scan_response.metadata.ticker_count

    @pytest.mark.asyncio
    async def test_get_nonexistent_scan_returns_none(self, store):
        """Test that retrieving a non-existent scan returns None."""
        result = await store.get("nonexistent-scan-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_preserves_ticker_data(self, store, sample_scan_response):
        """Test that retrieved data matches saved data exactly."""
        scan_id = "data-integrity-test"
        await store.save(scan_id, sample_scan_response)

        result = await store.get(scan_id)

        # Check first ticker in detail
        original_ticker = sample_scan_response.ranked_tickers[0]
        retrieved_ticker = result.ranked_tickers[0]

        assert retrieved_ticker.ticker == original_ticker.ticker
        assert retrieved_ticker.bullish_score == original_ticker.bullish_score
        assert retrieved_ticker.current_price == original_ticker.current_price
        assert (
            retrieved_ticker.signals.price_above_sma50 == original_ticker.signals.price_above_sma50
        )
        assert (
            retrieved_ticker.signals.macd_above_signal == original_ticker.signals.macd_above_signal
        )
        assert retrieved_ticker.indicators["sma_50"] == original_ticker.indicators["sma_50"]

    @pytest.mark.asyncio
    async def test_get_with_empty_database(self, store):
        """Test retrieving from an empty database returns None."""
        result = await store.get("any-scan-id")
        assert result is None


class TestScanStoreRoundTrip:
    """Tests for complete save and retrieve cycles."""

    @pytest.mark.asyncio
    async def test_roundtrip_serialization(self, store, sample_scan_response):
        """Test that data survives serialization/deserialization."""
        scan_id = "roundtrip-test"

        # Save
        await store.save(scan_id, sample_scan_response)

        # Retrieve
        result = await store.get(scan_id)

        # Verify complete equality
        assert result.model_dump() == sample_scan_response.model_dump()

    @pytest.mark.asyncio
    async def test_roundtrip_with_market_regimes(self, store):
        """Test that different market regimes are preserved."""
        for regime in [MarketRegime.BULLISH, MarketRegime.BEARISH, MarketRegime.NEUTRAL]:
            scan_id = f"regime-test-{regime.value}"
            response = ScanResponse(
                scan_id=scan_id,
                market_regime=regime,
                ranked_tickers=[],
                metadata=ScanMetadata(
                    timestamp=datetime.utcnow(), ticker_count=0, duration_seconds=0.1
                ),
            )

            await store.save(scan_id, response)
            result = await store.get(scan_id)

            assert result.market_regime == regime
