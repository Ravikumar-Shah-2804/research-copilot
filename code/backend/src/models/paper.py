"""
Research paper model with comprehensive ingestion support
"""
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text, func, ForeignKey, Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from ..database import Base

if TYPE_CHECKING:
    from .user import User
    from .role import Organization


class ResearchPaper(Base):
    """Research paper model with comprehensive metadata and content support"""
    __tablename__ = "research_papers"

    # Core identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    arxiv_id = Column(String(255), unique=True, nullable=False, index=True)
    doi = Column(String(255), unique=True)

    # Organization-based access control
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=True)
    visibility = Column(String(50), default='public', nullable=False)  # public, organization, private

    # Basic metadata
    title = Column(String(500), nullable=False)
    authors = Column(JSON, nullable=False)  # Store as JSON for structured data
    abstract = Column(Text, nullable=False)
    categories = Column(JSON, nullable=False)  # arXiv categories
    published_date = Column(DateTime, nullable=False)
    pdf_url = Column(String(500), nullable=False)

    # Parsed PDF content (added for comprehensive storage)
    raw_text = Column(Text, nullable=True)
    sections = Column(JSON, nullable=True)  # Structured sections from PDF
    references = Column(JSON, nullable=True)  # Extracted references

    # PDF processing metadata
    parser_used = Column(String(50), nullable=True)  # e.g., 'docling', 'pypdf'
    parser_metadata = Column(JSON, nullable=True)  # Parser-specific metadata
    pdf_processed = Column(Boolean, default=False, nullable=False)
    pdf_processing_date = Column(DateTime, nullable=True)
    pdf_file_size = Column(String(50), nullable=True)  # Human-readable size
    pdf_page_count = Column(String(10), nullable=True)

    # Additional metadata
    tags = Column(JSON, nullable=True)  # User-defined tags
    keywords = Column(JSON, nullable=True)  # Extracted keywords
    journal_ref = Column(String(500), nullable=True)  # Journal reference if available
    comments = Column(Text, nullable=True)  # arXiv comments

    # Comprehensive metadata tracking
    license = Column(String(255), nullable=True)  # License information
    version = Column(String(50), nullable=True)  # Paper version
    submission_date = Column(DateTime, nullable=True)  # arXiv submission date
    update_date = Column(DateTime, nullable=True)  # Last update date
    citation_count = Column(Integer, default=0)  # Citation count
    view_count = Column(Integer, default=0)  # View count
    download_count = Column(Integer, default=0)  # Download count
    arxiv_version = Column(String(10), nullable=True)  # arXiv version (v1, v2, etc.)
    primary_category = Column(String(50), nullable=True)  # Primary arXiv category

    # Processing status and tracking
    ingestion_status = Column(String(50), default="pending", nullable=False)  # pending, processing, completed, failed
    ingestion_attempts = Column(String(10), default="0", nullable=False)
    last_ingestion_attempt = Column(DateTime, nullable=True)
    ingestion_errors = Column(JSON, nullable=True)  # Store error details

    # Audit and tracking
    created_at = Column(DateTime, default=lambda: datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    last_modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Enterprise features
    source = Column(String(100), default="arxiv", nullable=False)  # arxiv, manual, etc.
    quality_score = Column(String(10), nullable=True)  # Quality assessment score
    duplicate_of = Column(UUID(as_uuid=True), ForeignKey("research_papers.id"), nullable=True)  # For duplicate detection

    # Relationships
    organization = relationship("Organization", backref="papers")

    def can_access(self, user: "User") -> bool:
        """Check if a user can access this paper based on visibility and organization."""
        if self.visibility == 'public':
            return True
        if self.visibility == 'private':
            return False  # Private papers are not accessible via this method
        if self.visibility == 'organization':
            if not user or not user.organization_id:
                return False
            return self.organization_id == user.organization_id
        return False

    def is_public(self) -> bool:
        """Check if the paper is publicly accessible."""
        return self.visibility == 'public'

    def is_organization_accessible(self) -> bool:
        """Check if the paper is accessible within the organization."""
        return self.visibility in ['public', 'organization']

    def increment_view_count(self):
        """Increment the view count."""
        self.view_count = (self.view_count or 0) + 1

    def increment_download_count(self):
        """Increment the download count."""
        self.download_count = (self.download_count or 0) + 1

    def update_citation_count(self, count: int):
        """Update the citation count."""
        self.citation_count = count

    def __repr__(self):
        return f"<ResearchPaper(id={self.id}, arxiv_id={self.arxiv_id}, title={self.title[:50]}..., visibility={self.visibility})>"