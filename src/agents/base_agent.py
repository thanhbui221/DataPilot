"""Base agent class with shared LLM interface."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger("datapilot")


class BaseAgent(ABC):
    """Base class for all LLM agents."""
    
    def __init__(self, model_path: str, model_type: str, temperature: float = 0.7, 
                 max_tokens: int = 2048, timeout: int = 60):
        """
        Initialize base agent.
        
        Args:
            model_path: Path to model file
            model_type: Type of model (mistral, llama, codellama)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
        """
        self.model_path = model_path
        self.model_type = model_type
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._model = None
    
    def load_model(self):
        """Load the LLM model. To be implemented by subclasses."""
        # TODO: Implement model loading based on model_type
        # This will depend on the chosen LLM library (llama.cpp, transformers, etc.)
        logger.warning("Model loading not yet implemented")
        pass
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text
        """
        pass
    
    def _format_prompt(self, system_prompt: str, user_prompt: str) -> str:
        """
        Format prompt based on model type.
        
        Args:
            system_prompt: System instructions
            user_prompt: User input
            
        Returns:
            Formatted prompt string
        """
        if self.model_type == "mistral":
            # Mistral format
            return f"<s>[INST] {system_prompt}\n\n{user_prompt} [/INST]"
        elif self.model_type in ["llama", "codellama"]:
            # LLaMA format
            return f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{user_prompt} [/INST]"
        else:
            # Default format
            return f"{system_prompt}\n\n{user_prompt}"

