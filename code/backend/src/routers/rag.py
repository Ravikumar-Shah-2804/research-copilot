"""
RAG (Retrieval-Augmented Generation) API endpoints
"""
import json
import time
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..services.auth import get_current_active_user
from ..services.rag_pipeline import RAGPipeline
from ..services.monitoring import performance_monitor, search_analytics
from ..services.rate_limiting import rag_rate_limiter, rate_limit
from ..services.audit import search_audit_logger
from ..schemas.rag import RAGRequest, RAGResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=RAGResponse)
# @rate_limit("rag")
async def generate_answer(
    request: RAGRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate answer directly using OpenRouter"""
    start_time = time.time()
    logger.info(f"Starting direct OpenRouter generation for user {current_user.id}, query: {request.query[:50]}...")

    try:
        # Direct call to OpenRouter LLM service
        logger.info(f"Calling OpenRouter directly for query: {request.query[:50]}...")
        from ..services.llm import LLMFactory
        llm_service = LLMFactory.create_service("openrouter")

        async with llm_service:
            result = await llm_service.generate_completion(
                prompt=request.query,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
        logger.info(f"OpenRouter response received: model={result.model}, tokens={result.usage.get('total_tokens', 0)}")

        generation_time = time.time() - start_time

        # Record analytics (simplified)
        await search_analytics.record_search_query(
            query=request.query,
            mode="direct",
            results_count=0,  # No sources
            search_time=generation_time,
            user_id=str(current_user.id) if current_user else None,
            filters={}
        )

        # Audit logging
        await search_audit_logger.log_rag_query(
            db,
            user_id=current_user.id if current_user else None,
            query=request.query,
            sources_count=0,
            tokens_used=result.usage.get("total_tokens", 0),
            model=result.model,
            duration=generation_time
        )

        logger.info(f"Direct OpenRouter generation completed, tokens: {result.usage.get('total_tokens', 0)}, time: {generation_time:.3f}s")
        return RAGResponse(
            query=request.query,
            answer=result.text,
            sources=[],  # No sources for direct call
            confidence=1.0,  # High confidence for direct LLM response
            tokens_used=result.usage.get("total_tokens", 0),
            generation_time=generation_time,
            model=result.model,
            context_length=0,  # No context
            degraded=False
        )

    except Exception as e:
        logger.error(f"Direct OpenRouter generation failed for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/stream")
@rate_limit("rag")
async def stream_answer(
    request: RAGRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Stream RAG answer generation with retrieval"""
    logger.info(f"Starting RAG streaming for user {current_user.id}, query: {request.query[:50]}...")
    logger.info(f"Request data: query={request.query}, context_limit={request.context_limit}, max_tokens={request.max_tokens}, temperature={request.temperature}, search_mode={request.search_mode}")
    try:
        async def generate_stream():
            # Retrieve context using RAGPipeline
            async with RAGPipeline() as rag_pipeline:
                context = await rag_pipeline._retrieve_context(
                    query=request.query,
                    search_mode=request.search_mode or "hybrid",
                    context_limit=request.context_limit or 5
                )
                logger.info(f"Retrieved {len(context.documents)} context documents for streaming")

                # Stream response with context
                from ..services.openrouter import OpenRouterClient
                client = OpenRouterClient()

                async with client:
                    async for chunk in client.generate_streaming_response(
                        query=request.query,
                        context_docs=context.documents,
                        max_tokens=request.max_tokens,
                        temperature=request.temperature
                    ):
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"

                # Send sources and done
                yield f"data: {json.dumps({'type': 'sources', 'sources': context.documents})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

        logger.info(f"RAG streaming initiated for user {current_user.id}")
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    except Exception as e:
        logger.error(f"RAG streaming failed for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Streaming failed: {str(e)}")


@router.post("/batch")
@rate_limit("rag")
async def batch_generate(
    queries: List[str] = Query(..., description="List of queries to process"),
    context_limit: int = Query(5, description="Number of context documents per query"),
    max_tokens: int = Query(1000, description="Max tokens per response"),
    temperature: float = Query(0.7, description="Response temperature"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Batch generate answers for multiple queries"""
    logger.info(f"Starting RAG batch generation for user {current_user.id}, query count {len(queries)}, context limit {context_limit}")
    if len(queries) > 10:
        logger.warning(f"Batch query limit exceeded for user {current_user.id}, query count {len(queries)}")
        raise HTTPException(status_code=400, detail="Maximum 10 queries per batch")

    try:
        results = []
        async with RAGPipeline() as rag_pipeline:
            for query in queries:
                result = await rag_pipeline.generate_answer(
                    query=query,
                    search_mode="hybrid",
                    context_limit=context_limit,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    use_cache=True
                )

                results.append({
                    "query": query,
                    "answer": result.answer,
                    "sources": result.sources,
                    "confidence": result.confidence,
                    "tokens_used": result.tokens_used,
                    "generation_time": result.generation_time,
                    "model": result.model,
                    "context_length": result.context_length,
                    "degraded": result.degraded
                })

        # Audit logging
        total_tokens = sum(result.get("tokens_used", 0) for result in results)
        search_audit_logger.log_rag_operation(
            user_id=str(current_user.id) if current_user else "anonymous",
            operation="rag_batch",
            query=f"batch:{len(queries)} queries",
            context_docs=len(queries),
            tokens_used=total_tokens,
            duration=time.time() - time.time()  # Would need to track total time
        )

        logger.info(f"RAG batch generation completed successfully for user {current_user.id}, total queries {len(queries)}, total tokens {total_tokens}")
        return {"results": results, "total_queries": len(queries)}

    except Exception as e:
        logger.error("RAG batch generation failed", user_id=current_user.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"RAG batch generation failed: {str(e)}")


@router.get("/models")
async def get_available_models(
    current_user: User = Depends(get_current_active_user)
):
    """Get available LLM models for RAG"""
    logger.info(f"Retrieving available RAG models for user {current_user.id}")
    try:
        from ..services.llm import LLMFactory
        llm_service = LLMFactory.create_service("openrouter")

        async with llm_service:
            models = await llm_service.get_available_models()

        # Filter for DeepSeek models
        deepseek_models = [
            model for model in models
            if "x-ai" in model.get("id", "").lower()
        ]

        logger.info(f"Available RAG models retrieved successfully for user {current_user.id}, model count {len(deepseek_models)}")
        return {
            "models": deepseek_models,
            "default_model": "x-ai/grok-4-fast:free"
        }

    except Exception as e:
        logger.error("Failed to get RAG models", user_id=current_user.id, error=str(e), exc_info=True)
        return {"models": [], "error": str(e)}


@router.get("/health")
async def rag_health_check(
    current_user: User = Depends(get_current_active_user)
):
    """Check RAG system health"""
    logger.info(f"Performing RAG health check for user {current_user.id}")
    try:
        async with RAGPipeline() as rag_pipeline:
            health = await rag_pipeline.get_health_status()

        logger.info(f"RAG health check completed for user {current_user.id}, overall healthy {health.get('overall_healthy')}")
        return health

    except Exception as e:
        logger.error("RAG health check failed", user_id=current_user.id, error=str(e), exc_info=True)
        return {
            "overall_healthy": False,
            "error": str(e),
            "timestamp": time.time()
        }


@router.get("/usage")
async def get_rag_usage(
    current_user: User = Depends(get_current_active_user)
):
    """Get RAG usage statistics"""
    logger.info(f"Retrieving RAG usage statistics for user {current_user.id}")
    try:
        from ..services.llm import LLMFactory
        llm_service = LLMFactory.create_service("openrouter")

        async with llm_service:
            usage = await llm_service.get_usage_stats()

        logger.info(f"RAG usage statistics retrieved successfully for user {current_user.id}")
        return usage

    except Exception as e:
        logger.error("Failed to get RAG usage stats", user_id=current_user.id, error=str(e), exc_info=True)
        return {"error": str(e)}