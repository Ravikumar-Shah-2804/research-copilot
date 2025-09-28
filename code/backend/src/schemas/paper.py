"""
Paper schemas with comprehensive ingestion support
"""
from pydantic import BaseModel, HttpUrl, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from uuid import UUID
from enum import Enum


class IngestionStatus(str, Enum):
    """Paper ingestion status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ParserType(str, Enum):
    """PDF parser type enumeration"""
    DOCLING = "docling"
    PYPDF = "pypdf"
    MANUAL = "manual"


class Visibility(str, Enum):
    """Paper visibility enumeration"""
    PUBLIC = "public"
    ORGANIZATION = "organization"
    PRIVATE = "private"


class PaperSection(BaseModel):
    """Structured section from PDF content"""
    title: str
    content: str
    level: Optional[int] = 1  # Section hierarchy level


class PaperReference(BaseModel):
    """Extracted reference from paper"""
    text: str
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    title: Optional[str] = None


class PaperCreate(BaseModel):
    """Paper creation schema with comprehensive metadata"""
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
    source: str = "arxiv"
    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None

    # Organization-based access control
    organization_id: Optional[UUID] = None
    visibility: Visibility = Visibility.PUBLIC

    # Comprehensive metadata
    license: Optional[str] = None
    version: Optional[str] = None
    submission_date: Optional[datetime] = None
    update_date: Optional[datetime] = None
    citation_count: int = 0
    view_count: int = 0
    download_count: int = 0
    arxiv_version: Optional[str] = None
    primary_category: Optional[str] = None

    @field_validator('published_date', mode='before')
    @classmethod
    def ensure_naive_published_date(cls, v):
        if isinstance(v, str):
            # Parse string to datetime, make it naive
            dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return dt
        elif isinstance(v, datetime):
            if v.tzinfo is not None:
                return v.replace(tzinfo=None)
            return v
        return v


class PaperUpdate(BaseModel):
    """Paper update schema"""
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    doi: Optional[str] = None
    journal_ref: Optional[str] = None
    comments: Optional[str] = None
    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    quality_score: Optional[float] = None
    ingestion_status: Optional[IngestionStatus] = None

    # Organization-based access control
    organization_id: Optional[UUID] = None
    visibility: Optional[Visibility] = None

    # Comprehensive metadata
    license: Optional[str] = None
    version: Optional[str] = None
    submission_date: Optional[datetime] = None
    update_date: Optional[datetime] = None
    citation_count: Optional[int] = None
    view_count: Optional[int] = None
    download_count: Optional[int] = None
    arxiv_version: Optional[str] = None
    primary_category: Optional[str] = None


class PaperIngestionUpdate(BaseModel):
    """Schema for updating paper during ingestion process"""
    raw_text: Optional[str] = None
    sections: Optional[List[PaperSection]] = None
    references: Optional[List[PaperReference]] = None
    parser_used: Optional[ParserType] = None
    parser_metadata: Optional[Dict[str, Any]] = None
    pdf_processed: bool = False
    pdf_processing_date: Optional[datetime] = None
    pdf_file_size: Optional[str] = None
    pdf_page_count: Optional[int] = None
    ingestion_status: IngestionStatus
    ingestion_attempts: Optional[int] = None
    last_ingestion_attempt: Optional[datetime] = None
    ingestion_errors: Optional[List[Dict[str, Any]]] = None


class PaperResponse(BaseModel):
    """Paper response schema with full metadata"""
    id: UUID
    arxiv_id: str
    doi: Optional[str] = None
    title: str
    authors: List[str]
    abstract: str
    categories: List[str]
    published_date: datetime
    pdf_url: str

    # Content fields
    raw_text: Optional[str] = None
    sections: Optional[List[PaperSection]] = None
    references: Optional[List[PaperReference]] = None

    # Processing metadata
    parser_used: Optional[ParserType] = None
    parser_metadata: Optional[Dict[str, Any]] = None
    pdf_processed: bool = False
    pdf_processing_date: Optional[datetime] = None
    pdf_file_size: Optional[str] = None
    pdf_page_count: Optional[int] = None

    # Additional metadata
    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    journal_ref: Optional[str] = None
    comments: Optional[str] = None

    # Status and tracking
    ingestion_status: IngestionStatus
    ingestion_attempts: int = 0
    last_ingestion_attempt: Optional[datetime] = None
    ingestion_errors: Optional[List[Dict[str, Any]]] = None

    # Audit fields
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    last_modified_by: Optional[UUID] = None

    # Enterprise fields
    source: str
    quality_score: Optional[float] = None
    duplicate_of: Optional[UUID] = None

    # Organization-based access control
    organization_id: Optional[UUID] = None
    visibility: Visibility

    # Comprehensive metadata tracking
    license: Optional[str] = None
    version: Optional[str] = None
    submission_date: Optional[datetime] = None
    update_date: Optional[datetime] = None
    citation_count: int = 0
    view_count: int = 0
    download_count: int = 0
    arxiv_version: Optional[str] = None
    primary_category: Optional[str] = None

    class Config:
        from_attributes = True


class PaperListResponse(BaseModel):
    """Paginated paper list response"""
    papers: List[PaperResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class PaperIngestionStats(BaseModel):
    """Statistics for paper ingestion pipeline"""
    total_papers: int
    processed_papers: int
    papers_with_text: int
    failed_ingestions: int
    processing_rate: float
    text_extraction_rate: float
    average_processing_time: Optional[float] = None
    last_ingestion_run: Optional[datetime] = None