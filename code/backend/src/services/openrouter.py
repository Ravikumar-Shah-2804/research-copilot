"""
OpenRouter DeepSeek service with enhanced error handling and enterprise features
"""
import asyncio
import httpx
import logging
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
import json
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import settings
from .cache import RedisCache
from .monitoring import performance_monitor
from .rate_limiting import RateLimiter

logger = logging.getLogger(__name__)


class OpenRouterError(Exception):
    """Base exception for OpenRouter errors"""
    pass


class OpenRouterRateLimitError(OpenRouterError):
    """Rate limit exceeded"""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class OpenRouterAuthError(OpenRouterError):
    """Authentication error"""
    pass


class OpenRouterQuotaError(OpenRouterError):
    """Quota exceeded"""
    pass


class OpenRouterClient:
    """Enhanced OpenRouter API client for DeepSeek with enterprise features"""

    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = settings.deepseek_model
        self.client = None
        self.cache = RedisCache()
        self.rate_limiter = RateLimiter()
        self.usage_stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "errors": 0,
            "last_reset": datetime.now()
        }
        self._setup_client()

    def _setup_client(self):
        """Setup HTTP client with proper configuration"""
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://research-copilot.com",
                "X-Title": "Research Copilot"
            },
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )

    async def __aenter__(self):
        await self.cache.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
        await self.cache.disconnect()

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle API errors and raise appropriate exceptions"""
        if response.status_code == 401:
            raise OpenRouterAuthError("Invalid API key")
        elif response.status_code == 429:
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                try:
                    retry_after = int(retry_after)
                    logger.warning(f"Rate limit exceeded. Retry-After: {retry_after} seconds")
                except ValueError:
                    retry_after = None
                    logger.warning("Rate limit exceeded. Invalid Retry-After header")
            else:
                logger.warning("Rate limit exceeded")
            raise OpenRouterRateLimitError("Rate limit exceeded", retry_after)
        elif response.status_code == 402:
            raise OpenRouterQuotaError("Quota exceeded")
        elif response.status_code >= 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
            except:
                error_msg = response.text or "Unknown error"
            raise OpenRouterError(f"API error: {error_msg}")

    def _update_usage_stats(self, usage: Dict[str, Any]) -> None:
        """Update usage statistics"""
        self.usage_stats["total_requests"] += 1
        if "total_tokens" in usage:
            self.usage_stats["total_tokens"] += usage["total_tokens"]

        # Estimate cost (rough calculation - would need actual pricing)
        if "total_tokens" in usage:
            # Approximate cost per token for DeepSeek
            cost_per_token = 0.000001  # $0.001 per 1000 tokens
            self.usage_stats["total_cost"] += usage["total_tokens"] * cost_per_token

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, OpenRouterRateLimitError)),
        before_sleep=lambda retry_state: logger.info(f"Retrying OpenRouter request in {retry_state.next_action.sleep} seconds (attempt {retry_state.attempt_number})")
    )
    async def _make_request(self, endpoint: str, payload: Dict[str, Any], stream: bool = False) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        url = f"{self.base_url}/{endpoint}"

        # Check rate limit before making request
        allowed, limit_info = await self.rate_limiter.check_rate_limit(
            identifier="openrouter",
            endpoint=endpoint,
            requests_per_window=30,  # 30 requests per minute
            window_seconds=60
        )

        if not allowed:
            raise OpenRouterRateLimitError("Rate limit exceeded")

        try:
            async with performance_monitor.measure_time(f"openrouter_{endpoint}"):
                response = await self.client.post(url, json=payload)
                response.raise_for_status()

                if stream:
                    return {"stream": response.aiter_lines()}
                else:
                    return response.json()

        except httpx.HTTPStatusError as e:
            self._handle_error(e.response)
        except Exception as e:
            self.usage_stats["errors"] += 1
            logger.error(f"OpenRouter request failed: {e}")
            raise

    async def generate_completion(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        context: Optional[List[Dict[str, str]]] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Generate completion using DeepSeek with caching"""
        # Create cache key
        cache_key = None
        if use_cache:
            cache_content = {
                "prompt": prompt,
                "context": context,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "model": self.model
            }
            cache_key = f"completion:{hash(json.dumps(cache_content, sort_keys=True))}"

            # Check cache first
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.info("Returning cached completion")
                return cached_result

        try:
            messages = []
            if context:
                messages.extend(context)
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }

            result = await self._make_request("chat/completions", payload)

            response_data = {
                "text": result["choices"][0]["message"]["content"],
                "usage": result.get("usage", {}),
                "model": result.get("model", self.model),
                "timestamp": datetime.now().isoformat()
            }

            # Update usage stats
            self._update_usage_stats(result.get("usage", {}))

            # Cache the result
            if cache_key:
                await self.cache.set(cache_key, response_data, ttl=3600)  # 1 hour

            return response_data

        except Exception as e:
            logger.error(f"OpenRouter completion error: {e}")
            raise

    async def generate_rag_response(
        self,
        query: str,
        context_docs: List[Dict[str, Any]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Generate RAG response with context and intelligent prompt engineering"""
        # Create cache key
        cache_key = None
        if use_cache:
            cache_content = {
                "query": query,
                "context_docs": [{"id": doc.get("id"), "title": doc.get("title")} for doc in context_docs],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "model": self.model
            }
            cache_key = f"rag:{hash(json.dumps(cache_content, sort_keys=True))}"

            # Check cache first
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.info("Returning cached RAG response")
                return cached_result

        try:
            # Compress context if too long
            context_text = self._compress_context(context_docs, max_context_length=8000)

            # Enhanced system prompt with better instructions
            system_prompt = """You are an expert research assistant specializing in academic paper analysis.

Your task is to provide accurate, comprehensive answers based on the provided research paper context. Follow these guidelines:

1. **Answer directly and comprehensively** using only the information from the provided context
2. **Cite specific papers** by mentioning their titles and key findings
3. **Be precise** - don't add external knowledge or assumptions
4. **Structure your answer** with clear sections if the question is complex
5. **Acknowledge limitations** - if the context doesn't fully answer the question, clearly state what's missing
6. **Use academic tone** appropriate for research discussions

If the context is insufficient to answer the question, clearly state this and suggest what additional information would be needed."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context from research papers:\n{context_text}\n\nQuestion: {query}\n\nPlease provide a comprehensive answer based on the above context."}
            ]

            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }

            result = await self._make_request("chat/completions", payload)

            response_data = {
                "answer": result["choices"][0]["message"]["content"],
                "sources": context_docs,
                "usage": result.get("usage", {}),
                "model": result.get("model", self.model),
                "timestamp": datetime.now().isoformat(),
                "context_length": len(context_text)
            }

            # Update usage stats
            self._update_usage_stats(result.get("usage", {}))

            # Cache the result
            if cache_key:
                await self.cache.set(cache_key, response_data, ttl=1800)  # 30 minutes

            return response_data

        except Exception as e:
            logger.error(f"RAG generation error: {e}")
            raise

    def _compress_context(self, context_docs: List[Dict[str, Any]], max_context_length: int = 8000) -> str:
        """Compress context to fit within token limits"""
        context_parts = []

        for i, doc in enumerate(context_docs):
            title = doc.get("title", f"Document {i+1}")
            content = doc.get("content", doc.get("abstract", ""))

            # Truncate content if too long
            if len(content) > 2000:
                content = content[:2000] + "..."

            part = f"Paper {i+1}: {title}\n{content}"
            context_parts.append(part)

        # Join and truncate if necessary
        full_context = "\n\n".join(context_parts)
        if len(full_context) > max_context_length:
            full_context = full_context[:max_context_length] + "\n\n[Context truncated due to length]"

        return full_context

    async def generate_streaming_response(
        self,
        query: str,
        context_docs: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Generate streaming RAG response"""
        try:
            messages = []
            if context_docs:
                context_text = self._compress_context(context_docs, max_context_length=6000)
                system_prompt = """You are an expert research assistant. Provide accurate answers based on the research context provided."""

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {query}"}
                ]
            else:
                messages = [{"role": "user", "content": query}]

            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True
            }

            result = await self._make_request("chat/completions", payload, stream=True)

            async for line in result["stream"]:
                if line.strip():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if chunk.get("choices"):
                                delta = chunk["choices"][0].get("delta", {})
                                if delta.get("content"):
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            logger.error(f"Streaming response error: {e}")
            raise

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get available models from OpenRouter with caching"""
        cache_key = "openrouter_models"

        # Check cache first
        cached_models = await self.cache.get(cache_key)
        if cached_models:
            return cached_models

        try:
            response = await self.client.get(f"{self.base_url}/models")
            response.raise_for_status()
            models = response.json().get("data", [])

            # Cache for 1 hour
            await self.cache.set(cache_key, models, ttl=3600)

            return models
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return []

    async def check_health(self) -> Dict[str, Any]:
        """Check OpenRouter service health with detailed status"""
        try:
            response = await self.client.get(f"{self.base_url}/models")
            return {
                "healthy": response.status_code == 200,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            **self.usage_stats,
            "current_timestamp": datetime.now().isoformat()
        }

    async def reset_usage_stats(self):
        """Reset usage statistics"""
        self.usage_stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "errors": 0,
            "last_reset": datetime.now()
        }
        logger.info("OpenRouter usage stats reset")