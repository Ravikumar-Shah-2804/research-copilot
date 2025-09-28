"""
RAG API schemas
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class RAGRequest(BaseModel):
    """RAG request schema"""
    query: str = Field(..., description="The question to answer", min_length=1, max_length=1000)
    context_limit: int = Field(5, description="Maximum number of context documents", ge=1, le=10)
    max_tokens: int = Field(1000, description="Maximum tokens in response", ge=100, le=4000)
    temperature: float = Field(0.7, description="Response temperature", ge=0.0, le=2.0)
    search_mode: str = Field("hybrid", description="Search mode: 'bm25_only', 'vector_only', or 'hybrid'")


class RAGSource(BaseModel):
    """RAG source document schema"""
    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    abstract: Optional[str] = Field(None, description="Document abstract")
    content: Optional[str] = Field(None, description="Document content")
    authors: List[str] = Field(default_factory=list, description="Document authors")
    score: float = Field(..., description="Relevance score")
    url: Optional[str] = Field(None, description="Document URL")


class RAGResponse(BaseModel):
    """RAG response schema"""
    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="Generated answer")
    sources: List[RAGSource] = Field(..., description="Source documents used")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0)", ge=0.0, le=1.0)
    tokens_used: int = Field(..., description="Total tokens used", ge=0)
    generation_time: float = Field(..., description="Time taken to generate response", ge=0.0)
    model: str = Field(..., description="LLM model used")
    context_length: int = Field(..., description="Length of context provided", ge=0)
    degraded: bool = Field(False, description="Whether the response is degraded due to service issues")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class BatchRAGRequest(BaseModel):
    """Batch RAG request schema"""
    queries: List[str] = Field(..., description="List of queries to process", min_items=1, max_items=10)
    context_limit: int = Field(5, description="Maximum number of context documents per query", ge=1, le=10)
    max_tokens: int = Field(1000, description="Maximum tokens per response", ge=100, le=4000)
    temperature: float = Field(0.7, description="Response temperature", ge=0.0, le=2.0)
    search_mode: str = Field("hybrid", description="Search mode for all queries")


class BatchRAGResponse(BaseModel):
    """Batch RAG response schema"""
    results: List[RAGResponse] = Field(..., description="Results for each query")
    total_queries: int = Field(..., description="Total number of queries processed")
    total_tokens: int = Field(..., description="Total tokens used across all queries")
    total_time: float = Field(..., description="Total processing time", ge=0.0)
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class StreamingRAGResponse(BaseModel):
    """Streaming RAG response chunk schema"""
    type: str = Field(..., description="Chunk type: 'text' or 'sources'")
    content: Optional[str] = Field(None, description="Text content chunk")
    sources: Optional[List[RAGSource]] = Field(None, description="Source documents (final chunk)")
    done: bool = Field(False, description="Whether streaming is complete")


class LLMModelInfo(BaseModel):
    """LLM model information schema"""
    id: str = Field(..., description="Model ID")
    name: str = Field(..., description="Model name")
    context_length: Optional[int] = Field(None, description="Maximum context length")
    pricing: Optional[Dict[str, float]] = Field(None, description="Pricing information")


class AvailableModelsResponse(BaseModel):
    """Available models response schema"""
    models: List[LLMModelInfo] = Field(..., description="Available models")
    default_model: str = Field(..., description="Default model ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class HealthStatus(BaseModel):
    """Health status schema"""
    service: str = Field(..., description="Service name")
    healthy: bool = Field(..., description="Whether service is healthy")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    response_time: Optional[float] = Field(None, description="Response time in seconds")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    timestamp: datetime = Field(default_factory=datetime.now, description="Check timestamp")


class RAGHealthResponse(BaseModel):
    """RAG system health response schema"""
    overall_healthy: bool = Field(..., description="Overall system health")
    services: Dict[str, HealthStatus] = Field(..., description="Individual service health status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")


class UsageStats(BaseModel):
    """Usage statistics schema"""
    total_requests: int = Field(..., description="Total requests made", ge=0)
    total_tokens: int = Field(..., description="Total tokens used", ge=0)
    total_cost: float = Field(..., description="Total cost incurred", ge=0.0)
    errors: int = Field(..., description="Total errors encountered", ge=0)
    average_response_time: Optional[float] = Field(None, description="Average response time", ge=0.0)
    last_reset: datetime = Field(..., description="Last statistics reset timestamp")
    timestamp: datetime = Field(default_factory=datetime.now, description="Statistics timestamp")


class RAGConfig(BaseModel):
    """RAG configuration schema"""
    default_model: str = Field(..., description="Default LLM model")
    max_context_docs: int = Field(..., description="Maximum context documents")
    context_window_size: int = Field(..., description="Context window size in tokens")
    default_temperature: float = Field(..., description="Default temperature")
    default_max_tokens: int = Field(..., description="Default max tokens")
    cache_ttl: int = Field(..., description="Cache TTL in seconds")
    batch_max_queries: int = Field(..., description="Maximum queries per batch")
    rate_limit_requests_per_minute: int = Field(..., description="Rate limit for requests")
    rate_limit_streaming_requests_per_minute: int = Field(..., description="Rate limit for streaming")
    rate_limit_batch_max_queries_per_minute: int = Field(..., description="Rate limit for batch queries")