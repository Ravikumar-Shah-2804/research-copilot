"""
Embedding service manager - factory for different embedding providers
"""
import logging
from typing import List, Dict, Any, Optional

from ...config import settings
from .base import EmbeddingClient
from .openrouter_client import OpenRouterEmbeddingClient
from .gemini_client import GeminiEmbeddingClient

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embedding service manager that delegates to specific providers"""

    def __init__(self, provider: str = None):
        self.provider = provider or settings.embedding_provider
        self._client: Optional[EmbeddingClient] = None

    async def initialize(self):
        if self._client is None:
            client = self._get_client()
            self._client = await client.__aenter__()

    async def cleanup(self):
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None

    def _get_client(self) -> EmbeddingClient:
        """Get the appropriate embedding client based on provider"""
        if self.provider == "openrouter":
            return OpenRouterEmbeddingClient()
        elif self.provider == "gemini":
            return GeminiEmbeddingClient()
        else:
            raise ValueError(f"Unknown embedding provider: {self.provider}")

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        return await self._client.embed_text(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts"""
        return await self._client.embed_batch(texts)

    async def embed_paper(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate embeddings for a research paper"""
        try:
            # Extract text content for embedding
            title = paper_data.get("title", "")
            abstract = paper_data.get("abstract", "")
            content = paper_data.get("content", "")

            # Create combined text for document-level embedding
            combined_text = f"{title}\n\n{abstract}"
            if content:
                combined_text += f"\n\n{content}"

            # Generate document embedding
            doc_embedding = await self.embed_text(combined_text)

            # Update paper data with embedding
            paper_data["embedding"] = doc_embedding

            # Process chunks if available
            if "chunks" in paper_data and paper_data["chunks"]:
                chunk_texts = [chunk["content"] for chunk in paper_data["chunks"]]
                chunk_embeddings = await self.embed_batch(chunk_texts)

                # Add embeddings to chunks
                for chunk, embedding in zip(paper_data["chunks"], chunk_embeddings):
                    chunk["embedding"] = embedding

            return paper_data

        except Exception as e:
            logger.error(f"Failed to embed paper {paper_data.get('paper_id', 'unknown')}: {e}")
            raise

    async def embed_papers_batch(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate embeddings for multiple papers"""
        import asyncio
        try:
            # Process papers concurrently with semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent embeddings

            async def embed_single_paper(paper: Dict[str, Any]) -> Dict[str, Any]:
                async with semaphore:
                    return await self.embed_paper(paper)

            # Process all papers concurrently
            tasks = [embed_single_paper(paper) for paper in papers]
            embedded_papers = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions
            results = []
            for i, result in enumerate(embedded_papers):
                if isinstance(result, Exception):
                    logger.error(f"Failed to embed paper {i}: {result}")
                    # Return original paper without embedding
                    results.append(papers[i])
                else:
                    results.append(result)

            return results

        except Exception as e:
            logger.error(f"Failed to embed papers batch: {e}")
            raise

    async def get_embedding_stats(self) -> Dict[str, Any]:
        """Get embedding service statistics"""
        try:
            # This would integrate with monitoring system
            return {
                "provider": self.provider,
                "model": getattr(self._client, 'model', 'unknown'),
                "dimension": getattr(self._client, 'dimension', 'unknown'),
                "batch_size": getattr(self._client, 'batch_size', 'unknown'),
            }
        except Exception as e:
            logger.error(f"Failed to get embedding stats: {e}")
            return {}

    async def clear_cache(self):
        """Clear embedding cache"""
        try:
            # This would need a more sophisticated cache clearing
            # For now, we'll just log
            logger.info("Embedding cache clearing requested")
        except Exception as e:
            logger.error(f"Failed to clear embedding cache: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        return await self._client.health_check()