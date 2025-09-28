"""
Base LLM Service interface
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """Configuration for LLM service"""
    model: str
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 60


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    text: str
    usage: Dict[str, Any]
    model: str
    finish_reason: Optional[str] = None
    cost: Optional[float] = None


@dataclass
class RAGRequest:
    """RAG-specific request"""
    query: str
    context_docs: List[Dict[str, Any]]
    max_tokens: int = 1000
    temperature: float = 0.7


@dataclass
class RAGResponse:
    """RAG-specific response"""
    answer: str
    sources: List[Dict[str, Any]]
    usage: Dict[str, Any]
    model: str
    confidence: float = 0.0
    cost: Optional[float] = None


class BaseLLMService(ABC):
    """Abstract base class for LLM services"""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    async def __aenter__(self):
        """Async context manager entry"""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass

    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Generate text completion"""
        pass

    @abstractmethod
    async def generate_rag_response(
        self,
        request: RAGRequest
    ) -> RAGResponse:
        """Generate RAG response with context"""
        pass

    @abstractmethod
    async def generate_streaming_response(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response"""
        pass

    @abstractmethod
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get available models"""
        pass

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Check service health"""
        pass

    @abstractmethod
    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        pass

    @abstractmethod
    async def estimate_cost(self, tokens: int, model: str) -> float:
        """Estimate cost for token usage"""
        pass