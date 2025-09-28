"""
PDF parsing schemas and data models
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from pathlib import Path


class ParserType(str, Enum):
    """PDF parser type enumeration"""
    DOCLING = "docling"
    PYPDF = "pypdf"
    PYMuPDF = "pymupdf"
    MANUAL = "manual"


class PaperFigure(BaseModel):
    """Extracted figure from PDF"""
    caption: str
    image_path: Optional[str] = None
    page_number: int
    bounding_box: Optional[Dict[str, float]] = None


class PaperTable(BaseModel):
    """Extracted table from PDF"""
    caption: str
    content: List[List[str]]  # Table data as list of rows
    page_number: int
    bounding_box: Optional[Dict[str, float]] = None


class PaperSection(BaseModel):
    """Structured section from PDF content"""
    title: str
    content: str
    level: int = Field(default=1, ge=1, le=6)  # Section hierarchy level
    page_start: Optional[int] = None
    page_end: Optional[int] = None


class PaperReference(BaseModel):
    """Extracted reference from paper"""
    text: str
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    year: Optional[int] = None


class PdfContent(BaseModel):
    """Complete parsed content from PDF"""
    sections: List[PaperSection]
    figures: List[PaperFigure] = []
    tables: List[PaperTable] = []
    raw_text: str
    references: List[PaperReference] = []
    parser_used: ParserType
    metadata: Dict[str, Any] = {}
    processing_time_seconds: Optional[float] = None
    page_count: Optional[int] = None
    file_size_bytes: Optional[int] = None


class PdfProcessingRequest(BaseModel):
    """Request to process a PDF"""
    paper_id: str
    pdf_path: str
    parser_type: ParserType = ParserType.DOCLING
    force_reprocess: bool = False
    extract_figures: bool = False
    extract_tables: bool = True
    max_pages: Optional[int] = None


class PdfProcessingResponse(BaseModel):
    """Response from PDF processing"""
    paper_id: str
    success: bool
    content: Optional[PdfContent] = None
    error_message: Optional[str] = None
    processing_time_seconds: float
    parser_used: ParserType


class PdfParserConfig(BaseModel):
    """Configuration for PDF parser"""
    max_pages: int = 50
    max_file_size_mb: int = 20
    do_ocr: bool = False
    do_table_structure: bool = True
    do_figure_extraction: bool = False
    timeout_seconds: int = 300
    cache_parsed_content: bool = True
    supported_formats: List[str] = ["pdf"]


class PdfValidationResult(BaseModel):
    """Result of PDF validation"""
    is_valid: bool
    file_size_bytes: int
    page_count: int
    errors: List[str] = []
    warnings: List[str] = []
    metadata: Dict[str, Any] = {}