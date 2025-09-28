"""
OpenRouter LLM Service implementation
"""
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator

from .base import BaseLLMService, LLMConfig, LLMResponse, RAGRequest, RAGResponse
from ..openrouter import OpenRouterClient, OpenRouterError

logger = logging.getLogger(__name__)


class OpenRouterLLMService(BaseLLMService):
    """OpenRouter-based LLM service"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = OpenRouterClient()
        self.client.model = config.model

    async def __aenter__(self):
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def generate_completion(
        self,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Generate text completion"""
        try:
            # Merge config with kwargs
            params = {
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                **kwargs
            }

            result = await self.client.generate_completion(
                prompt=prompt,
                **params
            )

            return LLMResponse(
                text=result["text"],
                usage=result["usage"],
                model=result["model"],
                cost=self.estimate_cost(
                    result["usage"].get("total_tokens", 0),
                    result["model"]
                )
            )

        except OpenRouterError as e:
            logger.error(f"OpenRouter completion error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected completion error: {e}")
            raise

    async def generate_rag_response(
        self,
        request: RAGRequest
    ) -> RAGResponse:
        """Generate RAG response with context"""
        try:
            result = await self.client.generate_rag_response(
                query=request.query,
                context_docs=request.context_docs,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )

            # Calculate confidence (simple implementation)
            confidence = min(1.0, len(request.context_docs) / 10)

            return RAGResponse(
                answer=result["answer"],
                sources=result["sources"],
                usage=result["usage"],
                model=result["model"],
                confidence=confidence,
                cost=self.estimate_cost(
                    result["usage"].get("total_tokens", 0),
                    result["model"]
                )
            )

        except OpenRouterError as e:
            logger.error(f"OpenRouter RAG error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected RAG error: {e}")
            raise

    async def generate_streaming_response(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response"""
        try:
            async for chunk in self.client.generate_streaming_response(
                query=prompt,
                **kwargs
            ):
                yield chunk

        except OpenRouterError as e:
            logger.error(f"OpenRouter streaming error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected streaming error: {e}")
            raise

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get available models"""
        try:
            return await self.client.get_available_models()
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return []

    async def check_health(self) -> Dict[str, Any]:
        """Check service health"""
        try:
            return await self.client.check_health()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"healthy": False, "error": str(e)}

    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        try:
            return await self.client.get_usage_stats()
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {}

    def estimate_cost(self, tokens: int, model: str) -> float:
        """Estimate cost for token usage"""
        # DeepSeek pricing (approximate)
        cost_per_token = 0.000001  # $0.001 per 1000 tokens
        return (tokens / 1000) * cost_per_token