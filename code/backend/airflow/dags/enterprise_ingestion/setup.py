"""
Enterprise environment setup and validation for research-copilot ingestion pipeline.
"""

import logging
import os
import sys
from typing import Dict, Any
from datetime import datetime

# Add the src directory to the path to import research-copilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from services.monitoring import performance_monitor
from services.organization import organization_service
from database import get_db_session
from services.opensearch.client import OpenSearchClient
from services.arxiv import ArxivClient
from config import Settings
from dags.enterprise_ingestion.tracing import enterprise_tracer

logger = logging.getLogger(__name__)


def setup_enterprise_environment() -> Dict[str, Any]:
    """
    Setup and validate enterprise environment for paper ingestion.

    :returns: Dictionary with setup status and validation results
    """
    logger.info("Setting up enterprise environment for paper ingestion")

    setup_results = {
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "validations": {},
        "services": {},
        "errors": []
    }

    with enterprise_tracer.trace_task("enterprise_setup_validation") as span:
        try:
            # Load configuration
            settings = Settings()

            # Validate database connectivity
        try:
            with get_db_session() as session:
                session.execute("SELECT 1")
            setup_results["validations"]["database"] = {"status": "success", "message": "Database connection verified"}
            logger.info("Database connection validated")
        except Exception as e:
            error_msg = f"Database connection failed: {str(e)}"
            setup_results["validations"]["database"] = {"status": "failed", "error": error_msg}
            setup_results["errors"].append(error_msg)
            logger.error(error_msg)

        # Validate OpenSearch connectivity
        try:
            opensearch_client = OpenSearchClient()
            health = opensearch_client.client.cluster.health()
            if health["status"] in ["green", "yellow"]:
                setup_results["validations"]["opensearch"] = {
                    "status": "success",
                    "message": f"OpenSearch cluster healthy (status: {health['status']})"
                }
                logger.info("OpenSearch connection validated")
            else:
                raise Exception(f"OpenSearch cluster unhealthy: {health['status']}")
        except Exception as e:
            error_msg = f"OpenSearch validation failed: {str(e)}"
            setup_results["validations"]["opensearch"] = {"status": "failed", "error": error_msg}
            setup_results["errors"].append(error_msg)
            logger.error(error_msg)

        # Validate arXiv client
        try:
            arxiv_client = ArxivClient(settings)
            # Test with a minimal query
            test_papers = arxiv_client.fetch_papers(max_results=1)
            setup_results["validations"]["arxiv"] = {
                "status": "success",
                "message": f"arXiv client ready (base_url: {arxiv_client.base_url})"
            }
            logger.info("arXiv client validated")
        except Exception as e:
            error_msg = f"arXiv client validation failed: {str(e)}"
            setup_results["validations"]["arxiv"] = {"status": "failed", "error": error_msg}
            setup_results["errors"].append(error_msg)
            logger.error(error_msg)

        # Validate organization service
        try:
            # Test organization service availability
            org_count = len(organization_service.list_organizations())
            setup_results["validations"]["organization"] = {
                "status": "success",
                "message": f"Organization service ready ({org_count} organizations found)"
            }
            logger.info("Organization service validated")
        except Exception as e:
            error_msg = f"Organization service validation failed: {str(e)}"
            setup_results["validations"]["organization"] = {"status": "failed", "error": error_msg}
            setup_results["errors"].append(error_msg)
            logger.error(error_msg)

        # Validate monitoring service
        try:
            system_metrics = performance_monitor.get_system_metrics()
            setup_results["validations"]["monitoring"] = {
                "status": "success",
                "message": "Monitoring service ready",
                "system_info": {
                    "cpu_usage": system_metrics.get("cpu_percent", "unknown"),
                    "memory_usage": system_metrics.get("memory_percent", "unknown")
                }
            }
            logger.info("Monitoring service validated")
        except Exception as e:
            error_msg = f"Monitoring service validation failed: {str(e)}"
            setup_results["validations"]["monitoring"] = {"status": "failed", "error": error_msg}
            setup_results["errors"].append(error_msg)
            logger.error(error_msg)

        # Check for required environment variables
        required_env_vars = [
            "DATABASE_URL",
            "OPENSEARCH_HOST",
            "OPENSEARCH_PORT",
            "ARXIV_BASE_URL"
        ]

        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            setup_results["validations"]["environment"] = {"status": "failed", "error": error_msg}
            setup_results["errors"].append(error_msg)
            logger.error(error_msg)
        else:
            setup_results["validations"]["environment"] = {
                "status": "success",
                "message": "All required environment variables present"
            }

        # Determine overall status
        failed_validations = [k for k, v in setup_results["validations"].items() if v["status"] == "failed"]
        if failed_validations:
            setup_results["status"] = "failed"
            setup_results["message"] = f"Setup failed with {len(failed_validations)} validation errors"
        else:
            setup_results["status"] = "success"
            setup_results["message"] = "Enterprise environment setup completed successfully"

            # Record setup metrics
            performance_monitor.record_paper_ingestion("setup", setup_results["status"])

            # Record tracing metrics
            enterprise_tracer.record_task_metric(
                "enterprise_setup_validation",
                "validations_completed",
                len(setup_results["validations"]),
                organization_id=None
            )
            enterprise_tracer.record_task_metric(
                "enterprise_setup_validation",
                "errors_count",
                len(setup_results["errors"]),
                organization_id=None
            )

            logger.info(f"Enterprise setup completed with status: {setup_results['status']}")
            return setup_results

        except Exception as e:
            error_msg = f"Unexpected error during enterprise setup: {str(e)}"
            setup_results["status"] = "failed"
            setup_results["message"] = error_msg
            setup_results["errors"].append(error_msg)

            # Record error in trace
            enterprise_tracer.record_error("enterprise_setup_validation", e)

            logger.error(error_msg)
            return setup_results