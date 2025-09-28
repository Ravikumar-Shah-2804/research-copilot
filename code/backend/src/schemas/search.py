"""
Search schemas
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class SearchRequest(BaseModel):
    """Search request schema"""
    query: str
    mode: str = "hybrid"  # "bm25_only", "vector_only", "hybrid"
    limit: int = 10
    offset: int = 0
    filters: Optional[Dict[str, Any]] = None
    include_highlights: bool = True
    search_fields: Optional[List[str]] = None
    field_boosts: Optional[Dict[str, float]] = None


class SearchResult(BaseModel):
    """Individual search result"""
    id: str
    title: str
    abstract: Optional[str] = None
    authors: List[str] = []
    score: float
    highlights: Optional[Dict[str, List[str]]] = None


class SearchResponse(BaseModel):
    """Search response schema"""
    query: str
    total: int
    results: List[SearchResult]
    took: float


class RAGRequest(BaseModel):
    """RAG request schema"""
    query: str
    context_limit: int = 5
    max_tokens: int = 1000
    temperature: float = 0.7


class RAGResponse(BaseModel):
    """RAG response schema"""
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    tokens_used: int