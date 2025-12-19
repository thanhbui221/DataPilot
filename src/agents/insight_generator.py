"""Agent 4: Insight Generator - Generates human-readable insights using LangChain."""
import json
from typing import Dict, Any
from langchain.prompts import ChatPromptTemplate
from .base_agent import BaseAgent
import logging

logger = logging.getLogger("datapilot")


class InsightGenerator(BaseAgent):
    """Generates human-readable insights from query results using LangChain."""
    
    def generate_insights(self, reduced_results: Dict[str, Any],
                         original_question: str,
                         metric_description: str) -> str:
        """
        Generate insights from reduced query results using LangChain.
        
        Args:
            reduced_results: Reduced result JSON from Result Reducer
            original_question: User's original question
            metric_description: Description of the metric from metrics.yaml
            
        Returns:
            Human-readable insight text
        """
        logger.info("Generating insights from results")
        
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            reduced_results, original_question, metric_description
        )
        
        try:
            insights = self.generate(system_prompt, user_prompt)
            return insights.strip()
            
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            # Return fallback insights
            return self._generate_fallback_insights(reduced_results, original_question)
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for insight generation."""
        return """You are an expert data analyst. Your task is to generate clear, actionable insights from query results.

Format your response as:
1. **Executive Summary** - 2-3 sentence overview
2. **Key Findings** - Bullet points of important observations
3. **Caveats** - Any limitations or important context
4. **Suggested Next Questions** - 2-3 relevant follow-up questions

Be concise, data-driven, and business-focused. Use emojis sparingly for emphasis."""
    
    def _build_user_prompt(self, reduced_results: Dict[str, Any],
                          original_question: str,
                          metric_description: str) -> str:
        """Build user prompt with results and context."""
        prompt_parts = []
        
        prompt_parts.append(f"Original Question: {original_question}")
        prompt_parts.append(f"Metric: {metric_description}")
        prompt_parts.append("")
        
        prompt_parts.append("Query Results Summary:")
        prompt_parts.append(f"- Total rows: {reduced_results.get('row_count', 0)}")
        
        # Summary statistics
        if reduced_results.get('summary'):
            prompt_parts.append("- Summary Statistics:")
            for key, value in reduced_results['summary'].items():
                prompt_parts.append(f"  {key}: {value}")
        
        # Top breakdown
        if reduced_results.get('top_breakdown'):
            prompt_parts.append("- Top Breakdown:")
            for item in reduced_results['top_breakdown'][:5]:  # Top 5
                prompt_parts.append(f"  {json.dumps(item)}")
        
        # Sample data
        if reduced_results.get('sample'):
            prompt_parts.append("- Sample Data (first few rows):")
            for row in reduced_results['sample'][:3]:  # First 3 rows
                prompt_parts.append(f"  {json.dumps(row)}")
        
        prompt_parts.append("")
        prompt_parts.append("Generate insights based on this data.")
        
        return "\n".join(prompt_parts)
    
    def _generate_fallback_insights(self, reduced_results: Dict[str, Any],
                                    original_question: str) -> str:
        """Generate basic fallback insights if LLM fails."""
        row_count = reduced_results.get('row_count', 0)
        
        insights = f"""## Summary

Based on your question: "{original_question}"

The query returned {row_count} rows of data.

## Key Findings

"""
        
        if reduced_results.get('summary'):
            insights += "Summary statistics:\n"
            for key, value in reduced_results['summary'].items():
                insights += f"- {key}: {value}\n"
        
        if reduced_results.get('top_breakdown'):
            insights += "\nTop items:\n"
            for item in reduced_results['top_breakdown'][:5]:
                insights += f"- {item}\n"
        
        insights += "\n## Suggested Next Questions\n"
        insights += "- Can you break this down further?\n"
        insights += "- What about a different time period?\n"
        insights += "- How does this compare to previous periods?\n"
        
        return insights
