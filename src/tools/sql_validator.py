"""SQL Validator & Cost Guard - Validates SQL safety and estimates cost."""
import sqlglot
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("datapilot")


class SQLValidator:
    """Validates SQL queries for safety and estimates cost."""
    
    def __init__(self, max_estimated_rows: int = 10000, 
                 require_limit: bool = True,
                 require_partition_filter: bool = True):
        """
        Initialize SQL validator.
        
        Args:
            max_estimated_rows: Maximum allowed estimated rows
            require_limit: Whether to require LIMIT clause for non-aggregated queries
            require_partition_filter: Whether to require partition filter
        """
        self.max_estimated_rows = max_estimated_rows
        self.require_limit = require_limit
        self.require_partition_filter = require_partition_filter
    
    def validate(self, sql: str, partition_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate SQL query for safety.
        
        Args:
            sql: SQL query to validate
            partition_key: Partition key column (e.g., "orders.created_at")
            
        Returns:
            Validation result dict with:
            - approved: bool
            - reason: str (if not approved)
            - estimated_rows: int or None
            - estimated_cost: str or None
            - warnings: list of warning strings
        """
        try:
            # Parse SQL
            parsed = sqlglot.parse_one(sql)
            
            # Check 1: Only SELECT allowed
            if not self._is_select_only(parsed):
                return {
                    "approved": False,
                    "reason": "Only SELECT statements are allowed",
                    "estimated_rows": None,
                    "estimated_cost": None,
                    "warnings": []
                }
            
            # Check 2: No SELECT *
            if self._has_select_star(parsed):
                return {
                    "approved": False,
                    "reason": "SELECT * is not allowed. Please specify columns explicitly",
                    "estimated_rows": None,
                    "estimated_cost": None,
                    "warnings": []
                }
            
            # Check 3: No cross joins
            if self._has_cross_join(parsed):
                return {
                    "approved": False,
                    "reason": "Cross joins are not allowed",
                    "estimated_rows": None,
                    "estimated_cost": None,
                    "warnings": []
                }
            
            # Check 4: LIMIT required for non-aggregated queries
            if self.require_limit and not self._is_aggregated(parsed) and not self._has_limit(parsed):
                return {
                    "approved": False,
                    "reason": "LIMIT clause required for non-aggregated queries",
                    "estimated_rows": None,
                    "estimated_cost": None,
                    "warnings": []
                }
            
            # Check 5: Partition filter required
            if self.require_partition_filter and partition_key:
                if not self._has_partition_filter(parsed, partition_key):
                    return {
                        "approved": False,
                        "reason": f"Time filter required on partitioned column: {partition_key}",
                        "estimated_rows": None,
                        "estimated_cost": None,
                        "warnings": []
                    }
            
            # Check 6: Subqueries must have LIMIT
            if self._has_unlimited_subquery(parsed):
                return {
                    "approved": False,
                    "reason": "Subqueries must include LIMIT clause",
                    "estimated_rows": None,
                    "estimated_cost": None,
                    "warnings": []
                }
            
            # Estimate cost (placeholder)
            estimated_rows = self._estimate_rows(parsed)
            warnings = []
            
            if estimated_rows and estimated_rows > self.max_estimated_rows:
                warnings.append(f"Query may return large number of rows (~{estimated_rows})")
            
            return {
                "approved": True,
                "estimated_rows": estimated_rows,
                "estimated_cost": "low" if not estimated_rows or estimated_rows < 1000 else "medium",
                "warnings": warnings
            }
            
        except sqlglot.errors.ParseError as e:
            return {
                "approved": False,
                "reason": f"SQL parse error: {str(e)}",
                "estimated_rows": None,
                "estimated_cost": None,
                "warnings": []
            }
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return {
                "approved": False,
                "reason": f"Validation error: {str(e)}",
                "estimated_rows": None,
                "estimated_cost": None,
                "warnings": []
            }
    
    def _is_select_only(self, parsed) -> bool:
        """Check if query is SELECT only."""
        return isinstance(parsed, sqlglot.expressions.Select)
    
    def _has_select_star(self, parsed) -> bool:
        """Check if query uses SELECT *."""
        if isinstance(parsed, sqlglot.expressions.Select):
            expressions = parsed.expressions or []
            for expression in expressions:
                if isinstance(expression, sqlglot.expressions.Star):
                    return True
        return False
    
    def _has_cross_join(self, parsed) -> bool:
        """Check if query has cross joins."""
        # TODO: Implement cross join detection
        return False
    
    def _is_aggregated(self, parsed) -> bool:
        """Check if query uses aggregation functions."""
        if isinstance(parsed, sqlglot.expressions.Select):
            # Check for GROUP BY - sqlglot uses 'group' key in args
            group_by = parsed.args.get("group")
            if group_by and group_by.expressions:
                return True
            
            # Check for aggregate functions in SELECT
            expressions = parsed.expressions or []
            for expr in expressions:
                expr_str = str(expr)
                # Check for aggregate function calls
                if any(func in expr_str.upper() for func in ['SUM(', 'COUNT(', 'AVG(', 'MAX(', 'MIN(', 'GROUP_CONCAT(']):
                    return True
                # Also check if expression is an aggregate function
                if isinstance(expr, (sqlglot.expressions.AggFunc, sqlglot.expressions.Count, 
                                    sqlglot.expressions.Sum, sqlglot.expressions.Avg,
                                    sqlglot.expressions.Max, sqlglot.expressions.Min)):
                    return True
        return False
    
    def _has_limit(self, parsed) -> bool:
        """Check if query has LIMIT clause."""
        if isinstance(parsed, sqlglot.expressions.Select):
            return parsed.args.get("limit") is not None
        return False
    
    def _has_partition_filter(self, parsed, partition_key: str) -> bool:
        """Check if query filters on partition key."""
        # Simple check: look for partition key in WHERE clause
        if isinstance(parsed, sqlglot.expressions.Select):
            where_str = str(parsed.args.get("where", ""))
            return partition_key.split(".")[-1] in where_str.lower()
        return False
    
    def _has_unlimited_subquery(self, parsed) -> bool:
        """Check if subqueries have LIMIT."""
        # TODO: Implement subquery LIMIT checking
        return False
    
    def _estimate_rows(self, parsed) -> Optional[int]:
        """Estimate number of rows (placeholder)."""
        # TODO: Implement row estimation using SQL EXPLAIN or sampling
        return None

