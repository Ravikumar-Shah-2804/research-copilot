"""
Research papers router
"""
import logging
import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from ..config import settings
from ..database import get_db
from ..models.user import User
from ..services.auth import get_current_active_user
from ..schemas.paper import PaperCreate, PaperResponse, PaperUpdate
from ..repositories.paper import PaperRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=PaperResponse)
async def create_paper(
    paper: PaperCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new research paper"""
    logger.info(f"Creating paper: {paper.title} by user: {current_user.id}")
    repo = PaperRepository(db)
    try:
        # Set organization_id from user if not provided
        if paper.organization_id is None:
            paper.organization_id = current_user.organization_id

        db_paper = await repo.create(paper, current_user.id)
        logger.info(f"Paper created successfully: {db_paper.id}")
        return db_paper
    except Exception as e:
        logger.error(f"Failed to create paper: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to create paper: {str(e)}")


@router.get("/", response_model=List[PaperResponse])
async def list_papers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List research papers accessible to the user"""
    logger.info(f"Listing papers for user: {current_user.id}, organization: {current_user.organization_id}, skip: {skip}, limit: {limit}, search: {search}")
    repo = PaperRepository(db)
    try:
        if search:
            papers = await repo.search_similar_papers(search, limit)
        else:
            papers = await repo.get_accessible_papers_for_user(
                user_id=current_user.id,
                organization_id=current_user.organization_id,
                limit=limit,
                offset=skip
            )
        logger.info(f"Retrieved {len(papers)} papers")
        return papers
    except Exception as e:
        logger.error(f"Failed to list papers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list papers: {str(e)}")


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific research paper if accessible"""
    logger.info(f"Getting paper: {paper_id} for user: {current_user.id}")
    repo = PaperRepository(db)
    try:
        logger.info(f"Checking access for paper {paper_id}")
        # Check access first
        if not await repo.check_paper_access(paper_id, current_user.id, current_user.organization_id):
            logger.warning(f"Access denied for paper {paper_id} by user {current_user.id}")
            raise HTTPException(status_code=403, detail="Access denied to this paper")

        logger.info(f"Access granted, fetching paper {paper_id} from database")
        paper = await repo.get_by_id(paper_id)
        if not paper:
            logger.warning(f"Paper {paper_id} not found")
            raise HTTPException(status_code=404, detail="Paper not found")

        logger.info(f"Paper found, pdf_processed: {paper.pdf_processed}, incrementing view count")
        # Increment view count
        await repo.increment_view_count(paper_id)

        logger.info(f"Successfully retrieved paper: {paper.id}")
        return paper
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get paper {paper_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get paper: {str(e)}")


@router.put("/{paper_id}", response_model=PaperResponse)
async def update_paper(
    paper_id: UUID,
    paper_update: PaperUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a research paper if accessible"""
    logger.info(f"Updating paper: {paper_id} for user: {current_user.id}")
    repo = PaperRepository(db)
    try:
        # Check access first
        if not await repo.check_paper_access(paper_id, current_user.id, current_user.organization_id):
            raise HTTPException(status_code=403, detail="Access denied to this paper")

        updated_paper = await repo.update_paper(paper_id, paper_update, current_user.id)
        if not updated_paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        logger.info(f"Updated paper: {paper_id}")
        return updated_paper
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update paper: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update paper: {str(e)}")


@router.delete("/{paper_id}")
async def delete_paper(
    paper_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a research paper if accessible"""
    logger.info(f"Deleting paper: {paper_id} for user: {current_user.id}")
    repo = PaperRepository(db)
    try:
        # Check access first
        if not await repo.check_paper_access(paper_id, current_user.id, current_user.organization_id):
            raise HTTPException(status_code=403, detail="Access denied to this paper")

        success = await repo.delete(paper_id)
        if not success:
            raise HTTPException(status_code=404, detail="Paper not found")
        logger.info(f"Deleted paper: {paper_id}")
        return {"message": "Paper deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete paper: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete paper: {str(e)}")


@router.post("/{paper_id}/upload")
async def upload_paper_pdf(
    paper_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload PDF for a research paper"""
    logger.info(f"Uploading PDF for paper: {paper_id} by user: {current_user.id}")
    repo = PaperRepository(db)
    try:
        # Check access first
        if not await repo.check_paper_access(paper_id, current_user.id, current_user.organization_id):
            raise HTTPException(status_code=403, detail="Access denied to this paper")

        # Validate file
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        if file.size > settings.max_upload_size:
            raise HTTPException(status_code=400, detail=f"File size exceeds maximum allowed size of {settings.max_upload_size} bytes")

        # Ensure directory exists
        os.makedirs(settings.pdf_cache_dir, exist_ok=True)

        # Save file
        file_path = os.path.join(settings.pdf_cache_dir, f"{paper_id}.pdf")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Update paper
        paper = await repo.get_by_id(paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        paper.pdf_url = file_path
        paper.pdf_processed = False
        paper.pdf_processing_date = None
        paper.pdf_file_size = str(file.size)
        await repo.update(paper)

        # Trigger background processing for content extraction and embedding generation
        from ..services.ingestion import IngestionService
        ingestion_service = IngestionService(settings)
        background_tasks.add_task(ingestion_service.process_single_paper_pdf, paper_id)

        logger.info(f"PDF uploaded successfully for paper: {paper_id}, processing started in background")
        return {"message": "PDF uploaded successfully, processing started"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload PDF for paper {paper_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload PDF: {str(e)}")