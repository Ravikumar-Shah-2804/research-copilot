"""
Google Gemini embedding client
"""
import asyncio
import hashlib
import logging
from typing import List, Dict, Any, Optional
import httpx

from ...config import settings
from ..cache import RedisCache
from .base import EmbeddingClient

logger = logging.getLogger(__name__)


class GeminiEmbeddingClient(EmbeddingClient):
    """Embedding client using Google Gemini"""

    def __init__(self):
        super().__init__(
            dimension=768,  # Gemini text-embedding-004 has 768 dimensions
            batch_size=settings.embedding_batch_size,
            max_retries=settings.embedding_max_retries,
            retry_delay=settings.embedding_retry_delay
        )
        self.api_key = settings.gemini_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = "text-embedding-004"
        self.cache_ttl = settings.embedding_cache_ttl

        self.client = httpx.AsyncClient(
            headers={
                "Content-Type": "application/json"
            },
            timeout=120.0
        )
        self.cache = RedisCache()

    async def __aenter__(self):
        try:
            await self.cache.connect()
        except Exception as e:
            logger.warning(f"Embedding cache connection failed, continuing without cache: {e}")
            self.cache = None  # Disable cache
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
        if self.cache:
            await self.cache.disconnect()

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"embedding:{self.model}:{text_hash}"

    async def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from cache"""
        if not self.cache:
            return None
        cache_key = self._get_cache_key(text)
        cached = await self.cache.get(cache_key)
        if cached and isinstance(cached, list):
            logger.debug(f"Cache hit for embedding: {cache_key}")
            return cached
        return None

    async def _cache_embedding(self, text: str, embedding: List[float]):
        """Cache embedding"""
        if not self.cache:
            return
        cache_key = self._get_cache_key(text)
        await self.cache.set(cache_key, embedding, ttl=self.cache_ttl)
        logger.debug(f"Cached embedding: {cache_key}")

    async def _call_embedding_api(self, texts: List[str]) -> List[List[float]]:
        """Call Gemini embedding API"""
        payload = {
            "content": {
                "parts": [{"text": text} for text in texts]
            }
        }

        url = f"{self.base_url}/models/{self.model}:embedContent?key={self.api_key}"
        response = await self.client.post(url, json=payload)
        response.raise_for_status()

        result = response.json()
        embedding = result["embedding"]["values"]

        # Gemini returns single embedding for single text, but we expect batch
        # For batch processing, we'd need to make multiple calls or use batch API
        # For now, handle single text case
        if len(texts) == 1:
            # Validate dimension
            if len(embedding) != self.dimension:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {self.dimension}, got {len(embedding)}"
                )
            return [embedding]
        else:
            # For batch, we'd need to implement batch processing
            # For now, raise error as Gemini doesn't support batch embedding directly
            raise NotImplementedError("Batch embedding not yet implemented for Gemini")

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Check cache first
        cached = await self._get_cached_embedding(text)
        if cached:
            return cached

        # Generate embedding
        embeddings = await self._call_with_retry(self._call_embedding_api, [text])
        embedding = embeddings[0]

        # Cache result
        await self._cache_embedding(text, embedding)

        return embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts"""
        if not texts:
            return []

        # Filter out empty texts
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)

        if not valid_texts:
            raise ValueError("All texts are empty")

        # For Gemini, we need to process one by one since batch API isn't directly available
        # Check cache first
        cached_embeddings = []
        uncached_texts = []
        uncached_indices = []

        for i, text in zip(valid_indices, valid_texts):
            cached = await self._get_cached_embedding(text)
            if cached:
                cached_embeddings.append((i, cached))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Generate embeddings for uncached texts
        all_embeddings = [None] * len(texts)

        # Set cached embeddings
        for idx, embedding in cached_embeddings:
            all_embeddings[idx] = embedding

        # Process uncached texts one by one (Gemini doesn't have batch embedding)
        for text, idx in zip(uncached_texts, uncached_indices):
            max_connection_retries = 3
            for attempt in range(max_connection_retries):
                try:
                    embedding = await self.embed_text(text)
                    all_embeddings[idx] = embedding
                    break
                except ConnectionResetError as e:
                    if attempt == max_connection_retries - 1:
                        logger.error(f"Failed to embed text at index {idx} after {max_connection_retries} retries: {e}")
                        all_embeddings[idx] = None
                    else:
                        delay = self.retry_delay * (2 ** attempt)
                        logger.warning(f"ConnectionResetError for text at index {idx}, attempt {attempt + 1}, retrying in {delay}s: {e}")
                        await asyncio.sleep(delay)
                except Exception as e:
                    logger.error(f"Failed to embed text at index {idx}: {e}")
                    all_embeddings[idx] = None
                    break

        # Check for any None values (failed embeddings)
        failed_indices = [i for i, emb in enumerate(all_embeddings) if emb is None]
        if failed_indices:
            raise RuntimeError(f"Failed to generate embeddings for texts at indices: {failed_indices}")

        return all_embeddings

    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        try:
            # Simple health check - try a minimal embedding request
            test_text = "test"
            await self.embed_text(test_text)
            return {
                "healthy": True,
                "provider": "gemini",
                "model": self.model,
                "dimension": self.dimension
            }
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return {
                "healthy": False,
                "provider": "gemini",
                "error": str(e)
            }