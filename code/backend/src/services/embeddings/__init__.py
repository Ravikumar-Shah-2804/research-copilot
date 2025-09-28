"""
Embeddings service package
"""
from .client import EmbeddingService
from .base import EmbeddingClient
from .openrouter_client import OpenRouterEmbeddingClient
from .gemini_client import GeminiEmbeddingClient

__all__ = [
    "EmbeddingService",
    "EmbeddingClient",
    "OpenRouterEmbeddingClient",
    "GeminiEmbeddingClient"
]