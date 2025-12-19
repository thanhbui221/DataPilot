"""Agent 1: Intent Clarifier - Extracts and clarifies user intent using LangChain."""
import json
from typing import Dict, Any, Optional
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from .base_agent import BaseAgent
from ..prompts import (
    INTENT_CLARIFIER_SYSTEM_PROMPT, 
    INTENT_CLARIFIER_CLARIFICATION_SYSTEM_PROMPT,
    INTENT_CLARIFIER_CLARIFICATION_USER_PROMPT
)
import logging

logger = logging.getLogger("datapilot")


class IntentOutput(BaseModel):
    """Structured output for intent clarification."""
    metric: str = Field(description="Metric name from metrics.yaml (e.g., 'total_revenue')")
    dimensions: list[str] = Field(default=[], description="List of dimensions to group by (e.g., ['country', 'month'])")
    time_range: Optional[str] = Field(default=None, description="Time range filter (e.g., 'last_month', 'last_quarter', '2024-01-01 to 2024-03-31')")
    comparison: Optional[str] = Field(default=None, description="Comparison period (e.g., 'previous_month', 'previous_quarter')")
    needs_confirmation: bool = Field(default=False, description="Whether clarification is needed from user")
    confidence: float = Field(default=0.5, description="Confidence score between 0 and 1")


class IntentClarifier(BaseAgent):
    """Clarifies user intent and extracts structured information using LangChain."""
    
    def __init__(self, *args, **kwargs):
        # Extract IntentClarifier-specific parameters before calling super()
        max_clarification_rounds = kwargs.pop("max_clarification_rounds", 2)
        confidence_threshold = kwargs.pop("confidence_threshold", 0.7)
        
        # Now call super with remaining kwargs
        super().__init__(*args, **kwargs)
        
        # Set IntentClarifier-specific attributes
        self.max_clarification_rounds = max_clarification_rounds
        self.confidence_threshold = confidence_threshold
        self.output_parser = PydanticOutputParser(pydantic_object=IntentOutput)
        
        # Load metrics for context
        self._load_metrics()
    
    def _load_metrics(self):
        """Load available metrics for context."""
        try:
            import yaml
            from pathlib import Path
            metrics_path = Path("./metadata/metrics.yaml")
            if metrics_path.exists():
                with open(metrics_path, 'r') as f:
                    self.available_metrics = list(yaml.safe_load(f).keys())
            else:
                self.available_metrics = []
            logger.info(f"Loaded {len(self.available_metrics)} available metrics")
        except Exception as e:
            logger.warning(f"Could not load metrics: {str(e)}")
            self.available_metrics = []
    
    def clarify_intent(self, user_message: str, 
                      conversation_context: Optional[list] = None) -> Dict[str, Any]:
        """
        Extract and clarify user intent using LangChain.
        
        Args:
            user_message: User's natural language question
            conversation_context: Previous conversation messages (optional)
            
        Returns:
            Structured intent dictionary
        """
        logger.info(f"Clarifying intent for: {user_message}")
        
        # Build system prompt
        system_prompt = self._build_system_prompt()
        
        # Build user prompt with context
        user_prompt = self._build_user_prompt(user_message, conversation_context)
        
        try:
            # Generate response
            response = self.generate(system_prompt, user_prompt)
            
            # Parse structured output
            intent = self._parse_response(response)
            
            logger.info(f"Extracted intent: {intent.get('metric')} with confidence {intent.get('confidence')}")
            return intent
            
        except Exception as e:
            logger.error(f"Error clarifying intent: {str(e)}")
            # Return default intent on error
            return {
                "metric": "total_revenue",
                "dimensions": [],
                "time_range": None,
                "comparison": None,
                "needs_confirmation": True,
                "confidence": 0.3
            }
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for intent clarification."""
        metrics_list = ", ".join(self.available_metrics) if self.available_metrics else "total_revenue, order_count, etc."
        return INTENT_CLARIFIER_SYSTEM_PROMPT.format(available_metrics=metrics_list)
    
    def _build_user_prompt(self, user_message: str, 
                          conversation_context: Optional[list] = None) -> str:
        """Build user prompt with conversation context."""
        prompt = f"User question: {user_message}"
        
        if conversation_context:
            context_str = "\n".join([
                f"- {msg.get('type', 'unknown')}: {msg.get('content', '')}"
                for msg in conversation_context[-3:]  # Last 3 messages
            ])
            prompt += f"\n\nPrevious conversation:\n{context_str}"
        
        return prompt
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to structured intent."""
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            # Parse JSON
            intent_dict = json.loads(response)
            
            # Validate and convert to IntentOutput format
            intent = IntentOutput(**intent_dict)
            return intent.dict()
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {str(e)}")
            # Try to use Pydantic parser as fallback
            try:
                intent = self.output_parser.parse(response)
                return intent.dict()
            except Exception:
                logger.error("Failed to parse response with Pydantic parser")
                raise
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            raise
    
    def ask_clarification(self, ambiguous_intent: Dict[str, Any]) -> str:
        """
        Generate a clarification question using LangChain.
        
        Args:
            ambiguous_intent: Partially extracted intent
            
        Returns:
            Clarification question string
        """
        system_prompt = INTENT_CLARIFIER_CLARIFICATION_SYSTEM_PROMPT
        
        user_prompt = INTENT_CLARIFIER_CLARIFICATION_USER_PROMPT.format(
            metric=ambiguous_intent.get('metric', 'unknown'),
            dimensions=', '.join(ambiguous_intent.get('dimensions', [])) or 'None',
            time_range=ambiguous_intent.get('time_range', 'not specified')
        )
        
        try:
            clarification = self.generate(system_prompt, user_prompt)
            return clarification.strip()
        except Exception as e:
            logger.error(f"Error generating clarification: {str(e)}")
            return "Could you please clarify what you'd like to see?"
