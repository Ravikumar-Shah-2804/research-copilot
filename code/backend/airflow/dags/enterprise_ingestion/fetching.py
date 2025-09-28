"""
Distributed paper fetching for enterprise ingestion pipeline.
"""

import asyncio
import logging
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the src directory to the path
sys_path = os.path.join(os.path.dirname(__file__), '../../../src')
if sys_path not in os.sys.path:
    os.sys.path.insert(0, sys_path)

from services.arxiv import ArxivClient
from services.monitoring import performance_monitor
from schemas.arxiv import ArxivSearchQuery
from config import Settings

logger = logging.getLogger(__name__)


def fetch_papers_enterprise(organizations: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch papers using distributed processing across organizations.

    :param organizations: List of organizations to fetch papers for
    :param config: Enterprise configuration
    :returns: Fetch results with papers data
    """
    logger.info(f"Starting distributed paper fetching for {len(organizations)} organizations")

    fetch_results = {
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "organizations_processed": len(organizations),
        "total_papers_fetched": 0,
        "papers": [],
        "organization_stats": {},
        "errors": [],
        "performance_metrics": {}
    }

    try:
        settings = Settings()
        arxiv_client = ArxivClient(settings)

        # Calculate papers per organization based on their limits
        total_limit = sum(org.get("ingestion_limit", 100) for org in organizations)
        max_workers = min(config.get("distributed_workers", 4), len(organizations))

        logger.info(f"Using {max_workers} workers for distributed fetching (total limit: {total_limit})")

        # Use ThreadPoolExecutor for concurrent fetching
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit fetch tasks for each organization
            future_to_org = {}
            for org in organizations:
                org_limit = min(org.get("ingestion_limit", 100), config.get("papers_per_organization_limit", 500))
                future = executor.submit(_fetch_papers_for_organization, arxiv_client, org, org_limit, config)
                future_to_org[future] = org

            # Collect results as they complete
            start_time = datetime.now()
            for future in as_completed(future_to_org):
                org = future_to_org[future]
                try:
                    org_result = future.result()
                    org_id = org["id"]

                    fetch_results["organization_stats"][org_id] = org_result
                    fetch_results["total_papers_fetched"] += org_result["papers_fetched"]

                    # Add papers to main collection
                    if org_result["papers"]:
                        # Tag papers with organization info
                        for paper in org_result["papers"]:
                            paper["assigned_organization"] = org_id
                        fetch_results["papers"].extend(org_result["papers"])

                    logger.info(f"Completed fetching for org {org_id}: {org_result['papers_fetched']} papers")

                except Exception as e:
                    org_id = org["id"]
                    error_msg = f"Failed to fetch papers for organization {org_id}: {str(e)}"
                    fetch_results["errors"].append(error_msg)
                    fetch_results["organization_stats"][org_id] = {
                        "status": "failed",
                        "error": str(e),
                        "papers_fetched": 0,
                        "papers": []
                    }
                    logger.error(error_msg)

        # Calculate performance metrics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        fetch_results["performance_metrics"] = {
            "total_duration_seconds": duration,
            "papers_per_second": fetch_results["total_papers_fetched"] / duration if duration > 0 else 0,
            "organizations_successful": len([s for s in fetch_results["organization_stats"].values() if s.get("status") == "success"]),
            "organizations_failed": len([s for s in fetch_results["organization_stats"].values() if s.get("status") == "failed"])
        }

        # Record monitoring metrics
        performance_monitor.record_paper_ingestion("fetch", "success", fetch_results["total_papers_fetched"])

        fetch_results["status"] = "success"
        fetch_results["message"] = f"Successfully fetched {fetch_results['total_papers_fetched']} papers across {len(organizations)} organizations"

        logger.info(f"Distributed fetching completed: {fetch_results['total_papers_fetched']} papers fetched")
        return fetch_results

    except Exception as e:
        error_msg = f"Distributed paper fetching failed: {str(e)}"
        fetch_results["status"] = "failed"
        fetch_results["message"] = error_msg
        fetch_results["errors"].append(error_msg)
        logger.error(error_msg)
        return fetch_results


def _fetch_papers_for_organization(
    arxiv_client: ArxivClient,
    organization: Dict[str, Any],
    limit: int,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Fetch papers for a specific organization.

    :param arxiv_client: ArXiv client instance
    :param organization: Organization data
    :param limit: Maximum papers to fetch
    :param config: Enterprise configuration
    :returns: Fetch results for this organization
    """
    org_id = organization["id"]
    org_name = organization["name"]

    logger.info(f"Fetching papers for organization {org_name} (ID: {org_id}), limit: {limit}")

    result = {
        "org_id": org_id,
        "org_name": org_name,
        "status": "pending",
        "papers_fetched": 0,
        "papers": [],
        "errors": []
    }

    try:
        # Create search query for recent papers
        search_query = ArxivSearchQuery(
            query="cat:cs.AI",  # Focus on AI papers
            start=0,
            max_results=min(limit, 100),  # API limit
            sort_by="submittedDate",
            sort_order="descending"
        )

        # Fetch papers
        papers = arxiv_client.fetch_papers(search_query)

        if papers:
            # Convert to dict format
            papers_data = []
            for paper in papers:
                paper_dict = {
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "abstract": paper.abstract,
                    "categories": paper.categories,
                    "published_date": paper.published_date.isoformat() if paper.published_date else None,
                    "pdf_url": paper.pdf_url,
                    "doi": getattr(paper, 'doi', None),
                    "journal_ref": getattr(paper, 'journal_ref', None),
                    "comments": getattr(paper, 'comments', None),
                    "source": "arxiv"
                }
                papers_data.append(paper_dict)

            result["papers"] = papers_data
            result["papers_fetched"] = len(papers_data)
            result["status"] = "success"

            logger.info(f"Successfully fetched {len(papers_data)} papers for org {org_name}")
        else:
            result["status"] = "success"
            result["message"] = "No papers found"
            logger.info(f"No papers found for org {org_name}")

        return result

    except Exception as e:
        error_msg = f"Failed to fetch papers for org {org_name}: {str(e)}"
        result["status"] = "failed"
        result["errors"].append(error_msg)
        logger.error(error_msg)
        return result