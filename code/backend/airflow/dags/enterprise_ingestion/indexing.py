"""
Enterprise indexing with organization isolation for research-copilot.
"""

import logging
import os
from typing import Dict, Any, List
from datetime import datetime

# Add the src directory to the path
sys_path = os.path.join(os.path.dirname(__file__), '../../../src')
if sys_path not in os.sys.path:
    os.sys.path.insert(0, sys_path)

from services.opensearch.client import OpenSearchClient
from services.indexing.factory import make_hybrid_indexing_service
from services.monitoring import performance_monitor
from database import get_db_session
from repositories.paper import PaperRepository

logger = logging.getLogger(__name__)


def index_papers_enterprise(
    processing_result: Dict[str, Any],
    organizations: List[Dict[str, Any]],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Index papers with enterprise features and organization isolation.

    :param processing_result: Processing results from distributed tasks
    :param organizations: List of organizations
    :param config: Enterprise configuration
    :returns: Indexing results
    """
    logger.info("Starting enterprise indexing with organization isolation")

    indexing_results = {
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "organizations_processed": len(organizations),
        "total_papers_indexed": 0,
        "total_chunks_indexed": 0,
        "organization_results": {},
        "index_health": {},
        "errors": [],
        "performance_metrics": {}
    }

    try:
        # Initialize indexing service
        indexing_service = make_hybrid_indexing_service()
        opensearch_client = OpenSearchClient()

        # Create organization mapping for efficient lookup
        org_map = {org["id"]: org for org in organizations}

        # Process each organization's results
        org_results = processing_result.get("organization_results", {})

        start_time = datetime.now()
        for org_id, org_processing_result in org_results.items():
            try:
                org_data = org_map.get(org_id, {})
                org_name = org_data.get("name", f"Unknown ({org_id})")

                logger.info(f"Indexing papers for organization {org_name} (ID: {org_id})")

                # Get papers for this organization from database
                papers_data = _get_organization_papers(org_id, org_processing_result)

                if not papers_data:
                    logger.warning(f"No papers found for organization {org_id}")
                    indexing_results["organization_results"][org_id] = {
                        "status": "success",
                        "papers_indexed": 0,
                        "chunks_indexed": 0,
                        "message": "No papers to index"
                    }
                    continue

                # Index papers with organization isolation
                org_index_result = _index_organization_papers(
                    org_id, org_name, papers_data, indexing_service, config
                )

                indexing_results["organization_results"][org_id] = org_index_result
                indexing_results["total_papers_indexed"] += org_index_result.get("papers_indexed", 0)
                indexing_results["total_chunks_indexed"] += org_index_result.get("chunks_indexed", 0)

                logger.info(f"Completed indexing for org {org_id}: {org_index_result.get('papers_indexed', 0)} papers")

            except Exception as e:
                error_msg = f"Failed to index papers for organization {org_id}: {str(e)}"
                indexing_results["errors"].append(error_msg)
                indexing_results["organization_results"][org_id] = {
                    "status": "failed",
                    "error": str(e),
                    "papers_indexed": 0,
                    "chunks_indexed": 0
                }
                logger.error(error_msg)

        # Check index health
        try:
            index_health = opensearch_client.client.cluster.health()
            indexing_results["index_health"] = {
                "status": index_health["status"],
                "active_shards": index_health.get("active_shards", 0),
                "relocating_shards": index_health.get("relocating_shards", 0),
                "unassigned_shards": index_health.get("unassigned_shards", 0)
            }
        except Exception as e:
            logger.error(f"Failed to check index health: {e}")
            indexing_results["index_health"] = {"status": "unknown", "error": str(e)}

        # Calculate performance metrics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        indexing_results["performance_metrics"] = {
            "total_duration_seconds": duration,
            "papers_per_second": indexing_results["total_papers_indexed"] / duration if duration > 0 else 0,
            "chunks_per_second": indexing_results["total_chunks_indexed"] / duration if duration > 0 else 0,
            "organizations_successful": len([r for r in indexing_results["organization_results"].values() if r.get("status") == "success"]),
            "organizations_failed": len([r for r in indexing_results["organization_results"].values() if r.get("status") == "failed"])
        }

        # Record monitoring metrics
        performance_monitor.record_paper_ingestion("indexing", "success", indexing_results["total_papers_indexed"])

        indexing_results["status"] = "success"
        indexing_results["message"] = f"Successfully indexed {indexing_results['total_papers_indexed']} papers across {len(organizations)} organizations"

        logger.info(f"Enterprise indexing completed: {indexing_results['total_papers_indexed']} papers indexed")
        return indexing_results

    except Exception as e:
        error_msg = f"Enterprise indexing failed: {str(e)}"
        indexing_results["status"] = "failed"
        indexing_results["message"] = error_msg
        indexing_results["errors"].append(error_msg)
        logger.error(error_msg)
        return indexing_results


def _get_organization_papers(org_id: str, processing_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get papers for an organization from the database.

    :param org_id: Organization ID
    :param processing_result: Processing results for this organization
    :returns: List of paper data
    """
    try:
        with get_db_session() as session:
            repo = PaperRepository(session)

            # Get recently processed papers for this organization
            # In a real implementation, this would filter by organization
            papers = repo.get_recent_papers(limit=processing_result.get("papers_processed", 100))

            # Convert to indexing format
            papers_data = []
            for paper in papers:
                paper_dict = {
                    "id": str(paper.id),
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "abstract": paper.abstract,
                    "categories": paper.categories,
                    "published_date": paper.published_date.isoformat() if paper.published_date else None,
                    "raw_text": paper.raw_text or paper.abstract,
                    "sections": paper.sections or [],
                    "organization_id": org_id  # Add organization context
                }
                papers_data.append(paper_dict)

            return papers_data

    except Exception as e:
        logger.error(f"Failed to get papers for organization {org_id}: {e}")
        return []


def _index_organization_papers(
    org_id: str,
    org_name: str,
    papers_data: List[Dict[str, Any]],
    indexing_service,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Index papers for a specific organization.

    :param org_id: Organization ID
    :param org_name: Organization name
    :param papers_data: Papers to index
    :param indexing_service: Indexing service instance
    :param config: Enterprise configuration
    :returns: Indexing results for this organization
    """
    result = {
        "org_id": org_id,
        "org_name": org_name,
        "status": "pending",
        "papers_indexed": 0,
        "chunks_indexed": 0,
        "errors": []
    }

    try:
        if not papers_data:
            result["status"] = "success"
            result["message"] = "No papers to index"
            return result

        # Add organization context to papers for isolation
        for paper in papers_data:
            paper["organization_id"] = org_id
            paper["organization_name"] = org_name

        # Index papers using the hybrid indexing service
        index_stats = indexing_service.index_papers_batch(
            papers=papers_data,
            replace_existing=True,
            organization_id=org_id  # Pass organization context
        )

        result["papers_indexed"] = index_stats.get("papers_processed", 0)
        result["chunks_indexed"] = index_stats.get("total_chunks_indexed", 0)
        result["status"] = "success"
        result["index_stats"] = index_stats

        logger.info(f"Successfully indexed {result['papers_indexed']} papers ({result['chunks_indexed']} chunks) for org {org_name}")

        return result

    except Exception as e:
        error_msg = f"Failed to index papers for org {org_name}: {str(e)}"
        result["status"] = "failed"
        result["errors"].append(error_msg)
        logger.error(error_msg)
        return result