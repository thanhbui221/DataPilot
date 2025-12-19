"""SQL Executor - Executes read-only SQL queries safely."""
import pandas as pd
from typing import Dict, Any, Optional
from ..utils.db import DuckDBManager
import logging

logger = logging.getLogger("datapilot")


class SQLExecutor:
    """Executes SQL queries with safety constraints."""
    
    def __init__(self, db_manager: DuckDBManager, timeout: int = 30, max_rows: int = 5000):
        """
        Initialize SQL executor.
        
        Args:
            db_manager: DuckDB connection manager
            timeout: Query timeout in seconds
            max_rows: Maximum rows to return
        """
        self.db_manager = db_manager
        self.timeout = timeout
        self.max_rows = max_rows
    
    def execute(self, sql: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute SQL query safely.
        
        Args:
            sql: SQL query to execute
            user_id: User ID for logging (optional)
            
        Returns:
            Result dictionary with:
            - success: bool
            - data: DataFrame or None
            - row_count: int
            - execution_time: float (seconds)
            - error: str or None
        """
        import time
        start_time = time.time()
        
        try:
            # Ensure LIMIT is present (safety fallback)
            sql_with_limit = self._ensure_limit(sql)
            
            # Execute query
            result_df = self.db_manager.execute(sql_with_limit, timeout=self.timeout)
            
            # Apply row cap
            if len(result_df) > self.max_rows:
                result_df = result_df.head(self.max_rows)
                logger.warning(f"Result capped to {self.max_rows} rows")
            
            execution_time = time.time() - start_time
            
            logger.info(f"Query executed successfully: {len(result_df)} rows in {execution_time:.2f}s")
            
            return {
                "success": True,
                "data": result_df,
                "row_count": len(result_df),
                "execution_time": execution_time,
                "error": None
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = self._sanitize_error(str(e))
            
            logger.error(f"Query execution failed: {error_msg}")
            
            return {
                "success": False,
                "data": None,
                "row_count": 0,
                "execution_time": execution_time,
                "error": error_msg
            }
    
    def _ensure_limit(self, sql: str) -> str:
        """Ensure SQL has LIMIT clause (safety fallback)."""
        sql_upper = sql.upper()
        if "LIMIT" not in sql_upper:
            # Simple approach: append LIMIT
            # Note: This might break some queries, but it's a safety measure
            return f"{sql.rstrip(';')} LIMIT {self.max_rows}"
        return sql
    
    def _sanitize_error(self, error: str) -> str:
        """Sanitize error messages for user display."""
        # Remove internal details, keep only user-friendly messages
        # TODO: Implement better error sanitization
        return error

