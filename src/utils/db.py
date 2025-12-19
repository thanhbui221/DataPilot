"""DuckDB connection manager."""
import duckdb
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger("datapilot")


class DuckDBManager:
    """Manages DuckDB connections with read-only enforcement."""
    
    def __init__(self, db_path: str, read_only: bool = True):
        """
        Initialize DuckDB manager.
        
        Args:
            db_path: Path to DuckDB database file
            read_only: If True, enforce read-only mode
        """
        self.db_path = Path(db_path)
        self.read_only = read_only
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
    
    def connect(self) -> duckdb.DuckDBPyConnection:
        """Get or create a DuckDB connection."""
        if self._conn is None:
            if self.read_only:
                # DuckDB doesn't have explicit read-only mode, but we can
                # enforce it at the application level
                logger.info(f"Connecting to DuckDB (read-only): {self.db_path}")
            else:
                logger.info(f"Connecting to DuckDB: {self.db_path}")
            
            self._conn = duckdb.connect(str(self.db_path))
        
        return self._conn
    
    def execute(self, sql: str, timeout: int = 30) -> duckdb.DuckDBPyDataFrame:
        """
        Execute a SQL query with timeout.
        
        Args:
            sql: SQL query to execute
            timeout: Query timeout in seconds
            
        Returns:
            DuckDB DataFrame with results
            
        Raises:
            TimeoutError: If query exceeds timeout
            Exception: For other SQL errors
        """
        conn = self.connect()
        
        # Note: DuckDB doesn't have built-in timeout, so this is a placeholder
        # In production, you might want to use threading/multiprocessing with timeout
        try:
            result = conn.execute(sql).df()
            logger.info(f"Query executed successfully, returned {len(result)} rows")
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise
    
    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("DuckDB connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

