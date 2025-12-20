"""Base agent class with LangChain and Ollama integration."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage

logger = logging.getLogger("datapilot")


class BaseAgent(ABC):
    """Base class for all LLM agents using LangChain and Ollama."""
    
    def __init__(self, model_name: str, temperature: float = 0.7, 
                 max_tokens: int = 2048, timeout: int = 60, base_url: Optional[str] = None):
        """
        Initialize base agent with Ollama.
        
        Args:
            model_name: Ollama model name (e.g., "mistral", "llama3", "codellama")
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            base_url: Optional Ollama API base URL (defaults to http://localhost:11434)
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.base_url = base_url
        self._llm = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize Ollama LLM."""
        try:
            # Build ChatOllama args - only include base_url if provided
            llm_kwargs = {
                "model": self.model_name,
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
                "timeout": self.timeout
            }
            if self.base_url:
                llm_kwargs["base_url"] = self.base_url
            
            self._llm = ChatOllama(**llm_kwargs)
            logger.info(f"Initialized Ollama LLM: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama LLM: {str(e)}")
            raise
    
    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        Generate a response from the LLM using LangChain.
        
        Args:
            system_prompt: System instructions (can be pre-formatted, no template variables)
            user_prompt: User input
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text
        """
        try:
            # If system_prompt contains {variables}, we need to handle it differently
            # Check if it's already formatted (no template variables)
            # Use from_messages with Message objects directly to avoid template parsing issues
            from langchain_core.messages import SystemMessage, HumanMessage
            
            # Create messages directly (no template parsing)
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # Invoke LLM
            response = self._llm.invoke(messages)
            
            # Handle different response types
            if isinstance(response, BaseMessage):
                return response.content
            elif isinstance(response, str):
                return response
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise
    
    def generate_with_prompt_template(self, prompt_template: ChatPromptTemplate, 
                                     **kwargs) -> str:
        """
        Generate response using a LangChain prompt template.
        
        Args:
            prompt_template: LangChain ChatPromptTemplate
            **kwargs: Variables to format the template
            
        Returns:
            Generated text
        """
        try:
            formatted_messages = prompt_template.format_messages(**kwargs)
            response = self._llm.invoke(formatted_messages)
            
            if isinstance(response, BaseMessage):
                return response.content
            elif isinstance(response, str):
                return response
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"Error generating response with template: {str(e)}")
            raise
    
    def generate_with_messages(self, messages: list, **kwargs) -> str:
        """
        Generate response using a list of messages directly.
        
        Args:
            messages: List of message objects (SystemMessage, HumanMessage, etc.)
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text
        """
        try:
            response = self._llm.invoke(messages)
            
            if isinstance(response, BaseMessage):
                return response.content
            elif isinstance(response, str):
                return response
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"Error generating response with messages: {str(e)}")
            raise
    
    def stream(self, system_prompt: str, user_prompt: str):
        """
        Stream response from the LLM.
        
        Args:
            system_prompt: System instructions
            user_prompt: User input
            
        Yields:
            Response chunks
        """
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            for chunk in self._llm.stream(messages):
                if isinstance(chunk, BaseMessage):
                    yield chunk.content
                else:
                    yield str(chunk)
                    
        except Exception as e:
            logger.error(f"Error streaming response: {str(e)}")
            raise
