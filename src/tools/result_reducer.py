"""Result Reducer Tool - Prepares compact, LLM-friendly result summaries."""
import pandas as pd
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("datapilot")


class ResultReducer:
    """Reduces query results to compact summaries for LLM processing."""
    
    def __init__(self, max_sample_rows: int = 20):
        """
        Initialize result reducer.
        
        Args:
            max_sample_rows: Maximum rows to include in sample
        """
        self.max_sample_rows = max_sample_rows
    
    def reduce(self, df: pd.DataFrame, 
              comparison_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Reduce DataFrame to compact summary.
        
        Args:
            df: Query result DataFrame
            comparison_data: Optional comparison DataFrame for % change calculation
            
        Returns:
            Reduced result dictionary with:
            - row_count: Total number of rows
            - summary: Aggregated statistics
            - top_breakdown: Top N breakdown by first dimension
            - sample: Sample of rows (up to max_sample_rows)
        """
        if df is None or df.empty:
            return {
                "row_count": 0,
                "summary": {},
                "top_breakdown": [],
                "sample": []
            }
        
        row_count = len(df)
        
        # Calculate summary statistics
        summary = self._calculate_summary(df)
        
        # Get top breakdown (if multiple columns, use first as dimension)
        top_breakdown = self._get_top_breakdown(df)
        
        # Get sample
        sample = self._get_sample(df)
        
        # Calculate % change if comparison data provided
        if comparison_data is not None and not comparison_data.empty:
            summary["comparison_change_pct"] = self._calculate_change(df, comparison_data)
        
        result = {
            "row_count": row_count,
            "summary": summary,
            "top_breakdown": top_breakdown,
            "sample": sample
        }
        
        logger.info(f"Reduced {row_count} rows to summary")
        return result
    
    def _calculate_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate summary statistics."""
        summary = {}
        
        # Find numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if numeric_cols:
            for col in numeric_cols:
                summary[f"{col}_sum"] = float(df[col].sum())
                summary[f"{col}_avg"] = float(df[col].mean())
                summary[f"{col}_min"] = float(df[col].min())
                summary[f"{col}_max"] = float(df[col].max())
        
        return summary
    
    def _get_top_breakdown(self, df: pd.DataFrame, top_n: int = 10) -> list:
        """Get top N breakdown by first column."""
        if df.empty:
            return []
        
        # Use first column as dimension
        dimension_col = df.columns[0]
        
        # If there are numeric columns, calculate share
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if numeric_cols:
            value_col = numeric_cols[0]
            total = df[value_col].sum()
            
            top = df.nlargest(top_n, value_col)
            breakdown = []
            for _, row in top.iterrows():
                breakdown.append({
                    dimension_col: str(row[dimension_col]),
                    value_col: float(row[value_col]),
                    "share": float(row[value_col] / total) if total > 0 else 0.0
                })
            return breakdown
        else:
            # Just return top N rows
            top = df.head(top_n)
            return top.to_dict('records')
    
    def _get_sample(self, df: pd.DataFrame) -> list:
        """Get sample of rows."""
        if df.empty:
            return []
        
        sample_df = df.head(self.max_sample_rows)
        return sample_df.to_dict('records')
    
    def _calculate_change(self, current: pd.DataFrame, previous: pd.DataFrame) -> Optional[float]:
        """Calculate percentage change between current and previous data."""
        # Simple implementation: compare totals
        numeric_cols = current.select_dtypes(include=['number']).columns.tolist()
        if not numeric_cols:
            return None
        
        value_col = numeric_cols[0]
        current_total = current[value_col].sum()
        previous_total = previous[value_col].sum()
        
        if previous_total == 0:
            return None
        
        change_pct = ((current_total - previous_total) / previous_total) * 100
        return round(change_pct, 2)

