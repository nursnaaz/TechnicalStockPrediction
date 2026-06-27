"""
Scan Store

Persistence layer for storing and retrieving completed scan results using SQLite.
"""

import aiosqlite
import json
from typing import Optional
from datetime import datetime
from api.models import ScanResponse


class ScanStore:
    """Persists and retrieves completed scan results."""

    def __init__(self, db_path: str = "scanner.db"):
        """
        Initialize with SQLite database path.
        
        Args:
            db_path: Path to SQLite database file (default: scanner.db)
        """
        self.db_path = db_path

    async def initialize(self) -> None:
        """
        Create table if not exists. Called on app startup.
        
        Creates the scan_results table with schema:
        - scan_id TEXT PRIMARY KEY
        - result_json TEXT NOT NULL
        - created_at TEXT NOT NULL
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS scan_results (
                    scan_id TEXT PRIMARY KEY,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            await db.commit()

    async def save(self, scan_id: str, result: ScanResponse) -> None:
        """
        Persist a completed scan result.
        
        Args:
            scan_id: UUID for the scan
            result: Complete scan response to persist
            
        Raises:
            aiosqlite.IntegrityError: If scan_id already exists
        """
        # Serialize ScanResponse to JSON
        result_json = result.model_dump_json()
        created_at = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO scan_results (scan_id, result_json, created_at) VALUES (?, ?, ?)",
                (scan_id, result_json, created_at)
            )
            await db.commit()

    async def get(self, scan_id: str) -> Optional[ScanResponse]:
        """
        Retrieve a scan result by ID.
        
        Args:
            scan_id: UUID of the scan to retrieve
            
        Returns:
            ScanResponse if found, None otherwise
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT result_json FROM scan_results WHERE scan_id = ?",
                (scan_id,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row is None:
                    return None
                
                # Deserialize JSON to ScanResponse
                result_dict = json.loads(row[0])
                return ScanResponse(**result_dict)
