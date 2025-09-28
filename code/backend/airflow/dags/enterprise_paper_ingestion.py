"""
Enterprise Paper Ingestion DAG for research-copilot

This DAG extends the basic arxiv-paper-curator pipeline with enterprise features:
- Organization-based access control and paper assignment
- Distributed processing capabilities
- Comprehensive monitoring and metrics
- Enhanced security and audit logging
- Multi-tenant paper ingestion with organization isolation
"""

from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List, Optional
import json

from airflow import DAG
from airflow.decorators import dag, task
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.dummy import DummyOperator
from airflow.utils.trigger_rule import TriggerRule
from airflow.models import Variable
from airflow.sensors.base import BaseSensorOperator

# Enterprise imports
from dags.enterprise_ingestion.fetching import fetch_papers_enterprise
from dags.enterprise_ingestion.indexing import index_papers_enterprise
from dags.enterprise_ingestion.monitoring import monitor_ingestion_pipeline
from dags.enterprise_ingestion.organization import assign_papers_to_organizations
from dags.enterprise_ingestion.security import validate_enterprise_access
from dags.enterprise_ingestion.distributed import distribute_processing_tasks
from dags.enterprise_ingestion.tracing import enterprise_tracer

logger = logging.getLogger(__name__)

# Enterprise-specific default arguments
default_args = {
    "owner": "research-copilot-enterprise",
    "depends_on_past": False,
    "start_date": datetime(2025, 9, 26),
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=15),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(hours=2),
    "execution_timeout": timedelta(hours=4),
    "catchup": False,
    "tags": ["enterprise", "papers", "ingestion", "multi-tenant", "distributed", "monitoring"],
}

# Enterprise configuration
ENTERPRISE_CONFIG = {
    "max_organizations_per_run": 10,
    "papers_per_organization_limit": 500,
    "distributed_workers": 4,
    "monitoring_enabled": True,
    "audit_logging": True,
    "security_validation": True,
    "cleanup_retention_days": 30,
}


@dag(
    dag_id="enterprise_paper_ingestion",
    default_args=default_args,
    description="Enterprise multi-tenant paper ingestion pipeline with organization access control, distributed processing, and comprehensive monitoring",
    schedule="@daily",  # Run daily at midnight UTC
    max_active_runs=3,  # Allow multiple concurrent runs for different organizations
    concurrency=8,  # Allow 8 concurrent tasks
    catchup=False,
    tags=["enterprise", "papers", "ingestion", "multi-tenant"],
)
def enterprise_paper_ingestion_dag():
    """
    Main enterprise paper ingestion DAG.

    Workflow:
    1. Tracing initialization
    2. Enterprise setup and validation
    3. Organization access control check
    4. Distributed paper fetching
    5. Organization-based paper assignment
    6. Parallel processing and indexing
    7. Monitoring and reporting
    8. Cleanup and audit logging
    """

    # Task 0: Initialize tracing for the pipeline
    @task(task_id="initialize_tracing")
    def initialize_tracing(**context) -> str:
        """Initialize Langfuse tracing for the enterprise pipeline."""
        from datetime import datetime

        execution_date = context['execution_date']
        logger.info("Initializing enterprise pipeline tracing")

        try:
            # Start pipeline trace
            trace_id = enterprise_tracer.start_pipeline_trace(execution_date)
            logger.info(f"Pipeline tracing initialized with trace ID: {trace_id}")

            # Push trace ID to XCom for downstream tasks
            context['ti'].xcom_push(key="trace_id", value=trace_id)
            return trace_id

        except Exception as e:
            logger.error(f"Failed to initialize tracing: {e}")
            # Return a fallback trace ID to ensure pipeline continues
            fallback_id = f"fallback-{int(datetime.now().timestamp())}"
            context['ti'].xcom_push(key="trace_id", value=fallback_id)
            return fallback_id

    # Task 1: Enterprise environment setup and validation
    @task(task_id="enterprise_setup_validation")
    def enterprise_setup_validation(**context) -> Dict[str, Any]:
        """Validate enterprise environment and dependencies."""
        from dags.enterprise_ingestion.setup import setup_enterprise_environment

        logger.info("Starting enterprise environment setup and validation")

        try:
            setup_result = setup_enterprise_environment()
            logger.info(f"Enterprise setup completed: {setup_result}")

            # Push setup results to XCom for downstream tasks
            context['ti'].xcom_push(key="setup_result", value=setup_result)
            return setup_result

        except Exception as e:
            logger.error(f"Enterprise setup failed: {e}")
            raise

    # Task 2: Security and access control validation
    @task(task_id="security_access_validation")
    def security_access_validation(setup_result: Dict[str, Any], **context) -> Dict[str, Any]:
        """Validate security requirements and access controls."""
        logger.info("Validating enterprise security and access controls")

        try:
            security_result = validate_enterprise_access(setup_result)
            logger.info(f"Security validation completed: {security_result}")

            context['ti'].xcom_push(key="security_result", value=security_result)
            return security_result

        except Exception as e:
            logger.error(f"Security validation failed: {e}")
            raise

    # Task 3: Get active organizations for processing
    @task(task_id="get_active_organizations")
    def get_active_organizations(trace_id: str, security_result: Dict[str, Any], **context) -> List[Dict[str, Any]]:
        """Retrieve active organizations eligible for paper ingestion."""
        from dags.enterprise_ingestion.organization import get_active_organizations

        logger.info("Retrieving active organizations for paper ingestion")

        try:
            organizations = get_active_organizations(
                security_result=security_result,
                max_orgs=ENTERPRISE_CONFIG["max_organizations_per_run"]
            )

            logger.info(f"Found {len(organizations)} active organizations for processing")

            # Update tracer with organization context for multi-tenant observability
            if organizations:
                enterprise_tracer.start_pipeline_trace(
                    context['execution_date'],
                    organizations
                )

            context['ti'].xcom_push(key="organizations", value=organizations)
            return organizations

        except Exception as e:
            logger.error(f"Failed to retrieve active organizations: {e}")
            enterprise_tracer.record_error("get_active_organizations", e)
            raise

    # Task 4: Branch based on available organizations
    @task.branch(task_id="check_organizations_available")
    def check_organizations_available(organizations: List[Dict[str, Any]]) -> str:
        """Check if there are organizations to process."""
        if not organizations:
            logger.warning("No active organizations found for processing")
            return "no_organizations_skip"
        else:
            logger.info(f"Processing {len(organizations)} organizations")
            return "distributed_paper_fetch"

    # Task 5: Distributed paper fetching
    @task(task_id="distributed_paper_fetch")
    def distributed_paper_fetch(organizations: List[Dict[str, Any]], **context) -> Dict[str, Any]:
        """Fetch papers using distributed processing across organizations."""
        logger.info("Starting distributed paper fetching")

        try:
            fetch_result = fetch_papers_enterprise(
                organizations=organizations,
                config=ENTERPRISE_CONFIG
            )

            logger.info(f"Distributed fetching completed: {fetch_result}")

            context['ti'].xcom_push(key="fetch_result", value=fetch_result)
            return fetch_result

        except Exception as e:
            logger.error(f"Distributed paper fetching failed: {e}")
            raise

    # Task 6: Organization-based paper assignment
    @task(task_id="organization_paper_assignment")
    def organization_paper_assignment(
        organizations: List[Dict[str, Any]],
        fetch_result: Dict[str, Any],
        **context
    ) -> Dict[str, Any]:
        """Assign fetched papers to appropriate organizations."""
        logger.info("Starting organization-based paper assignment")

        try:
            assignment_result = assign_papers_to_organizations(
                organizations=organizations,
                fetch_result=fetch_result,
                config=ENTERPRISE_CONFIG
            )

            logger.info(f"Paper assignment completed: {assignment_result}")

            context['ti'].xcom_push(key="assignment_result", value=assignment_result)
            return assignment_result

        except Exception as e:
            logger.error(f"Paper assignment failed: {e}")
            raise

    # Task 7: Distributed processing and indexing
    @task(task_id="distributed_processing_indexing")
    def distributed_processing_indexing(
        assignment_result: Dict[str, Any],
        **context
    ) -> Dict[str, Any]:
        """Process and index papers using distributed workers."""
        logger.info("Starting distributed processing and indexing")

        try:
            processing_result = distribute_processing_tasks(
                assignment_result=assignment_result,
                config=ENTERPRISE_CONFIG
            )

            logger.info(f"Distributed processing completed: {processing_result}")

            context['ti'].xcom_push(key="processing_result", value=processing_result)
            return processing_result

        except Exception as e:
            logger.error(f"Distributed processing failed: {e}")
            raise

    # Task 8: Enterprise indexing with organization isolation
    @task(task_id="enterprise_indexing")
    def enterprise_indexing(
        processing_result: Dict[str, Any],
        organizations: List[Dict[str, Any]],
        **context
    ) -> Dict[str, Any]:
        """Index papers with enterprise features and organization isolation."""
        logger.info("Starting enterprise indexing")

        try:
            indexing_result = index_papers_enterprise(
                processing_result=processing_result,
                organizations=organizations,
                config=ENTERPRISE_CONFIG
            )

            logger.info(f"Enterprise indexing completed: {indexing_result}")

            context['ti'].xcom_push(key="indexing_result", value=indexing_result)
            return indexing_result

        except Exception as e:
            logger.error(f"Enterprise indexing failed: {e}")
            raise

    # Task 9: Comprehensive monitoring and metrics collection
    @task(task_id="enterprise_monitoring_reporting")
    def enterprise_monitoring_reporting(
        setup_result: Dict[str, Any],
        security_result: Dict[str, Any],
        fetch_result: Dict[str, Any],
        assignment_result: Dict[str, Any],
        processing_result: Dict[str, Any],
        indexing_result: Dict[str, Any],
        **context
    ) -> Dict[str, Any]:
        """Collect comprehensive monitoring data and generate reports."""
        logger.info("Starting enterprise monitoring and reporting")

        try:
            monitoring_result = monitor_ingestion_pipeline(
                pipeline_results={
                    "setup": setup_result,
                    "security": security_result,
                    "fetch": fetch_result,
                    "assignment": assignment_result,
                    "processing": processing_result,
                    "indexing": indexing_result,
                },
                config=ENTERPRISE_CONFIG
            )

            logger.info(f"Monitoring and reporting completed: {monitoring_result}")

            context['ti'].xcom_push(key="monitoring_result", value=monitoring_result)
            return monitoring_result

        except Exception as e:
            logger.error(f"Monitoring and reporting failed: {e}")
            raise

    # Task 10: Enterprise cleanup and audit logging
    @task(task_id="enterprise_cleanup_audit")
    def enterprise_cleanup_audit(
        monitoring_result: Dict[str, Any],
        **context
    ) -> Dict[str, Any]:
        """Perform enterprise cleanup and comprehensive audit logging."""
        from dags.enterprise_ingestion.cleanup import enterprise_cleanup

        logger.info("Starting enterprise cleanup and audit logging")

        try:
            cleanup_result = enterprise_cleanup(
                monitoring_result=monitoring_result,
                config=ENTERPRISE_CONFIG
            )

            logger.info(f"Enterprise cleanup completed: {cleanup_result}")

            context['ti'].xcom_push(key="cleanup_result", value=cleanup_result)
            return cleanup_result

        except Exception as e:
            logger.error(f"Enterprise cleanup failed: {e}")
            raise

    # Task 11: Skip task for when no organizations are available
    @task(task_id="no_organizations_skip")
    def no_organizations_skip(**context) -> Dict[str, Any]:
        """Handle case when no organizations are available for processing."""
        logger.info("No organizations available for processing - skipping ingestion")

        result = {
            "status": "skipped",
            "reason": "no_active_organizations",
            "timestamp": datetime.now().isoformat(),
            "message": "No active organizations found for paper ingestion"
        }

        context['ti'].xcom_push(key="skip_result", value=result)
        return result

    # Task 12: Final success notification and tracing completion
    @task(task_id="pipeline_success_notification", trigger_rule=TriggerRule.ONE_SUCCESS)
    def pipeline_success_notification(
        trace_id: str,
        monitoring_result: Optional[Dict[str, Any]] = None,
        skip_result: Optional[Dict[str, Any]] = None,
        **context
    ) -> Dict[str, Any]:
        """Send success notification, log final pipeline status, and complete tracing."""
        from dags.enterprise_ingestion.notifications import send_pipeline_notification

        logger.info("Pipeline completed successfully - sending notifications and finalizing tracing")

        try:
            # Determine pipeline status and results
            if monitoring_result:
                pipeline_status = "success"
                final_result = monitoring_result
            elif skip_result:
                pipeline_status = "skipped"
                final_result = skip_result
            else:
                pipeline_status = "unknown"
                final_result = {"status": "unknown", "message": "No result data available"}

            # Send notification
            notification_result = send_pipeline_notification(
                status=pipeline_status,
                result=final_result,
                config=ENTERPRISE_CONFIG
            )

            # End pipeline tracing
            enterprise_tracer.end_pipeline_trace(
                status=pipeline_status,
                metrics=final_result if isinstance(final_result, dict) else {}
            )

            logger.info(f"Pipeline notification sent and tracing completed: {notification_result}")
            return notification_result

        except Exception as e:
            logger.error(f"Failed to send pipeline notification: {e}")
            # Still try to end tracing even if notification fails
            try:
                enterprise_tracer.end_pipeline_trace("failed", {"error": str(e)})
            except:
                pass
            return {"status": "notification_failed", "error": str(e)}

    # Define task dependencies
    trace_id = initialize_tracing()
    setup_result = enterprise_setup_validation()
    security_result = security_access_validation(setup_result)
    organizations = get_active_organizations(trace_id, security_result)

    check_orgs = check_organizations_available(organizations)

    # Main processing branch
    fetch_result = distributed_paper_fetch(organizations)
    assignment_result = organization_paper_assignment(organizations, fetch_result)
    processing_result = distributed_processing_indexing(assignment_result)
    indexing_result = enterprise_indexing(processing_result, organizations)

    # Monitoring and reporting
    monitoring_result = enterprise_monitoring_reporting(
        setup_result, security_result, fetch_result,
        assignment_result, processing_result, indexing_result
    )

    # Cleanup
    cleanup_result = enterprise_cleanup_audit(monitoring_result)

    # Skip branch
    skip_result = no_organizations_skip()

    # Final notification and tracing completion
    notification = pipeline_success_notification(trace_id, monitoring_result, skip_result)

    # Set up dependencies
    trace_id >> setup_result >> security_result >> organizations >> check_orgs
    check_orgs >> [fetch_result, skip_result]
    fetch_result >> assignment_result >> processing_result >> indexing_result >> monitoring_result >> cleanup_result >> notification
    skip_result >> notification


# Instantiate the DAG
dag = enterprise_paper_ingestion_dag()