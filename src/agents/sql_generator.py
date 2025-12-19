"""Agent 2: SQL Generator - Generates SQL from intent and schema using LangChain."""
import json
from typing import Dict, Any, Optional
from langchain.prompts import ChatPromptTemplate
from .base_agent import BaseAgent
from ..prompts import SQL_GENERATOR_SYSTEM_PROMPT, SQL_GENERATOR_USER_PROMPT_TEMPLATE
import logging

logger = logging.getLogger("datapilot")


class SQLGenerator(BaseAgent):
    """Generates SQL queries from structured intent and schema using LangChain."""
    
    def generate_sql(self, intent: Dict[str, Any], 
                    schema_slice: Dict[str, Any],
                    metric_definition: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate SQL query from intent and schema using LangChain.
        
        Args:
            intent: Structured intent from Intent Clarifier
            schema_slice: Relevant schema from Schema Selector
            metric_definition: Metric definition from metrics.yaml
            
        Returns:
            Dictionary with 'sql' key containing the generated SQL
        """
        logger.info(f"Generating SQL for metric: {intent.get('metric')}")
        
        # Build prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(intent, schema_slice, metric_definition)
        
        try:
            # Generate SQL
            sql_response = self.generate(system_prompt, user_prompt)
            
            # Extract SQL from response
            sql = self._extract_sql(sql_response)
            
            logger.info(f"Generated SQL: {sql[:100]}...")
            return {"sql": sql}
            
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            raise
    
    def regenerate_sql(self, intent: Dict[str, Any],
                      schema_slice: Dict[str, Any],
                      metric_definition: Dict[str, Any],
                      validation_feedback: str) -> Dict[str, str]:
        """
        Regenerate SQL based on validation feedback using LangChain.
        
        Args:
            intent: Structured intent
            schema_slice: Relevant schema
            metric_definition: Metric definition
            validation_feedback: Error message from SQL validator
            
        Returns:
            Dictionary with 'sql' key containing the regenerated SQL
        """
        logger.info(f"Regenerating SQL with feedback: {validation_feedback}")
        
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            intent, schema_slice, metric_definition,
            validation_feedback=validation_feedback
        )
        
        try:
            sql_response = self.generate(system_prompt, user_prompt)
            sql = self._extract_sql(sql_response)
            
            logger.info(f"Regenerated SQL: {sql[:100]}...")
            return {"sql": sql}
            
        except Exception as e:
            logger.error(f"Error regenerating SQL: {str(e)}")
            raise
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for SQL generation."""
        return SQL_GENERATOR_SYSTEM_PROMPT
    
    def _build_user_prompt(self, intent: Dict[str, Any],
                          schema_slice: Dict[str, Any],
                          metric_definition: Dict[str, Any],
                          validation_feedback: Optional[str] = None) -> str:
        """Build user prompt with intent, schema, and optional feedback."""
        prompt_parts = []
        
        # Add validation feedback if regenerating
        if validation_feedback:
            prompt_parts.append(f"Previous SQL was rejected. Error: {validation_feedback}\n")
            prompt_parts.append("Please regenerate the SQL query fixing the issue.\n")
        
        # Intent
        prompt_parts.append("User Intent:")
        prompt_parts.append(f"- Metric: {intent.get('metric')}")
        prompt_parts.append(f"- Dimensions: {', '.join(intent.get('dimensions', [])) or 'None'}")
        if intent.get('time_range'):
            prompt_parts.append(f"- Time range: {intent.get('time_range')}")
        if intent.get('comparison'):
            prompt_parts.append(f"- Comparison: {intent.get('comparison')}")
        prompt_parts.append("")
        
        # Metric definition
        prompt_parts.append("Metric Definition:")
        prompt_parts.append(f"- Description: {metric_definition.get('description', 'N/A')}")
        prompt_parts.append(f"- Base table: {metric_definition.get('table', 'N/A')}")
        prompt_parts.append(f"- SQL calculation: {metric_definition.get('sql', 'N/A')}")
        if metric_definition.get('filters'):
            prompt_parts.append(f"- Required filters: {json.dumps(metric_definition.get('filters'))}")
        prompt_parts.append("")
        
        # Schema
        prompt_parts.append("Available Schema:")
        prompt_parts.append(f"Tables: {', '.join(schema_slice.get('tables', []))}")
        prompt_parts.append("Columns:")
        for table, columns in schema_slice.get('columns', {}).items():
            prompt_parts.append(f"  {table}: {', '.join(columns)}")
        if schema_slice.get('joins'):
            prompt_parts.append("Join relationships:")
            for join in schema_slice.get('joins', []):
                prompt_parts.append(f"  {join}")
        if schema_slice.get('partition'):
            prompt_parts.append(f"Partition key: {schema_slice.get('partition')}")
        prompt_parts.append("")
        
        prompt_parts.append("Generate a SQL query that:")
        prompt_parts.append("1. Uses the metric calculation from the metric definition")
        prompt_parts.append("2. Groups by the specified dimensions")
        prompt_parts.append("3. Applies required filters from the metric definition")
        if intent.get('time_range') and schema_slice.get('partition'):
            prompt_parts.append("4. Includes time filter using the user's specified time_range and partition key")
        else:
            prompt_parts.append("4. Do NOT add time filters if user did not specify a time_range")
        prompt_parts.append("5. Uses proper JOINs to connect tables")
        
        return "\n".join(prompt_parts)
    
    def _extract_sql(self, response: str) -> str:
        """Extract SQL from LLM response."""
        response = response.strip()
        
        # Remove markdown code blocks if present
        if "```sql" in response:
            start = response.find("```sql") + 6
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        # If no code blocks, return as-is (assuming it's already SQL)
        return response
