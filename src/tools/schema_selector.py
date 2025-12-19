"""Schema Selector Tool - Returns relevant schema slice for SQL generation."""
import json
from pathlib import Path
from typing import Dict, Any, List, Set
import logging

logger = logging.getLogger("datapilot")


class SchemaSelector:
    """Selects relevant schema based on metric and dimensions."""
    
    def __init__(self, schema_path: str, metrics_path: str):
        """
        Initialize schema selector.
        
        Args:
            schema_path: Path to schema.json
            metrics_path: Path to metrics.yaml
        """
        self.schema_path = Path(schema_path)
        self.metrics_path = Path(metrics_path)
        self._schema = None
        self._metrics = None
        self._load_metadata()
    
    def _load_metadata(self):
        """Load schema and metrics from files."""
        # Load schema
        with open(self.schema_path, 'r') as f:
            self._schema = json.load(f)
        
        # Load metrics (YAML)
        import yaml
        with open(self.metrics_path, 'r') as f:
            self._metrics = yaml.safe_load(f)
        
        logger.info("Metadata loaded successfully")
    
    def select_schema(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select relevant schema based on intent.
        
        Args:
            intent: Structured intent with 'metric' and 'dimensions' keys
            
        Returns:
            Schema slice with:
            - tables: List of relevant table names
            - columns: Dict mapping table names to column lists
            - joins: List of join conditions
            - partition: Partition key if applicable
        """
        metric_name = intent.get("metric")
        dimensions = intent.get("dimensions", [])
        
        if not metric_name:
            raise ValueError("Intent must contain 'metric' key")
        
        # Get metric definition
        metric_def = self._metrics.get(metric_name)
        if not metric_def:
            raise ValueError(f"Metric '{metric_name}' not found in metrics.yaml")
        
        # Start with metric's base table
        base_table = metric_def.get("table")
        if not base_table:
            raise ValueError(f"Metric '{metric_name}' missing 'table' definition")
        
        # Collect all needed tables
        needed_tables: Set[str] = {base_table}
        
        # Find tables for dimensions
        for dimension in dimensions:
            table = self._find_table_for_column(dimension)
            if table:
                needed_tables.add(table)
        
        # Build join path
        joins = self._build_join_path(base_table, needed_tables)
        
        # Get columns for each table
        columns = {}
        for table in needed_tables:
            if table in self._schema["tables"]:
                columns[table] = list(self._schema["tables"][table]["columns"].keys())
        
        # Get partition key if applicable
        partition = None
        if base_table in self._schema["tables"]:
            for col_name, col_info in self._schema["tables"][base_table]["columns"].items():
                if col_info.get("partition_key"):
                    partition = f"{base_table}.{col_name}"
                    break
        
        result = {
            "tables": list(needed_tables),
            "columns": columns,
            "joins": joins,
            "partition": partition,
            "metric": metric_def
        }
        
        logger.info(f"Selected schema for {metric_name}: {len(needed_tables)} tables")
        return result
    
    def _find_table_for_column(self, column_name: str) -> str:
        """Find which table contains a given column."""
        for table_name, table_info in self._schema["tables"].items():
            if column_name in table_info["columns"]:
                return table_name
        return None
    
    def _build_join_path(self, start_table: str, target_tables: Set[str]) -> List[str]:
        """
        Build join path between tables using relationship graph.
        
        Args:
            start_table: Starting table (metric's base table)
            target_tables: Set of all tables that need to be joined
            
        Returns:
            List of join conditions as strings
        """
        joins = []
        relationships = self._schema.get("relationships", [])
        
        # Simple implementation: find direct relationships
        # TODO: Implement graph traversal for multi-hop joins
        for rel in relationships:
            from_table = rel["from_table"]
            to_table = rel["to_table"]
            
            if from_table in target_tables and to_table in target_tables:
                join_condition = f"{from_table}.{rel['from_column']} = {to_table}.{rel['to_column']}"
                if join_condition not in joins:
                    joins.append(join_condition)
        
        return joins

