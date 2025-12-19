"""Base agent class with LangChain and Ollama integration."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from langchain_community.llms import Ollama
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.schema import BaseMessage

logger = logging.getLogger("datapilot")


class BaseAgent(ABC):
    """Base class for all LLM agents using LangChain and Ollama."""
    
    def __init__(self, model_name: str, base_url: str = "http://localhost:11434",
                 temperature: float = 0.7, max_tokens: int = 2048, timeout: int = 60):
        """
        Initialize base agent with Ollama.
        
        Args:
            model_name: Ollama model name (e.g., "mistral", "llama3", "codellama")
            base_url: Ollama API base URL
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
        """
        self.model_name = model_name
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._llm = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize Ollama LLM."""
        try:
            self._llm = Ollama(
                model=self.model_name,
                base_url=self.base_url,
                temperature=self.temperature,
                num_predict=self.max_tokens,
                timeout=self.timeout
            )
            logger.info(f"Initialized Ollama LLM: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama LLM: {str(e)}")
            raise
    
    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        Generate a response from the LLM using LangChain.
        
        Args:
            system_prompt: System instructions
            user_prompt: User input
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text
        """
        try:
            # Create prompt template
            prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_prompt),
                HumanMessagePromptTemplate.from_template("{user_input}")
            ])
            
            # Format and invoke
            formatted_prompt = prompt.format_messages(user_input=user_prompt)
            response = self._llm.invoke(formatted_prompt)
            
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
            prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_prompt),
                HumanMessagePromptTemplate.from_template("{user_input}")
            ])
            
            formatted_messages = prompt.format_messages(user_input=user_prompt)
            
            for chunk in self._llm.stream(formatted_messages):
                if isinstance(chunk, BaseMessage):
                    yield chunk.content
                else:
                    yield str(chunk)
                    
        except Exception as e:
            logger.error(f"Error streaming response: {str(e)}")
            raise
