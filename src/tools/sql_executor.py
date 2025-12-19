"""SQL Executor - Executes SQL queries using LangChain SQLDatabase tools."""
import pandas as pd
from typing import Dict, Any, Optional
from ..utils.db import DatabaseManager
import logging
import re

logger = logging.getLogger("datapilot")


class SQLExecutor:
    """Executes SQL queries using LangChain SQLDatabase tools."""
    
    def __init__(self, db_manager: DatabaseManager, llm, timeout: int = 30, max_rows: int = 5000):
        """
        Initialize SQL executor with LangChain tools.
        
        Args:
            db_manager: Database connection manager
            llm: LLM instance for tool creation
            timeout: Query timeout in seconds
            max_rows: Maximum rows to return
        """
        self.db_manager = db_manager
        self.timeout = timeout
        self.max_rows = max_rows
        self.llm = llm
        
        # Initialize tools (will be created on first use)
        self._tools = None
        self._query_tool = None
        self._schema_tool = None
        self._list_tables_tool = None
        self._query_checker_tool = None
        
        logger.info("SQL executor initialized (tools will be created on first use)")
    
    def _initialize_tools(self):
        """Initialize LangChain SQL tools."""
        if self._tools is None:
            from langchain_community.agent_toolkits import SQLDatabaseToolkit
            
            db = self.db_manager.get_db()
            toolkit = SQLDatabaseToolkit(db=db, llm=self.llm)
            self._tools = toolkit.get_tools()
            
            # Get specific tools
            self._query_tool = next(t for t in self._tools if t.name == "sql_db_query")
            self._schema_tool = next(t for t in self._tools if t.name == "sql_db_schema")
            self._list_tables_tool = next(t for t in self._tools if t.name == "sql_db_list_tables")
            self._query_checker_tool = next(t for t in self._tools if t.name == "sql_db_query_checker")
            
            logger.info("LangChain SQL tools initialized")
    
    def execute(self, sql: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute SQL query directly using pandas (more reliable than LangChain string parsing).
        
        Args:
            sql: SQL query to execute
            user_id: User ID for logging (optional)
            
        Returns:
            Result dictionary with:
            - success: bool
            - data: pandas DataFrame or None
            - row_count: int
            - execution_time: float (seconds)
            - error: str or None
        """
        import time
        start_time = time.time()
        
        try:
            # Ensure LIMIT is present (safety fallback)
            sql_with_limit = self._ensure_limit(sql)
            
            # Get database connection
            db = self.db_manager.get_db()
            
            # Execute query directly using pandas (more reliable)
            # SQLDatabase has a run() method that returns results
            result_str = db.run(sql_with_limit)
            
            # Parse the result string into DataFrame
            result_df = self._parse_result(result_str, sql_with_limit)
            
            # Apply row cap
            if result_df is not None and len(result_df) > self.max_rows:
                result_df = result_df.head(self.max_rows)
                logger.warning(f"Result capped to {self.max_rows} rows")
            
            execution_time = time.time() - start_time
            
            row_count = len(result_df) if result_df is not None else 0
            logger.info(f"Query executed successfully: {row_count} rows in {execution_time:.2f}s")
            
            return {
                "success": True,
                "data": result_df,
                "row_count": row_count,
                "execution_time": execution_time,
                "error": None
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = self._sanitize_error(str(e))
            
            logger.error(f"Query execution failed: {error_msg}", exc_info=True)
            
            return {
                "success": False,
                "data": None,
                "row_count": 0,
                "execution_time": execution_time,
                "error": error_msg
            }
    
    def _parse_result(self, result_str: str, sql: str) -> pd.DataFrame:
        """
        Parse LangChain SQL result string into DataFrame.
        
        LangChain returns results as string like:
        "[(1, 'value1'), (2, 'value2')]"
        or sometimes with column names in the format.
        """
        try:
            # Try to evaluate as Python literal
            import ast
            import re
            
            # Clean the result string - remove any extra whitespace
            result_str = result_str.strip()
            
            # Try parsing as Python literal (list of tuples)
            try:
                result_list = ast.literal_eval(result_str)
                
                if not result_list:
                    return pd.DataFrame()
                
                # Convert to DataFrame
                if isinstance(result_list, list) and len(result_list) > 0:
                    if isinstance(result_list[0], tuple):
                        # Try to get column names from SQL query
                        column_names = self._extract_column_names(sql)
                        if column_names:
                            return pd.DataFrame(result_list, columns=column_names)
                        else:
                            return pd.DataFrame(result_list)
                    else:
                        return pd.DataFrame(result_list)
                
                return pd.DataFrame()
                
            except (ValueError, SyntaxError):
                # If literal_eval fails, try to parse manually
                # Handle formats like: "country\ttotal_revenue\nUSA\t1000\nUK\t2000"
                if '\t' in result_str or '\n' in result_str:
                    # Try tab-separated format
                    lines = result_str.strip().split('\n')
                    if len(lines) > 1:
                        # First line might be headers
                        headers = lines[0].split('\t')
                        data = []
                        for line in lines[1:]:
                            if line.strip():
                                data.append(line.split('\t'))
                        if data:
                            return pd.DataFrame(data, columns=headers[:len(data[0])])
                
                # Last resort: return as single column
                logger.warning(f"Could not parse result format, returning as text. Result: {result_str[:200]}")
                return pd.DataFrame({"result": [result_str]})
            
        except Exception as e:
            logger.warning(f"Could not parse result as DataFrame: {str(e)}")
            logger.debug(f"Result string: {result_str[:500]}")
            # Return empty DataFrame with result as string in a column
            return pd.DataFrame({"result": [result_str]})
    
    def _extract_column_names(self, sql: str) -> Optional[list]:
        """Extract column names from SELECT statement."""
        try:
            # Simple regex to extract column names from SELECT ... FROM
            # This is a basic implementation
            match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
            if match:
                columns_str = match.group(1)
                # Split by comma and clean
                columns = [col.strip().split()[-1] for col in columns_str.split(',')]
                # Remove AS aliases
                columns = [col.split(' AS ')[-1].strip() if ' AS ' in col.upper() else col for col in columns]
                return columns
        except:
            pass
        return None
    
    def _ensure_limit(self, sql: str) -> str:
        """Ensure SQL has LIMIT clause (safety fallback)."""
        sql_upper = sql.upper().strip()
        # Check if it's a SELECT statement without LIMIT
        if sql_upper.startswith("SELECT") and "LIMIT" not in sql_upper:
            # Simple approach: append LIMIT
            # Note: This might break some queries, but it's a safety measure
            sql_clean = sql.rstrip(';').strip()
            return f"{sql_clean} LIMIT {self.max_rows}"
        return sql
    
    def _sanitize_error(self, error: str) -> str:
        """Sanitize error messages for user display."""
        # Remove internal details, keep only user-friendly messages
        # TODO: Implement better error sanitization
        return error
    
    def get_tools(self):
        """Get all SQL tools for agent use."""
        self._initialize_tools()
        return self._tools
