"""
Abstract base class for embedding clients
"""
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class EmbeddingClient(ABC):
    """Abstract base class for embedding clients"""

    def __init__(self, dimension: int, batch_size: int = 100, max_retries: int = 3, retry_delay: float = 1.0):
        self.dimension = dimension
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    @abstractmethod
    async def __aenter__(self):
        """Async context manager entry"""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts"""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        pass

    async def _call_with_retry(self, func, *args, **kwargs):
        """Generic retry wrapper"""
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(self.retry_delay * (2 ** attempt))