"""
Paper repository with comprehensive CRUD operations and bulk insertion
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import func, select, update, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from ..models.paper import ResearchPaper
from ..schemas.paper import PaperCreate, PaperUpdate, PaperIngestionUpdate, PaperIngestionStats
from ..utils.exceptions import DatabaseException

import logging
logger = logging.getLogger(__name__)


class PaperRepository:
    """Repository for research paper operations with enterprise features."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, paper: PaperCreate, created_by: UUID) -> ResearchPaper:
        """Create a new research paper."""
        db_paper = ResearchPaper(
            **paper.model_dump(),
            created_by=created_by,
            ingestion_status="pending"
        )
        self.session.add(db_paper)
        try:
            await self.session.commit()
            await self.session.refresh(db_paper)
            return db_paper
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Integrity error creating paper {paper.arxiv_id}: {e}")
            raise DatabaseException(f"Paper with arXiv ID {paper.arxiv_id} already exists")

    async def get_by_arxiv_id(self, arxiv_id: str) -> Optional[ResearchPaper]:
        """Get paper by arXiv ID."""
        stmt = select(ResearchPaper).where(ResearchPaper.arxiv_id == arxiv_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, paper_id: UUID) -> Optional[ResearchPaper]:
        """Get paper by ID."""
        stmt = select(ResearchPaper).where(ResearchPaper.id == paper_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_doi(self, doi: str) -> Optional[ResearchPaper]:
        """Get paper by DOI."""
        stmt = select(ResearchPaper).where(ResearchPaper.doi == doi)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        ingestion_status: Optional[str] = None,
        category: Optional[str] = None,
        has_pdf_content: bool = False,
        organization_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None
    ) -> List[ResearchPaper]:
        """Get papers with optional filtering, including organization-based access control."""
        conditions = []

        if ingestion_status:
            conditions.append(ResearchPaper.ingestion_status == ingestion_status)

        if category:
            # Check if category is in the JSON array
            conditions.append(
                text("categories::jsonb ? :category").bindparams(category=category)
            )

        if has_pdf_content:
            conditions.append(ResearchPaper.raw_text.isnot(None))

        # Organization-based access control
        if organization_id:
            conditions.append(
                or_(
                    ResearchPaper.visibility == 'public',
                    and_(ResearchPaper.visibility == 'organization', ResearchPaper.organization_id == organization_id)
                )
            )
        else:
            # If no organization specified, only show public papers
            conditions.append(ResearchPaper.visibility == 'public')

        stmt = select(ResearchPaper).where(and_(*conditions)) \
            .order_by(ResearchPaper.published_date.desc()) \
            .limit(limit).offset(offset)

        return list((await self.session.execute(stmt)).scalars())

    async def get_count(self, **filters) -> int:
        """Get total count of papers with optional filters."""
        conditions = []
        for key, value in filters.items():
            if hasattr(ResearchPaper, key):
                conditions.append(getattr(ResearchPaper, key) == value)

        stmt = select(func.count(ResearchPaper.id)).where(and_(*conditions))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def update(self, paper: ResearchPaper) -> ResearchPaper:
        """Update an existing paper."""
        paper.updated_at = datetime.now()
        self.session.add(paper)
        await self.session.commit()
        await self.session.refresh(paper)
        return paper

    async def update_paper(self, paper_id: UUID, update_data: PaperUpdate, updated_by: Optional[UUID] = None) -> Optional[ResearchPaper]:
        """Update paper with partial data."""
        paper = await self.get_by_id(paper_id)
        if not paper:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(paper, key, value)

        if updated_by:
            paper.last_modified_by = updated_by

        return await self.update(paper)

    async def update_ingestion_status(
        self,
        paper_id: UUID,
        status: str,
        attempts: Optional[int] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> Optional[ResearchPaper]:
        """Update paper ingestion status."""
        paper = await self.get_by_id(paper_id)
        if not paper:
            return None

        paper.ingestion_status = status
        paper.last_ingestion_attempt = datetime.now()

        if attempts is not None:
            paper.ingestion_attempts = str(attempts)

        if error_details:
            current_errors = paper.ingestion_errors or []
            current_errors.append({
                "timestamp": datetime.now().isoformat(),
                "error": error_details
            })
            paper.ingestion_errors = current_errors

        return await self.update(paper)

    async def update_pdf_content(self, paper_id: UUID, pdf_update: PaperIngestionUpdate) -> Optional[ResearchPaper]:
        """Update paper with PDF processing results."""
        paper = await self.get_by_id(paper_id)
        if not paper:
            return None

        # Update PDF processing fields
        if pdf_update.raw_text is not None:
            paper.raw_text = pdf_update.raw_text
        if pdf_update.sections is not None:
            paper.sections = [section.model_dump() for section in pdf_update.sections]
        if pdf_update.references is not None:
            paper.references = [ref.model_dump() for ref in pdf_update.references]
        if pdf_update.parser_used:
            paper.parser_used = pdf_update.parser_used.value
        if pdf_update.parser_metadata:
            paper.parser_metadata = pdf_update.parser_metadata
        if pdf_update.pdf_file_size:
            paper.pdf_file_size = pdf_update.pdf_file_size
        if pdf_update.pdf_page_count:
            paper.pdf_page_count = str(pdf_update.pdf_page_count)

        paper.pdf_processed = pdf_update.pdf_processed
        paper.pdf_processing_date = pdf_update.pdf_processing_date or datetime.now()
        paper.ingestion_status = pdf_update.ingestion_status.value

        if pdf_update.ingestion_attempts is not None:
            paper.ingestion_attempts = str(pdf_update.ingestion_attempts)
        if pdf_update.ingestion_errors:
            paper.ingestion_errors = pdf_update.ingestion_errors

        return await self.update(paper)

    async def bulk_create(self, papers: List[PaperCreate], created_by: UUID) -> List[ResearchPaper]:
        """Bulk create papers with error handling."""
        created_papers = []
        errors = []

        for paper_data in papers:
            try:
                paper = await self.create(paper_data, created_by)
                created_papers.append(paper)
            except Exception as e:
                logger.error(f"Failed to create paper {paper_data.arxiv_id}: {e}")
                errors.append({"arxiv_id": paper_data.arxiv_id, "error": str(e)})

        if errors:
            logger.warning(f"Bulk create completed with {len(errors)} errors: {errors}")

        return created_papers

    async def bulk_upsert(self, papers: List[PaperCreate], created_by: UUID) -> Dict[str, Any]:
        """Bulk upsert papers (create or update existing)."""
        created = []
        updated = []
        errors = []

        for paper_data in papers:
            try:
                existing = await self.get_by_arxiv_id(paper_data.arxiv_id)
                if existing:
                    # Update existing paper
                    for key, value in paper_data.model_dump(exclude_unset=True).items():
                        setattr(existing, key, value)
                    existing.last_modified_by = created_by
                    await self.update(existing)
                    updated.append(existing)
                else:
                    # Create new paper
                    paper = await self.create(paper_data, created_by)
                    created.append(paper)
            except Exception as e:
                logger.error(f"Failed to upsert paper {paper_data.arxiv_id}: {e}")
                errors.append({"arxiv_id": paper_data.arxiv_id, "error": str(e)})

        return {
            "created": len(created),
            "updated": len(updated),
            "errors": len(errors),
            "created_papers": created,
            "updated_papers": updated,
            "error_details": errors
        }

    async def get_unprocessed_papers(self, limit: int = 100, offset: int = 0) -> List[ResearchPaper]:
        """Get papers that haven't been processed for PDF content yet."""
        stmt = select(ResearchPaper) \
            .where(ResearchPaper.pdf_processed == False) \
            .where(ResearchPaper.ingestion_status.in_(["pending", "failed"])) \
            .order_by(ResearchPaper.published_date.desc()) \
            .limit(limit).offset(offset)
        return list((await self.session.execute(stmt)).scalars())

    async def get_failed_ingestions(self, limit: int = 100, offset: int = 0) -> List[ResearchPaper]:
        """Get papers with failed ingestion."""
        stmt = select(ResearchPaper) \
            .where(ResearchPaper.ingestion_status == "failed") \
            .order_by(ResearchPaper.last_ingestion_attempt.desc()) \
            .limit(limit).offset(offset)
        return list((await self.session.execute(stmt)).scalars())

    async def get_processing_papers(self, limit: int = 100, offset: int = 0) -> List[ResearchPaper]:
        """Get papers currently being processed."""
        stmt = select(ResearchPaper) \
            .where(ResearchPaper.ingestion_status == "processing") \
            .order_by(ResearchPaper.last_ingestion_attempt.desc()) \
            .limit(limit).offset(offset)
        return list((await self.session.execute(stmt)).scalars())

    async def get_duplicate_candidates(self, arxiv_id: str, title: str, authors: List[str]) -> List[ResearchPaper]:
        """Find potential duplicate papers based on arXiv ID, title similarity, and authors."""
        # This is a basic implementation - could be enhanced with ML similarity
        conditions = [
            ResearchPaper.arxiv_id != arxiv_id,  # Exclude the paper itself
            or_(
                func.lower(ResearchPaper.title).contains(title.lower()),
                ResearchPaper.doi.isnot(None)  # Could add DOI matching
            )
        ]

        stmt = select(ResearchPaper).where(and_(*conditions)).limit(10)
        return list((await self.session.execute(stmt)).scalars())

    async def get_ingestion_stats(self) -> PaperIngestionStats:
        """Get comprehensive ingestion statistics."""
        total_papers = await self.get_count()

        # Count by status
        status_counts = {}
        for status in ["pending", "processing", "completed", "failed"]:
            status_counts[status] = await self.get_count(ingestion_status=status)

        # Count processed papers
        processed_stmt = select(func.count(ResearchPaper.id)).where(ResearchPaper.pdf_processed == True)
        processed_result = await self.session.execute(processed_stmt)
        processed_papers = processed_result.scalar() or 0

        # Count papers with text
        text_stmt = select(func.count(ResearchPaper.id)).where(ResearchPaper.raw_text.isnot(None))
        text_result = await self.session.execute(text_stmt)
        papers_with_text = text_result.scalar() or 0

        # Calculate rates
        processing_rate = (status_counts["completed"] / total_papers * 100) if total_papers > 0 else 0
        text_extraction_rate = (papers_with_text / processed_papers * 100) if processed_papers > 0 else 0

        # Get last ingestion run (most recent paper creation/update)
        last_ingestion_stmt = select(func.max(ResearchPaper.created_at))
        last_result = await self.session.execute(last_ingestion_stmt)
        last_ingestion_run = last_result.scalar()

        return PaperIngestionStats(
            total_papers=total_papers,
            processed_papers=processed_papers,
            papers_with_text=papers_with_text,
            failed_ingestions=status_counts["failed"],
            processing_rate=processing_rate,
            text_extraction_rate=text_extraction_rate,
            last_ingestion_run=last_ingestion_run
        )

    async def delete(self, paper_id: UUID) -> bool:
        """Delete a paper by ID."""
        paper = await self.get_by_id(paper_id)
        if not paper:
            return False

        self.session.delete(paper)
        await self.session.commit()
        return True

    async def search_similar_papers(self, query: str, limit: int = 10) -> List[ResearchPaper]:
        """Search for papers with similar titles or content."""
        # Basic text search - could be enhanced with full-text search
        conditions = [
            or_(
                func.lower(ResearchPaper.title).contains(query.lower()),
                func.lower(ResearchPaper.abstract).contains(query.lower()),
                func.lower(ResearchPaper.raw_text).contains(query.lower())
            )
        ]

        stmt = select(ResearchPaper) \
            .where(and_(*conditions)) \
            .order_by(ResearchPaper.published_date.desc()) \
            .limit(limit)

        return list((await self.session.execute(stmt)).scalars())

    async def get_papers_for_organization(self, organization_id: UUID, limit: int = 100, offset: int = 0) -> List[ResearchPaper]:
        """Get papers accessible to an organization (public + organization papers)."""
        conditions = [
            or_(
                ResearchPaper.visibility == 'public',
                and_(ResearchPaper.visibility == 'organization', ResearchPaper.organization_id == organization_id)
            )
        ]

        stmt = select(ResearchPaper) \
            .where(and_(*conditions)) \
            .order_by(ResearchPaper.published_date.desc()) \
            .limit(limit).offset(offset)

        return list((await self.session.execute(stmt)).scalars())

    async def get_accessible_papers_for_user(self, user_id: UUID, organization_id: Optional[UUID] = None,
                                        limit: int = 100, offset: int = 0) -> List[ResearchPaper]:
        """Get papers accessible to a specific user based on their organization and permissions."""
        # For now, assume organization access. Could be enhanced with role-based permissions
        if not organization_id:
            # If no organization, only public papers
            conditions = [ResearchPaper.visibility == 'public']
        else:
            conditions = [
                or_(
                    ResearchPaper.visibility == 'public',
                    and_(ResearchPaper.visibility == 'organization', ResearchPaper.organization_id == organization_id)
                )
            ]

        stmt = select(ResearchPaper) \
            .where(and_(*conditions)) \
            .order_by(ResearchPaper.published_date.desc()) \
            .limit(limit).offset(offset)

        return list((await self.session.execute(stmt)).scalars())

    async def check_paper_access(self, paper_id: UUID, user_id: Optional[UUID] = None,
                           organization_id: Optional[UUID] = None) -> bool:
        """Check if a user/organization can access a specific paper."""
        paper = await self.get_by_id(paper_id)
        if not paper:
            return False

        if paper.visibility == 'public':
            return True
        if paper.visibility == 'private':
            return False  # Private papers require specific permission checks
        if paper.visibility == 'organization':
            return organization_id is not None and paper.organization_id == organization_id

        return False

    async def increment_view_count(self, paper_id: UUID) -> bool:
        """Increment view count for a paper."""
        paper = await self.get_by_id(paper_id)
        if not paper:
            return False

        paper.increment_view_count()
        await self.update(paper)
        return True

    async def increment_download_count(self, paper_id: UUID) -> bool:
        """Increment download count for a paper."""
        paper = await self.get_by_id(paper_id)
        if not paper:
            return False

        paper.increment_download_count()
        await self.update(paper)
        return True

    async def update_citation_count(self, paper_id: UUID, count: int) -> bool:
        """Update citation count for a paper."""
        paper = await self.get_by_id(paper_id)
        if not paper:
            return False

        paper.update_citation_count(count)
        await self.update(paper)
        return True

    async def get_popular_papers(self, organization_id: Optional[UUID] = None, limit: int = 10) -> List[ResearchPaper]:
        """Get most viewed papers, optionally filtered by organization."""
        conditions = []
        if organization_id:
            conditions.append(
                or_(
                    ResearchPaper.visibility == 'public',
                    and_(ResearchPaper.visibility == 'organization', ResearchPaper.organization_id == organization_id)
                )
            )
        else:
            conditions.append(ResearchPaper.visibility == 'public')

        stmt = select(ResearchPaper) \
            .where(and_(*conditions)) \
            .order_by(ResearchPaper.view_count.desc()) \
            .limit(limit)

        return list((await self.session.execute(stmt)).scalars())

    async def get_recently_updated_papers(self, organization_id: Optional[UUID] = None, limit: int = 10) -> List[ResearchPaper]:
        """Get recently updated papers, optionally filtered by organization."""
        conditions = []
        if organization_id:
            conditions.append(
                or_(
                    ResearchPaper.visibility == 'public',
                    and_(ResearchPaper.visibility == 'organization', ResearchPaper.organization_id == organization_id)
                )
            )
        else:
            conditions.append(ResearchPaper.visibility == 'public')

        stmt = select(ResearchPaper) \
            .where(and_(*conditions)) \
            .order_by(ResearchPaper.update_date.desc()) \
            .limit(limit)

        return list((await self.session.execute(stmt)).scalars())