"""
arXiv API schemas and data models
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ArxivPaper(BaseModel):
    """arXiv paper metadata from API"""
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    categories: List[str]
    published_date: datetime
    pdf_url: str
    doi: Optional[str] = None
    journal_ref: Optional[str] = None
    comments: Optional[str] = None
    updated_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class ArxivSearchQuery(BaseModel):
    """arXiv search query parameters"""
    query: Optional[str] = None
    category: Optional[str] = None
    author: Optional[str] = None
    title: Optional[str] = None
    abstract: Optional[str] = None
    from_date: Optional[str] = None  # Format: YYYYMMDD
    to_date: Optional[str] = None    # Format: YYYYMMDD
    max_results: int = Field(default=100, ge=1, le=2000)
    start: int = Field(default=0, ge=0)
    sort_by: str = Field(default="submittedDate", pattern="^(submittedDate|lastUpdatedDate|relevance)$")
    sort_order: str = Field(default="descending", pattern="^(ascending|descending)$")


class ArxivIngestionRequest(BaseModel):
    """Request to ingest papers from arXiv"""
    search_query: ArxivSearchQuery
    batch_size: int = Field(default=50, ge=1, le=200)
    max_papers: Optional[int] = Field(default=None, ge=1, le=10000)
    process_pdfs: bool = True
    skip_duplicates: bool = True
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")


class ArxivIngestionResponse(BaseModel):
    """Response from arXiv ingestion request"""
    job_id: str
    status: str
    message: str
    estimated_papers: Optional[int] = None
    search_criteria: Dict[str, Any]


class ArxivIngestionStatus(BaseModel):
    """Status of an ongoing arXiv ingestion job"""
    job_id: str
    status: str  # pending, running, completed, failed, cancelled
    progress: Dict[str, Any]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    errors: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {}


class ArxivApiConfig(BaseModel):
    """Configuration for arXiv API client"""
    base_url: str = "http://export.arxiv.org/api/query"
    rate_limit_delay: float = 3.0  # seconds between requests
    timeout_seconds: int = 30
    max_results_per_request: int = 2000
    max_retries: int = 3
    retry_delay_base: float = 1.0
    namespaces: Dict[str, str] = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom"
    }