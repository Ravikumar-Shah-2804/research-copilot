"""
Ingestion API endpoints for research paper data ingestion
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..config import Settings
from ..database import get_db
from ..services.auth import get_current_user
from ..config import settings


def get_settings() -> Settings:
    """Dependency to get settings"""
    return settings
from ..models.user import User
from ..repositories.paper import PaperRepository
from ..services.ingestion import IngestionService
from ..schemas.arxiv import ArxivIngestionRequest, ArxivIngestionResponse, ArxivIngestionStatus
from ..schemas.paper import PaperIngestionStats, PaperResponse

router = APIRouter(tags=["ingestion"])
logger = logging.getLogger(__name__)


@router.post("/arxiv", response_model=ArxivIngestionResponse)
async def start_arxiv_ingestion(
    request: ArxivIngestionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings)
):
    """
    Start an arXiv data ingestion job.

    This endpoint initiates a background job to fetch research papers from arXiv
    based on the provided search criteria and process them for inclusion in the system.
    """
    try:
        ingestion_service = IngestionService(settings)
        response = await ingestion_service.start_ingestion_job(request, current_user.id)

        # Add background task for monitoring (optional)
        background_tasks.add_task(log_ingestion_start, request, current_user.id)

        return response

    except Exception as e:
        logger.error(f"Failed to start arXiv ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start ingestion: {str(e)}")


@router.get("/job/{job_id}", response_model=ArxivIngestionStatus)
async def get_ingestion_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings)
):
    """Get the status of an ingestion job."""
    try:
        ingestion_service = IngestionService(settings)
        job_status = await ingestion_service.get_job_status(job_id)

        if not job_status:
            raise HTTPException(status_code=404, detail="Job not found")

        return ArxivIngestionStatus(**job_status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.delete("/job/{job_id}")
async def cancel_ingestion_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings)
):
    """Cancel an active ingestion job."""
    try:
        ingestion_service = IngestionService(settings)
        cancelled = await ingestion_service.cancel_job(job_id)

        if not cancelled:
            raise HTTPException(status_code=400, detail="Job could not be cancelled")

        return {"message": f"Job {job_id} cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@router.get("/jobs", response_model=List[ArxivIngestionStatus])
async def list_active_ingestion_jobs(
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings)
):
    """List all active ingestion jobs."""
    try:
        ingestion_service = IngestionService(settings)
        jobs = ingestion_service.get_active_jobs()
        return [ArxivIngestionStatus(**job) for job in jobs]

    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")


@router.post("/paper/{paper_id}/process-pdf")
async def process_single_paper_pdf(
    paper_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db)
):
    """Process PDF for a single paper (retry/manual processing)."""
    try:
        # Check if paper exists and user has access
        repo = PaperRepository(db)
        paper = repo.get_by_id(paper_id)

        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        # Check if user created the paper or is admin
        if paper.created_by != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to process this paper")

        ingestion_service = IngestionService(settings)

        # Start background processing
        background_tasks.add_task(ingestion_service.process_single_paper_pdf, paper_id)

        return {"message": f"PDF processing started for paper {paper_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start PDF processing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start PDF processing: {str(e)}")


@router.get("/stats", response_model=PaperIngestionStats)
async def get_ingestion_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive ingestion statistics."""
    try:
        repo = PaperRepository(db)
        stats = repo.get_ingestion_stats()
        return stats

    except Exception as e:
        logger.error(f"Failed to get ingestion stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get ingestion stats: {str(e)}")


@router.get("/papers/unprocessed", response_model=List[PaperResponse])
async def get_unprocessed_papers(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get papers that haven't been processed yet."""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")

        repo = PaperRepository(db)
        papers = repo.get_unprocessed_papers(limit=limit, offset=offset)

        return [PaperResponse.model_validate(paper) for paper in papers]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get unprocessed papers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get unprocessed papers: {str(e)}")


@router.get("/papers/failed", response_model=List[PaperResponse])
async def get_failed_ingestions(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get papers with failed ingestion."""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")

        repo = PaperRepository(db)
        papers = repo.get_failed_ingestions(limit=limit, offset=offset)

        return [PaperResponse.model_validate(paper) for paper in papers]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get failed ingestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get failed ingestions: {str(e)}")


@router.post("/retry-failed/{paper_id}")
async def retry_failed_ingestion(
    paper_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db)
):
    """Retry ingestion for a failed paper."""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")

        repo = PaperRepository(db)
        paper = repo.get_by_id(paper_id)

        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        if paper.ingestion_status != "failed":
            raise HTTPException(status_code=400, detail="Paper is not in failed state")

        # Reset ingestion status
        repo.update_ingestion_status(paper_id, "pending")

        # Start background processing
        ingestion_service = IngestionService(settings)
        background_tasks.add_task(ingestion_service.process_single_paper_pdf, paper_id)

        return {"message": f"Retry started for paper {paper_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retry ingestion: {str(e)}")


async def log_ingestion_start(request: ArxivIngestionRequest, user_id: UUID):
    """Log ingestion job start (for audit purposes)."""
    logger.info(f"Ingestion job started by user {user_id}: {request.model_dump()}")