"""
Search and RAG router
"""
import time
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ..database import get_db
from ..models.user import User
from ..services.auth import get_current_active_user
from ..services.opensearch import OpenSearchService
from ..services.cache import RedisCache
from ..services.embeddings import EmbeddingService
from ..services.openrouter import OpenRouterClient
from ..services.monitoring import performance_monitor, search_analytics
from ..services.rate_limiting import search_rate_limiter, rate_limit
from ..services.audit import search_audit_logger
from ..schemas.search import SearchRequest, SearchResponse, RAGRequest, RAGResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/text", response_model=SearchResponse)
@rate_limit("search")
async def text_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Text-based search with BM25, vector, or hybrid modes"""
    start_time = time.time()

    try:
        # Initialize services
        from ..services.embeddings import EmbeddingService
        embedding_service = EmbeddingService()
        opensearch = OpenSearchService(provider=embedding_service.provider)
        await opensearch.connect()

        embedding_service = EmbeddingService()
        await embedding_service.__aenter__()

        cache = RedisCache()
        await cache.connect()

        # Generate embedding for vector search if needed
        vector_query = None
        if request.mode in ["vector_only", "hybrid"]:
            vector_query = await embedding_service.embed_text(request.query)

        # Perform search based on mode
        if request.mode == "bm25_only":
            search_result = opensearch.bm25_search(
                query=request.query,
                fields=request.search_fields,
                field_boosts=request.field_boosts,
                filters=request.filters,
                size=request.limit,
                highlight=request.include_highlights
            )
        elif request.mode == "vector_only":
            search_result = opensearch.vector_search(
                vector=vector_query,
                filters=request.filters,
                size=request.limit
            )
        elif request.mode == "hybrid":
            search_result = opensearch.hybrid_search(
                text_query=request.query,
                vector_query=vector_query,
                mode="hybrid",
                filters=request.filters,
                size=request.limit,
                highlight=request.include_highlights
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown search mode: {request.mode}")

        # Format results
        results = []
        for hit in search_result["hits"]["hits"]:
            source = hit["_source"]
            result = {
                "id": hit["_id"],
                "title": source.get("title", ""),
                "abstract": source.get("abstract"),
                "authors": source.get("authors", []),
                "score": hit["_score"],
                "highlights": hit.get("highlight", {})
            }
            results.append(result)

        # Calculate search time
        search_time = time.time() - start_time

        response = SearchResponse(
            query=request.query,
            total=search_result["hits"]["total"]["value"],
            results=results,
            took=search_time
        )

        # Record analytics
        await search_analytics.record_search_query(
            query=request.query,
            mode=request.mode,
            results_count=len(results),
            search_time=search_time,
            user_id=str(current_user.id) if current_user else None,
            filters=request.filters
        )

        # Audit logging
        search_audit_logger.log_search_operation(
            user_id=str(current_user.id) if current_user else "anonymous",
            operation="search",
            query=request.query,
            mode=request.mode,
            result_count=len(results),
            duration=search_time
        )

        # Cache successful searches
        cache_key = f"search:{hash(request.json())}"
        await cache.set(cache_key, response.dict(), ttl=300)  # 5 minutes

        return response

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    finally:
        # Cleanup
        try:
            await embedding_service.__aexit__(None, None, None)
            await cache.disconnect()
        except:
            pass


@router.post("/hybrid", response_model=SearchResponse)
async def hybrid_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Hybrid search combining text and vector search"""
    # This endpoint is now redundant with /text endpoint that supports modes
    # Keeping for backward compatibility
    request.mode = "hybrid"
    return await text_search(request, current_user, db)


@router.post("/rag", response_model=RAGResponse)
async def rag_query(
    request: RAGRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """RAG (Retrieval-Augmented Generation) query"""
    try:
        # Initialize services
        from ..services.embeddings import EmbeddingService
        embedding_service = EmbeddingService()
        opensearch = OpenSearchService(provider=embedding_service.provider)
        await opensearch.connect()

        embedding_service = EmbeddingService()
        await embedding_service.__aenter__()

        # Generate embedding for the query
        query_embedding = await embedding_service.embed_text(request.query)

        # Perform hybrid search to get relevant context
        search_result = opensearch.hybrid_search(
            text_query=request.query,
            vector_query=query_embedding,
            mode="hybrid",
            size=request.context_limit,
            highlight=False
        )

        # Extract context documents
        context_docs = []
        for hit in search_result["hits"]["hits"]:
            source = hit["_source"]
            doc = {
                "id": hit["_id"],
                "title": source.get("title", ""),
                "abstract": source.get("abstract", ""),
                "content": source.get("content", ""),
                "score": hit["_score"]
            }
            context_docs.append(doc)

        # Generate RAG response using OpenRouter
        async with OpenRouterClient() as openrouter:
            rag_result = await openrouter.generate_rag_response(
                query=request.query,
                context_docs=context_docs,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )

        return RAGResponse(
            query=request.query,
            answer=rag_result["answer"],
            sources=rag_result["sources"],
            confidence=0.8,  # TODO: Implement confidence scoring
            tokens_used=rag_result["usage"].get("total_tokens", 0)
        )

    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")
    finally:
        # Cleanup
        try:
            await embedding_service.__aexit__(None, None, None)
        except:
            pass


@router.get("/suggestions")
async def search_suggestions(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user)
):
    """Get search suggestions based on partial query"""
    try:
        from ..services.embeddings import EmbeddingService
        embedding_service = EmbeddingService()
        opensearch = OpenSearchService(provider=embedding_service.provider)
        await opensearch.connect()

        # Use completion suggester for search suggestions
        query = {
            "suggest": {
                "title-suggest": {
                    "text": q,
                    "completion": {
                        "field": "title",
                        "size": limit,
                        "skip_duplicates": True
                    }
                },
                "author-suggest": {
                    "text": q,
                    "completion": {
                        "field": "authors",
                        "size": limit,
                        "skip_duplicates": True
                    }
                }
            }
        }

        result = opensearch.search(query, size=0)  # size=0 to not return hits
        suggestions = []

        # Extract suggestions
        if "suggest" in result:
            for suggester_name, suggester_results in result["suggest"].items():
                for suggestion in suggester_results:
                    if "options" in suggestion:
                        for option in suggestion["options"]:
                            suggestions.append({
                                "text": option["text"],
                                "score": option.get("_score", 0),
                                "type": suggester_name.split("-")[0]
                            })

        # Sort by score and limit
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return {"suggestions": suggestions[:limit]}

    except Exception as e:
        logger.error(f"Search suggestions failed: {e}")
        return {"suggestions": []}


@router.get("/popular")
async def popular_searches(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get popular search queries"""
    try:
        cache = RedisCache()
        await cache.connect()

        # For now, return some default popular searches
        # TODO: Implement actual analytics tracking
        popular_queries = [
            "machine learning",
            "deep learning",
            "neural networks",
            "computer vision",
            "natural language processing",
            "reinforcement learning",
            "artificial intelligence",
            "data science",
            "quantum computing",
            "blockchain"
        ]

        return {"popular_searches": popular_queries[:limit]}

    except Exception as e:
        logger.error(f"Popular searches failed: {e}")
        return {"popular_searches": []}
    finally:
        try:
            await cache.disconnect()
        except:
            pass