"""
RAG Pipeline service for intelligent research paper Q&A
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

from ..config import settings
from .opensearch import OpenSearchService
from .embeddings import EmbeddingService
from .llm import LLMFactory
from .cache import RedisCache
from .monitoring import performance_monitor

logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    """Context for RAG generation"""
    query: str
    documents: List[Dict[str, Any]]
    search_time: float
    total_results: int
    search_mode: str


@dataclass
class RAGResult:
    """Result of RAG generation"""
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    tokens_used: int
    generation_time: float
    model: str
    context_length: int
    degraded: bool = False


class RAGPipeline:
    """RAG Pipeline for research paper question answering"""

    def __init__(self, llm_service_type: str = "openrouter", llm_model: str = None):
        self.embedding_service = EmbeddingService()
        self.opensearch = OpenSearchService(provider=self.embedding_service.provider)
        self.llm_service_type = llm_service_type
        self.llm_model = llm_model or settings.deepseek_model
        self.llm_client = None  # Will be created in __aenter__
        self.cache = RedisCache()
        self.context_window_size = 8192  # tokens
        self.max_context_docs = 5

    async def __aenter__(self):
        logger.info("Initializing RAG Pipeline components")
        try:
            await self.opensearch.connect()
            logger.info("OpenSearch connected successfully")
        except Exception as e:
            logger.warning(f"OpenSearch connection failed, continuing without search: {e}")
            self.opensearch = None  # Disable OpenSearch

        try:
            await self.embedding_service.__aenter__()
            logger.info("Embedding service initialized")
        except Exception as e:
            logger.error(f"Embedding service initialization failed: {e}")
            raise

        try:
            self.llm_client = LLMFactory.create_service(
                service_type=self.llm_service_type,
                model=self.llm_model
            )
            await self.llm_client.__aenter__()
            logger.info("LLM client initialized")
        except Exception as e:
            logger.error(f"LLM client initialization failed: {e}")
            raise

        try:
            await self.cache.connect()
            logger.info("Cache connected")
        except Exception as e:
            logger.warning(f"Cache connection failed: {e}")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # OpenSearch client doesn't have disconnect method
        await self.embedding_service.__aexit__(exc_type, exc_val, exc_tb)
        if self.llm_client:
            await self.llm_client.__aexit__(exc_type, exc_val, exc_tb)
        if self.cache:
            await self.cache.disconnect()

    async def generate_answer(
        self,
        query: str,
        search_mode: str = "hybrid",
        context_limit: int = 5,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        use_cache: bool = True
    ) -> RAGResult:
        """Generate answer using RAG pipeline"""
        start_time = asyncio.get_event_loop().time()
        logger.info(f"Starting RAG generation for query: {query[:50]}..., search_mode: {search_mode}, context_limit: {context_limit}")

        # Check cache first
        if use_cache and self.cache:
            cached_result = await self._check_cache(query, search_mode, context_limit)
            if cached_result:
                logger.info("Returning cached RAG result")
                return cached_result

        # Retrieve context
        context = await self._retrieve_context(query, search_mode, context_limit)
        logger.info(f"Retrieved {len(context.documents)} context documents, search_time: {context.search_time:.3f}s")

        # Generate answer using LLM service
        from .llm.base import RAGRequest
        rag_request = RAGRequest(
            query=query,
            context_docs=context.documents,
            max_tokens=max_tokens,
            temperature=temperature
        )
        logger.info(f"Calling LLM with {len(context.documents)} context docs")

        try:
            answer_result = await self.llm_client.generate_rag_response(rag_request)
            logger.info(f"LLM response received, tokens: {answer_result.usage.get('total_tokens', 0)}")

            # Calculate confidence
            confidence = self._calculate_confidence(context, answer_result)

            # Create result
            result = RAGResult(
                answer=answer_result.answer,
                sources=answer_result.sources,
                confidence=confidence,
                tokens_used=answer_result.usage.get("total_tokens", 0),
                generation_time=asyncio.get_event_loop().time() - start_time,
                model=answer_result.model,
                context_length=len(str(context.documents)),  # Approximate
                degraded=False
            )

        except Exception as e:
            logger.error(f"OpenRouter service failure: {e}")
            # Create degraded result
            degraded_message = "AI analysis is currently unavailable due to service issues. Retrieved context documents are provided below."
            result = RAGResult(
                answer=degraded_message,
                sources=context.documents,
                confidence=0.0,
                tokens_used=0,
                generation_time=asyncio.get_event_loop().time() - start_time,
                model=self.llm_model or "degraded",
                context_length=len(str(context.documents)),
                degraded=True
            )

        # Cache result if not degraded
        if use_cache and self.cache and not result.degraded:
            await self._cache_result(query, search_mode, context_limit, result)

        # Record metrics if not degraded
        if not result.degraded:
            await self._record_metrics(query, result, context)

        logger.info(f"RAG generation completed, degraded: {result.degraded}, sources: {len(result.sources)}")
        return result

    async def _retrieve_context(
        self,
        query: str,
        search_mode: str,
        context_limit: int
    ) -> RAGContext:
        """Retrieve relevant context documents"""
        start_time = asyncio.get_event_loop().time()
        logger.info(f"Retrieving context for query: {query[:50]}..., mode: {search_mode}, limit: {context_limit}")

        # If OpenSearch is not available, return empty context
        if self.opensearch is None:
            logger.warning("OpenSearch not available, returning empty context")
            return RAGContext(
                query=query,
                documents=[],
                search_time=asyncio.get_event_loop().time() - start_time,
                total_results=0,
                search_mode=search_mode
            )

        try:
            # Generate embedding for query
            logger.info("Generating query embedding")
            query_embedding = await self.embedding_service.embed_text(query)
            logger.info(f"Embedding generated, length: {len(query_embedding) if query_embedding else 0}")

            # Perform search based on mode
            logger.info(f"Performing {search_mode} search")
            if search_mode == "bm25_only":
                search_result = self.opensearch.bm25_search(
                    query=query,
                    size=context_limit,
                    highlight=False
                )
            elif search_mode == "vector_only":
                search_result = self.opensearch.vector_search(
                    vector=query_embedding,
                    size=context_limit
                )
            else:  # hybrid
                search_result = self.opensearch.hybrid_search(
                    text_query=query,
                    vector_query=query_embedding,
                    mode="hybrid",
                    size=context_limit,
                    highlight=False
                )

            # Extract documents
            documents = []
            for hit in search_result["hits"]["hits"]:
                source = hit["_source"]
                doc = {
                    "id": hit["_id"],
                    "title": source.get("title", ""),
                    "abstract": source.get("abstract", ""),
                    "content": source.get("content", ""),
                    "authors": source.get("authors", []),
                    "score": hit["_score"],
                    "url": source.get("url", "")
                }
                documents.append(doc)

            search_time = asyncio.get_event_loop().time() - start_time
            total_results = search_result["hits"]["total"]["value"]
            logger.info(f"Search completed, found {len(documents)} documents out of {total_results} total results")

            return RAGContext(
                query=query,
                documents=documents,
                search_time=search_time,
                total_results=total_results,
                search_mode=search_mode
            )

        except Exception as e:
            logger.error(f"Context retrieval error: {e}")
            # Return empty context for graceful degradation
            return RAGContext(
                query=query,
                documents=[],
                search_time=asyncio.get_event_loop().time() - start_time,
                total_results=0,
                search_mode=search_mode
            )

    def _calculate_confidence(self, context: RAGContext, answer_result: Dict[str, Any]) -> float:
        """Calculate confidence score for the answer"""
        try:
            # Base confidence on search quality and answer characteristics
            search_score = min(1.0, context.total_results / 100)  # Normalize search results

            # Average document relevance score
            if context.documents:
                avg_doc_score = sum(doc["score"] for doc in context.documents) / len(context.documents)
                doc_score = min(1.0, avg_doc_score / 10)  # Normalize relevance score
            else:
                doc_score = 0.0

            # Answer length as quality indicator (longer answers tend to be more comprehensive)
            answer_length = len(answer_result["answer"])
            length_score = min(1.0, answer_length / 1000)  # Normalize to 1000 chars

            # Combine scores with weights
            confidence = (
                search_score * 0.3 +
                doc_score * 0.4 +
                length_score * 0.3
            )

            return round(confidence, 3)

        except Exception as e:
            logger.error(f"Confidence calculation error: {e}")
            return 0.5  # Default confidence

    async def _check_cache(
        self,
        query: str,
        search_mode: str,
        context_limit: int
    ) -> Optional[RAGResult]:
        """Check cache for existing result"""
        if not self.cache:
            return None

        try:
            cache_key = f"rag_pipeline:{hash(f'{query}:{search_mode}:{context_limit}')}"
            cached_data = await self.cache.get(cache_key)

            if cached_data:
                # Convert cached data back to RAGResult
                return RAGResult(**cached_data)

            return None

        except Exception as e:
            logger.error(f"Cache check error: {e}")
            return None

    async def _cache_result(
        self,
        query: str,
        search_mode: str,
        context_limit: int,
        result: RAGResult
    ):
        """Cache RAG result"""
        if not self.cache:
            return

        try:
            cache_key = f"rag_pipeline:{hash(f'{query}:{search_mode}:{context_limit}')}"
            cache_data = {
                "answer": result.answer,
                "sources": result.sources,
                "confidence": result.confidence,
                "tokens_used": result.tokens_used,
                "generation_time": result.generation_time,
                "model": result.model,
                "context_length": result.context_length,
                "cached_at": datetime.now().isoformat()
            }

            await self.cache.set(cache_key, cache_data, ttl=1800)  # 30 minutes

        except Exception as e:
            logger.error(f"Cache storage error: {e}")

    async def _record_metrics(
        self,
        query: str,
        result: RAGResult,
        context: RAGContext
    ):
        """Record performance metrics"""
        try:
            await performance_monitor.record_metric(
                "rag_pipeline",
                result.generation_time,
                {
                    "query_length": len(query),
                    "context_docs": len(context.documents),
                    "search_time": context.search_time,
                    "tokens_used": result.tokens_used,
                    "confidence": result.confidence,
                    "search_mode": context.search_mode
                }
            )
        except Exception as e:
            logger.error(f"Metrics recording error: {e}")

    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of RAG pipeline components"""
        try:
            health_status = {
                "opensearch": await self.opensearch.health_check(),
                "embedding_service": await self.embedding_service.health_check(),
                "llm_client": await self.llm_client.check_health() if self.llm_client else {"healthy": False, "error": "Not initialized"},
                "cache": await self.cache.health_check() if hasattr(self.cache, 'health_check') else {"healthy": True},
                "timestamp": datetime.now().isoformat()
            }

            # Overall health
            health_status["overall_healthy"] = all(
                component.get("healthy", False)
                for component in health_status.values()
                if isinstance(component, dict) and "healthy" in component
            )

            return health_status

        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {
                "overall_healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }