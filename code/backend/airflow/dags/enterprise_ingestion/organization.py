"""
Organization management and paper assignment for enterprise ingestion.
"""

import logging
import os
from typing import Dict, Any, List
from datetime import datetime
from uuid import UUID

# Add the src directory to the path
sys_path = os.path.join(os.path.dirname(__file__), '../../../src')
if sys_path not in os.sys.path:
    os.sys.path.insert(0, sys_path)

from services.organization import organization_service
from database import get_db_session
from services.monitoring import performance_monitor
from dags.enterprise_ingestion.tracing import enterprise_tracer

logger = logging.getLogger(__name__)


def get_active_organizations(security_result: Dict[str, Any], max_orgs: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve active organizations eligible for paper ingestion.

    :param security_result: Security validation results
    :param max_orgs: Maximum number of organizations to return
    :returns: List of active organizations with ingestion permissions
    """
    logger.info(f"Retrieving active organizations (max: {max_orgs})")

    organizations = []

    with enterprise_tracer.trace_task("get_active_organizations") as span:
        try:
            # Check if security validation passed
            if security_result.get("status") != "success":
                logger.warning("Security validation failed - cannot retrieve organizations")
                return []

        # Get organizations from security result if available
        security_orgs = security_result.get("validations", {}).get("organization_permissions", {}).get("organizations", [])

        if security_orgs:
            # Filter for active organizations with ingestion permissions
            active_orgs = [
                org for org in security_orgs
                if org.get("is_active", False) and org.get("ingestion_allowed", False)
            ]

            # Convert to the expected format
            for org in active_orgs[:max_orgs]:
                organizations.append({
                    "id": org["org_id"],
                    "name": org["org_name"],
                    "max_users": org["max_users"],
                    "ingestion_limit": min(org["max_users"] * 10, 500),  # Rough estimate based on users
                    "priority": _calculate_org_priority(org)
                })

            logger.info(f"Found {len(organizations)} active organizations from security validation")
        else:
            # Fallback: get organizations directly from service
            with get_db_session() as session:
                all_orgs = organization_service.list_organizations()

                for org in all_orgs:
                    if org.is_active and _check_org_ingestion_permission(org.id):
                        organizations.append({
                            "id": str(org.id),
                            "name": org.name,
                            "max_users": org.max_users,
                            "ingestion_limit": min(org.max_users * 10, 500),
                            "priority": _calculate_org_priority({"max_users": org.max_users})
                        })

                        if len(organizations) >= max_orgs:
                            break

            logger.info(f"Retrieved {len(organizations)} active organizations from database")

        # Sort by priority (higher priority first)
        organizations.sort(key=lambda x: x["priority"], reverse=True)

        return organizations

    except Exception as e:
        logger.error(f"Failed to retrieve active organizations: {e}")
        return []


def assign_papers_to_organizations(
    organizations: List[Dict[str, Any]],
    fetch_result: Dict[str, Any],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Assign fetched papers to appropriate organizations based on rules and limits.

    :param organizations: List of active organizations
    :param fetch_result: Results from paper fetching
    :param config: Enterprise configuration
    :returns: Assignment results with paper distribution
    """
    logger.info("Starting organization-based paper assignment")

    assignment_results = {
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "total_papers_fetched": fetch_result.get("papers_fetched", 0),
        "organizations_processed": len(organizations),
        "assignments": {},
        "unassigned_papers": 0,
        "errors": []
    }

    try:
        papers_data = fetch_result.get("papers", [])
        if not papers_data:
            logger.warning("No papers data found in fetch result")
            assignment_results["status"] = "success"
            assignment_results["message"] = "No papers to assign"
            return assignment_results

        # Initialize assignment tracking
        for org in organizations:
            assignment_results["assignments"][org["id"]] = {
                "org_name": org["name"],
                "assigned_papers": [],
                "paper_count": 0,
                "limit": org["ingestion_limit"],
                "remaining_capacity": org["ingestion_limit"]
            }

        # Assign papers using round-robin with capacity limits
        paper_index = 0
        org_index = 0

        for paper in papers_data:
            assigned = False

            # Try to assign to organizations in priority order
            for attempt in range(len(organizations)):
                current_org = organizations[(org_index + attempt) % len(organizations)]
                org_id = current_org["id"]
                org_assignment = assignment_results["assignments"][org_id]

                # Check if organization has capacity
                if org_assignment["remaining_capacity"] > 0:
                    org_assignment["assigned_papers"].append(paper)
                    org_assignment["paper_count"] += 1
                    org_assignment["remaining_capacity"] -= 1
                    assigned = True

                    logger.debug(f"Assigned paper {paper.get('arxiv_id', 'unknown')} to org {org_id}")
                    break

            if not assigned:
                assignment_results["unassigned_papers"] += 1
                logger.warning(f"Could not assign paper {paper.get('arxiv_id', 'unknown')} - all organizations at capacity")

            paper_index += 1
            org_index = (org_index + 1) % len(organizations)

        # Calculate assignment statistics
        total_assigned = sum(org["paper_count"] for org in assignment_results["assignments"].values())
        assignment_results["total_assigned"] = total_assigned
        assignment_results["assignment_rate"] = total_assigned / len(papers_data) if papers_data else 0

        # Record assignment metrics
        performance_monitor.record_paper_ingestion("assignment", "success", total_assigned)

        assignment_results["status"] = "success"
        assignment_results["message"] = f"Assigned {total_assigned} papers to {len(organizations)} organizations"

        logger.info(f"Paper assignment completed: {total_assigned} papers assigned, {assignment_results['unassigned_papers']} unassigned")
        return assignment_results

    except Exception as e:
        error_msg = f"Paper assignment failed: {str(e)}"
        assignment_results["status"] = "failed"
        assignment_results["message"] = error_msg
        assignment_results["errors"].append(error_msg)
        logger.error(error_msg)
        return assignment_results


def _calculate_org_priority(org_data: Dict[str, Any]) -> int:
    """
    Calculate organization priority for paper assignment.

    :param org_data: Organization data
    :returns: Priority score (higher = more priority)
    """
    try:
        # Priority based on user capacity (larger orgs get higher priority)
        max_users = org_data.get("max_users", 10)
        return min(max_users // 10, 10)  # Cap at 10, scale by 10s
    except Exception:
        return 1  # Default low priority


def _check_org_ingestion_permission(org_id: str) -> bool:
    """
    Check if organization has ingestion permission.

    :param org_id: Organization ID
    :returns: True if organization can ingest papers
    """
    try:
        # In a real implementation, this would check specific permissions
        # For now, assume all organizations can ingest
        return True
    except Exception as e:
        logger.error(f"Error checking ingestion permission for org {org_id}: {e}")
        return False