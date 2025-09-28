"""
Data ingestion service for research papers
"""
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from ..config import Settings
from ..database import get_db
from ..repositories.paper import PaperRepository
from ..services.arxiv import ArxivClient
from ..services.pdf_parser import PDFParserFactory
from ..services.embeddings import EmbeddingService
from ..services.opensearch import OpenSearchService
from ..schemas.arxiv import ArxivSearchQuery, ArxivIngestionRequest, ArxivIngestionResponse
from ..schemas.paper import PaperCreate, PaperIngestionUpdate, IngestionStatus
from ..schemas.pdf_parser import PdfProcessingRequest, ParserType
from ..utils.exceptions import IngestionException, DatabaseException

logger = logging.getLogger(__name__)


class IngestionJob:
    """Represents an ingestion job with progress tracking."""

    def __init__(self, job_id: str, request: ArxivIngestionRequest):
        self.job_id = job_id
        self.request = request
        self.status = "pending"
        self.progress = {
            "papers_fetched": 0,
            "papers_created": 0,
            "papers_updated": 0,
            "pdfs_downloaded": 0,
            "pdfs_processed": 0,
            "errors": []
        }
        self.created_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "request": self.request.model_dump()
        }


class IngestionService:
    """Service for orchestrating research paper data ingestion."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._arxiv_client = ArxivClient(settings)
        self._pdf_parser_factory = PDFParserFactory(settings)
        self._embedding_service = EmbeddingService()
        self._active_jobs: Dict[str, IngestionJob] = {}
        self._job_queue: asyncio.Queue = asyncio.Queue()

    async def start_ingestion_job(self, request: ArxivIngestionRequest, user_id: UUID) -> ArxivIngestionResponse:
        """Start an arXiv ingestion job."""
        job_id = str(uuid4())
        job = IngestionJob(job_id, request)

        self._active_jobs[job_id] = job

        # Start background processing
        asyncio.create_task(self._process_ingestion_job(job, user_id))

        estimated_papers = min(request.max_papers or 1000, 1000)  # Rough estimate

        return ArxivIngestionResponse(
            job_id=job_id,
            status="started",
            message=f"Ingestion job started with ID: {job_id}",
            estimated_papers=estimated_papers,
            search_criteria=request.search_query.model_dump()
        )

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an ingestion job."""
        job = self._active_jobs.get(job_id)
        if job:
            return job.to_dict()
        return None

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel an active ingestion job."""
        job = self._active_jobs.get(job_id)
        if job and job.status in ["pending", "running"]:
            job.status = "cancelled"
            job.completed_at = datetime.now(timezone.utc)
            return True
        return False

    async def _process_ingestion_job(self, job: IngestionJob, user_id: UUID):
        """Process an ingestion job in the background."""
        try:
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)

            # Step 1: Fetch papers from arXiv
            papers_data = await self._fetch_arxiv_papers(job)

            # Step 2: Create/update papers in database
            created_papers, updated_papers = await self._store_papers(papers_data, user_id, job)

            # Step 3: Download and process PDFs if requested
            if job.request.process_pdfs:
                await self._process_pdfs(created_papers + updated_papers, job)

            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)

            logger.info(f"Ingestion job {job.job_id} completed successfully")

        except Exception as e:
            logger.error(f"Ingestion job {job.job_id} failed: {e}")
            job.status = "failed"
            job.progress["errors"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "stage": "general"
            })
            job.completed_at = datetime.now(timezone.utc)

    async def _fetch_arxiv_papers(self, job: IngestionJob) -> List[Dict[str, Any]]:
        """Fetch papers from arXiv API."""
        papers_data = []

        try:
            batch_size = job.request.batch_size
            max_papers = job.request.max_papers or 1000
            total_fetched = 0

            while total_fetched < max_papers:
                current_batch = min(batch_size, max_papers - total_fetched)

                # Update query with current pagination
                query = job.request.search_query.model_copy()
                query.start = total_fetched
                query.max_results = current_batch

                try:
                    batch_papers = await self._arxiv_client.fetch_papers(query)
                    papers_data.extend([paper.model_dump() for paper in batch_papers])
                    job.progress["papers_fetched"] += len(batch_papers)
                    total_fetched += len(batch_papers)

                    # Break if we got fewer papers than requested (end of results)
                    if len(batch_papers) < current_batch:
                        break

                except Exception as e:
                    logger.error(f"Failed to fetch batch starting at {total_fetched}: {e}")
                    job.progress["errors"].append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "error": str(e),
                        "stage": "arxiv_fetch",
                        "batch_start": total_fetched
                    })
                    break

        except Exception as e:
            logger.error(f"Failed to fetch papers from arXiv: {e}")
            job.progress["errors"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "stage": "arxiv_fetch"
            })

        return papers_data

    async def _store_papers(self, papers_data: List[Dict[str, Any]], user_id: UUID, job: IngestionJob) -> tuple:
        """Store papers in database with bulk operations."""
        created_papers = []
        updated_papers = []

        try:
            # Convert to PaperCreate objects
            paper_creates = []
            for paper_data in papers_data:
                try:
                    # Convert arXiv format to our PaperCreate format
                    paper_create = PaperCreate(
                        arxiv_id=paper_data["arxiv_id"],
                        title=paper_data["title"],
                        authors=paper_data["authors"],
                        abstract=paper_data["abstract"],
                        categories=paper_data["categories"],
                        published_date=datetime.fromisoformat(paper_data["published_date"]),
                        pdf_url=paper_data["pdf_url"],
                        doi=paper_data.get("doi"),
                        journal_ref=paper_data.get("journal_ref"),
                        comments=paper_data.get("comments"),
                        source="arxiv"
                    )
                    paper_creates.append(paper_create)
                except Exception as e:
                    logger.error(f"Failed to convert paper data {paper_data.get('arxiv_id')}: {e}")
                    continue

            # Bulk upsert papers
            async with async_session() as session:
                repo = PaperRepository(session)
                result = repo.bulk_upsert(paper_creates, user_id)

                job.progress["papers_created"] = result["created"]
                job.progress["papers_updated"] = result["updated"]

                # Get actual paper objects for PDF processing
                created_paper_objects = result["created_papers"]
                updated_paper_objects = result["updated_papers"]

                created_papers.extend(created_paper_objects)
                updated_papers.extend(updated_paper_objects)

        except Exception as e:
            logger.error(f"Failed to store papers: {e}")
            job.progress["errors"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "stage": "database_store"
            })

        return created_papers, updated_papers

    async def _process_pdfs(self, papers: List[Any], job: IngestionJob):
        """Download and process PDFs for papers."""
        try:
            parser = self._pdf_parser_factory.get_parser(ParserType.DOCLING)

            for paper in papers:
                try:
                    # Download PDF
                    pdf_path = await self._arxiv_client.download_pdf(paper)
                    if not pdf_path:
                        continue

                    job.progress["pdfs_downloaded"] += 1

                    # Process PDF
                    request = PdfProcessingRequest(
                        paper_id=str(paper.id),
                        pdf_path=str(pdf_path),
                        parser_type=ParserType.DOCLING
                    )

                    response = await parser.process_pdf(request)

                    # Update paper with processing results
                    async with get_db() as session:
                        repo = PaperRepository(session)

                        if response.success and response.content:
                            # Create ingestion update
                            ingestion_update = PaperIngestionUpdate(
                                raw_text=response.content.raw_text,
                                sections=response.content.sections,
                                references=response.content.references,
                                parser_used=response.content.parser_used,
                                parser_metadata=response.content.metadata,
                                pdf_processed=True,
                                pdf_processing_date=datetime.now(timezone.utc),
                                pdf_file_size=response.content.file_size_bytes,
                                pdf_page_count=response.content.page_count,
                                ingestion_status=IngestionStatus.COMPLETED
                            )
                        else:
                            # Mark as failed
                            ingestion_update = PaperIngestionUpdate(
                                pdf_processed=False,
                                ingestion_status=IngestionStatus.FAILED,
                                ingestion_errors=[{"error": response.error_message or "Unknown error"}]
                            )

                        repo.update_pdf_content(paper.id, ingestion_update)

                    job.progress["pdfs_processed"] += 1

                except Exception as e:
                    logger.error(f"Failed to process PDF for paper {paper.arxiv_id}: {e}")
                    job.progress["errors"].append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "error": str(e),
                        "stage": "pdf_processing",
                        "paper_id": str(paper.id)
                    })

        except Exception as e:
            logger.error(f"Failed to process PDFs: {e}")
            job.progress["errors"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "stage": "pdf_processing"
            })

    async def process_single_paper_pdf(self, paper_id: UUID) -> bool:
        """Process PDF for a single paper (for retry/manual processing)."""
        logger.info(f"Starting PDF processing for paper {paper_id}")
        try:
            async with get_db() as session:
                repo = PaperRepository(session)
                paper = await repo.get_by_id(paper_id)

                if not paper:
                    logger.warning(f"Paper {paper_id} not found for processing")
                    return False

                logger.info(f"Marking paper {paper_id} as processing")
                # Mark as processing
                await repo.update_ingestion_status(paper_id, "processing")

                logger.info(f"Downloading PDF for paper {paper_id}")
                # Download PDF
                pdf_path = await self._arxiv_client.download_pdf(paper)
                if not pdf_path:
                    logger.error(f"PDF download failed for paper {paper_id}")
                    await repo.update_ingestion_status(paper_id, "failed", error_details={"error": "PDF download failed"})
                    return False

                logger.info(f"Processing PDF content for paper {paper_id}")
                # Process PDF
                parser = self._pdf_parser_factory.get_parser(ParserType.DOCLING)
                request = PdfProcessingRequest(
                    paper_id=str(paper_id),
                    pdf_path=str(pdf_path),
                    parser_type=ParserType.DOCLING
                )

                response = await parser.process_pdf(request)
                logger.info(f"PDF processing completed for paper {paper_id}, success: {response.success}")

                # Update paper
                if response.success and response.content:
                    ingestion_update = PaperIngestionUpdate(
                        raw_text=response.content.raw_text,
                        sections=response.content.sections,
                        references=response.content.references,
                        parser_used=response.content.parser_used,
                        parser_metadata=response.content.metadata,
                        pdf_processed=True,
                        pdf_processing_date=datetime.now(timezone.utc),
                        pdf_file_size=response.content.file_size_bytes,
                        pdf_page_count=response.content.page_count,
                        ingestion_status=IngestionStatus.COMPLETED
                    )

                    logger.info(f"Generating embeddings and indexing for paper {paper_id}")
                    # Generate embeddings and index in OpenSearch
                    await self._generate_embeddings_and_index(paper, response.content.raw_text)
                    logger.info(f"Embeddings and indexing completed for paper {paper_id}")

                else:
                    logger.error(f"PDF processing failed for paper {paper_id}: {response.error_message}")
                    ingestion_update = PaperIngestionUpdate(
                        pdf_processed=False,
                        ingestion_status=IngestionStatus.FAILED,
                        ingestion_errors=[{"error": response.error_message or "Unknown error"}]
                    )

                await repo.update_pdf_content(paper_id, ingestion_update)
                logger.info(f"PDF processing finished for paper {paper_id}, success: {response.success}")
                return response.success

        except Exception as e:
            logger.error(f"Failed to process PDF for paper {paper_id}: {e}", exc_info=True)
            try:
                async with get_db() as session:
                    repo = PaperRepository(session)
                    await repo.update_ingestion_status(paper_id, "failed", error_details={"error": str(e)})
            except Exception as db_e:
                logger.error(f"Failed to update status after error for paper {paper_id}: {db_e}")
            return False

    async def _generate_embeddings_and_index(self, paper, raw_text: str):
        """Generate embeddings for paper content and index in OpenSearch"""
        logger.info(f"Starting embedding generation for paper {paper.id}")
        try:
            # Prepare paper data for embedding
            paper_data = {
                "paper_id": str(paper.id),
                "title": paper.title,
                "abstract": paper.abstract,
                "content": raw_text,
                "authors": paper.authors,
                "published_date": paper.published_date.isoformat() if paper.published_date else None,
                "categories": paper.categories,
                "doi": paper.doi,
                "source": paper.source or "manual",
                "file_path": paper.pdf_url,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            logger.info(f"Paper data prepared for embedding, content length: {len(raw_text) if raw_text else 0}")

            # Generate embeddings using configured provider (Gemini)
            logger.info(f"Generating embeddings for paper {paper.id}")
            await self._embedding_service.initialize()
            try:
                embedded_paper = await self._embedding_service.embed_paper(paper_data)
            finally:
                await self._embedding_service.cleanup()
            logger.info(f"Embeddings generated successfully for paper {paper.id}")

            # Index in OpenSearch
            logger.info(f"Connecting to OpenSearch for paper {paper.id}")
            opensearch_service = OpenSearchService()
            await opensearch_service.connect()
            logger.info(f"Connected to OpenSearch, creating index if needed")

            # Create index if it doesn't exist
            opensearch_service.create_index()
            logger.info(f"Index ready, preparing document for paper {paper.id}")

            # Prepare document for indexing
            doc = {
                "paper_id": embedded_paper["paper_id"],
                "title": embedded_paper["title"],
                "abstract": embedded_paper["abstract"],
                "content": embedded_paper["content"],
                "authors": embedded_paper["authors"],
                "published_date": embedded_paper["published_date"],
                "categories": embedded_paper["categories"],
                "doi": embedded_paper["doi"],
                "source": embedded_paper["source"],
                "file_path": embedded_paper["file_path"],
                "processed_at": embedded_paper["processed_at"],
                "embedding": embedded_paper["embedding"],
                "word_count": len(raw_text.split()) if raw_text else 0,
                "page_count": paper.pdf_page_count or 0,
                "view_count": paper.view_count or 0,
                "download_count": 0,
                "last_accessed": datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Indexing document for paper {paper.id}")
            # Index the document
            opensearch_service.index_document(str(paper.id), doc)
            opensearch_service.refresh_index()
            logger.info(f"Successfully generated embeddings and indexed paper {paper.id} in OpenSearch")

        except Exception as e:
            logger.error(f"Failed to generate embeddings and index paper {paper.id}: {e}", exc_info=True)
            # Don't fail the entire process if indexing fails, just log the error
            # The paper content is still processed and stored in DB

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get all active ingestion jobs."""
        return [job.to_dict() for job in self._active_jobs.values()]

    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up old completed/failed jobs."""
        cutoff_time = datetime.now(timezone.utc)
        # This would be implemented with actual cleanup logic
        pass