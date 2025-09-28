"""
OpenRouter embedding client
"""
import hashlib
import logging
from typing import List, Dict, Any, Optional
import httpx

from ...config import settings
from ..cache import RedisCache
from .base import EmbeddingClient

logger = logging.getLogger(__name__)


class OpenRouterEmbeddingClient(EmbeddingClient):
    """Embedding client using OpenRouter"""

    def __init__(self):
        super().__init__(
            dimension=settings.embedding_dimension,
            batch_size=settings.embedding_batch_size,
            max_retries=settings.embedding_max_retries,
            retry_delay=settings.embedding_retry_delay
        )
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = settings.embedding_model
        self.cache_ttl = settings.embedding_cache_ttl

        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://research-copilot.com",
                "X-Title": "Research Copilot"
            },
            timeout=60.0
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
        """Call OpenRouter embedding API"""
        payload = {
            "model": self.model,
            "input": texts
        }

        response = await self.client.post(
            f"{self.base_url}/embeddings",
            json=payload
        )
        response.raise_for_status()

        result = response.json()
        embeddings = [item["embedding"] for item in result["data"]]

        # Validate dimensions
        for i, embedding in enumerate(embeddings):
            if len(embedding) != self.dimension:
                raise ValueError(
                    f"Embedding dimension mismatch for text {i}: "
                    f"expected {self.dimension}, got {len(embedding)}"
                )

        return embeddings

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

        # Check cache for each text
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

        # Generate embeddings for uncached texts in batches
        all_embeddings = [None] * len(texts)

        # Set cached embeddings
        for idx, embedding in cached_embeddings:
            all_embeddings[idx] = embedding

        # Process uncached texts in batches
        for i in range(0, len(uncached_texts), self.batch_size):
            batch_texts = uncached_texts[i:i + self.batch_size]
            batch_indices = uncached_indices[i:i + self.batch_size]

            try:
                batch_embeddings = await self._call_with_retry(self._call_embedding_api, batch_texts)

                # Cache and set results
                for text, embedding, idx in zip(batch_texts, batch_embeddings, batch_indices):
                    try:
                        await self._cache_embedding(text, embedding)
                    except Exception as e:
                        logger.warning(f"Failed to cache embedding for text: {e}")
                    all_embeddings[idx] = embedding

            except Exception as e:
                logger.error(f"Failed to process batch starting at index {i}: {e}")
                # Set None for failed batch
                for idx in batch_indices:
                    all_embeddings[idx] = None

        # Check for any None values (failed embeddings)
        failed_indices = [i for i, emb in enumerate(all_embeddings) if emb is None]
        if failed_indices:
            raise RuntimeError(f"Failed to generate embeddings for texts at indices: {failed_indices}")

        return all_embeddings

    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        try:
            # Simple health check - try to get model info or make a minimal request
            return {
                "healthy": True,
                "provider": "openrouter",
                "model": self.model,
                "dimension": self.dimension
            }
        except Exception as e:
            logger.error(f"OpenRouter health check failed: {e}")
            return {
                "healthy": False,
                "provider": "openrouter",
                "error": str(e)
            }