"""
API routers for Research Copilot
"""
from fastapi import APIRouter

from .ping import router as ping_router
from .auth import router as auth_router
from .papers import router as papers_router
from .search import router as search_router
from .rag import router as rag_router
from .analytics import router as analytics_router
from .admin import router as admin_router
from .ingestion import router as ingestion_router
from .roles import router as roles_router
from .organizations import router as organizations_router
from .audit import router as audit_router
from .health import router as health_router
from .api_keys import router as api_keys_router

# Main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(ping_router, tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(papers_router, prefix="/papers", tags=["Research Papers"])
api_router.include_router(search_router, prefix="/search", tags=["Search"])
api_router.include_router(rag_router, prefix="/rag", tags=["RAG"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(ingestion_router, prefix="/ingestion", tags=["Data Ingestion"])
api_router.include_router(admin_router, prefix="/admin", tags=["Administration"])
api_router.include_router(roles_router, prefix="/roles", tags=["Roles & Permissions"])
api_router.include_router(organizations_router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(audit_router, prefix="/audit", tags=["Audit Logs"])
api_router.include_router(health_router, prefix="/health", tags=["Health Checks"])
api_router.include_router(api_keys_router, prefix="/api-keys", tags=["API Keys"])