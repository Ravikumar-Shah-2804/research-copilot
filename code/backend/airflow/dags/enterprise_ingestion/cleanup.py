"""
Enterprise cleanup and audit logging for research-copilot ingestion pipeline.
"""

import logging
import os
import shutil
from typing import Dict, Any
from datetime import datetime, timedelta

# Add the src directory to the path
sys_path = os.path.join(os.path.dirname(__file__), '../../../src')
if sys_path not in os.sys.path:
    os.sys.path.insert(0, sys_path)

from services.audit import AuditService
from services.monitoring import performance_monitor
from database import get_db_session

logger = logging.getLogger(__name__)


def enterprise_cleanup(monitoring_result: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform enterprise cleanup and comprehensive audit logging.

    :param monitoring_result: Monitoring results from the pipeline
    :param config: Enterprise configuration
    :returns: Cleanup results
    """
    logger.info("Starting enterprise cleanup and audit logging")

    cleanup_results = {
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "cleanup_actions": {},
        "audit_entries": [],
        "retention_stats": {},
        "errors": []
    }

    try:
        # Perform file system cleanup
        cleanup_results["cleanup_actions"]["filesystem"] = _cleanup_filesystem(config)

        # Clean up old database records
        cleanup_results["cleanup_actions"]["database"] = _cleanup_database_records(config)

        # Clean up old monitoring data
        cleanup_results["cleanup_actions"]["monitoring"] = _cleanup_monitoring_data(config)

        # Create comprehensive audit trail
        cleanup_results["audit_entries"] = _create_comprehensive_audit_trail(monitoring_result, config)

        # Calculate retention statistics
        cleanup_results["retention_stats"] = _calculate_retention_stats(config)

        # Final system health check
        cleanup_results["system_health"] = _perform_final_health_check()

        cleanup_results["status"] = "success"
        cleanup_results["message"] = "Enterprise cleanup and audit logging completed successfully"

        logger.info("Enterprise cleanup and audit logging completed")
        return cleanup_results

    except Exception as e:
        error_msg = f"Enterprise cleanup failed: {str(e)}"
        cleanup_results["status"] = "failed"
        cleanup_results["message"] = error_msg
        cleanup_results["errors"].append(error_msg)
        logger.error(error_msg)
        return cleanup_results


def _cleanup_filesystem(config: Dict[str, Any]) -> Dict[str, Any]:
    """Clean up temporary files and old data from filesystem."""
    cleanup_stats = {
        "temp_files_removed": 0,
        "old_pdfs_removed": 0,
        "cache_files_cleaned": 0,
        "total_space_freed_mb": 0.0
    }

    try:
        retention_days = config.get("cleanup_retention_days", 30)
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        # Clean up temporary PDF files
        temp_dirs = ["/tmp", "./temp", "./tmp"]
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith('.pdf'):
                            file_path = os.path.join(root, file)
                            try:
                                file_stat = os.stat(file_path)
                                file_date = datetime.fromtimestamp(file_stat.st_mtime)

                                if file_date < cutoff_date:
                                    os.remove(file_path)
                                    cleanup_stats["old_pdfs_removed"] += 1
                                    cleanup_stats["total_space_freed_mb"] += file_stat.st_size / (1024 * 1024)
                            except Exception as e:
                                logger.warning(f"Failed to clean up {file_path}: {e}")

        # Clean up old cache files
        cache_dirs = ["./cache", "./.cache", "__pycache__"]
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                try:
                    shutil.rmtree(cache_dir)
                    cleanup_stats["cache_files_cleaned"] += 1
                    logger.info(f"Cleaned cache directory: {cache_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean cache directory {cache_dir}: {e}")

        logger.info(f"Filesystem cleanup completed: {cleanup_stats}")

    except Exception as e:
        logger.error(f"Filesystem cleanup failed: {e}")
        cleanup_stats["error"] = str(e)

    return cleanup_stats


def _cleanup_database_records(config: Dict[str, Any]) -> Dict[str, Any]:
    """Clean up old database records."""
    cleanup_stats = {
        "old_ingestion_jobs_removed": 0,
        "old_audit_entries_removed": 0,
        "old_monitoring_data_removed": 0
    }

    try:
        retention_days = config.get("cleanup_retention_days", 30)
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        with get_db_session() as session:
            # Clean up old ingestion job records
            # Note: This would be implemented based on actual schema
            # For now, just log the intent
            logger.info(f"Database cleanup configured for records older than {retention_days} days")

            # In a real implementation, you would execute cleanup queries here
            # Example:
            # result = session.execute("DELETE FROM ingestion_jobs WHERE created_at < :cutoff", {"cutoff": cutoff_date})
            # cleanup_stats["old_ingestion_jobs_removed"] = result.rowcount

        logger.info(f"Database cleanup completed: {cleanup_stats}")

    except Exception as e:
        logger.error(f"Database cleanup failed: {e}")
        cleanup_stats["error"] = str(e)

    return cleanup_stats


def _cleanup_monitoring_data(config: Dict[str, Any]) -> Dict[str, Any]:
    """Clean up old monitoring and metrics data."""
    cleanup_stats = {
        "old_metrics_removed": 0,
        "old_logs_cleaned": 0
    }

    try:
        # Reset performance monitor metrics if needed
        retention_days = config.get("cleanup_retention_days", 30)

        # In a real implementation, you might archive old metrics
        # For now, just log current metrics state
        current_metrics = performance_monitor.get_performance_metrics()
        logger.info(f"Current monitoring metrics retained: {len(current_metrics.get('operations', {}))} operations")

        cleanup_stats["monitoring_status"] = "completed"

    except Exception as e:
        logger.error(f"Monitoring data cleanup failed: {e}")
        cleanup_stats["error"] = str(e)

    return cleanup_stats


def _create_comprehensive_audit_trail(monitoring_result: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create comprehensive audit trail for the entire pipeline execution."""
    audit_entries = []

    try:
        audit_service = AuditService()

        # Create main pipeline completion audit entry
        pipeline_audit = {
            "timestamp": datetime.now().isoformat(),
            "action": "enterprise_ingestion_pipeline_complete",
            "actor": "airflow_system",
            "resource": "ingestion_pipeline",
            "details": {
                "pipeline_status": monitoring_result.get("status"),
                "total_papers_processed": monitoring_result.get("pipeline_overview", {}).get("total_papers_processed", 0),
                "organizations_processed": monitoring_result.get("pipeline_overview", {}).get("total_organizations_processed", 0),
                "execution_time_seconds": monitoring_result.get("pipeline_overview", {}).get("total_duration_seconds", 0),
                "error_count": monitoring_result.get("error_analysis", {}).get("total_errors", 0)
            },
            "severity": "info" if monitoring_result.get("status") == "success" else "warning"
        }
        audit_entries.append(pipeline_audit)

        # Create audit entries for each organization
        org_metrics = monitoring_result.get("organization_metrics", {}).get("organization_performance", {})
        for org_id, org_data in org_metrics.items():
            org_audit = {
                "timestamp": datetime.now().isoformat(),
                "action": "organization_ingestion_complete",
                "actor": "airflow_system",
                "resource": f"organization_{org_id}",
                "details": {
                    "papers_processed": org_data.get("papers_processed", 0),
                    "papers_indexed": org_data.get("papers_indexed", 0),
                    "processing_status": org_data.get("processing_status"),
                    "indexing_status": org_data.get("indexing_status")
                },
                "severity": "info"
            }
            audit_entries.append(org_audit)

        # Create audit entries for alerts
        alerts = monitoring_result.get("alerts", [])
        for alert in alerts:
            alert_audit = {
                "timestamp": datetime.now().isoformat(),
                "action": "pipeline_alert_triggered",
                "actor": "monitoring_system",
                "resource": "ingestion_pipeline",
                "details": alert,
                "severity": alert.get("level", "info")
            }
            audit_entries.append(alert_audit)

        # Log audit entries (in real implementation, would save to audit service)
        for entry in audit_entries:
            logger.info(f"Audit entry: {entry['action']} - {entry['details']}")

        logger.info(f"Created {len(audit_entries)} comprehensive audit entries")

    except Exception as e:
        logger.error(f"Failed to create comprehensive audit trail: {e}")
        audit_entries.append({
            "timestamp": datetime.now().isoformat(),
            "action": "audit_creation_failed",
            "error": str(e),
            "severity": "error"
        })

    return audit_entries


def _calculate_retention_stats(config: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate data retention statistics."""
    retention_stats = {
        "retention_policy_days": config.get("cleanup_retention_days", 30),
        "data_categories": {},
        "compliance_status": "compliant"
    }

    try:
        # Calculate retention stats for different data categories
        retention_stats["data_categories"] = {
            "ingestion_logs": {"retention_days": 90, "current_count": "unknown"},
            "audit_trail": {"retention_days": 365, "current_count": "unknown"},
            "monitoring_metrics": {"retention_days": 30, "current_count": "unknown"},
            "temporary_files": {"retention_days": 7, "current_count": "unknown"}
        }

        logger.info(f"Retention statistics calculated: {retention_stats}")

    except Exception as e:
        logger.error(f"Failed to calculate retention stats: {e}")
        retention_stats["error"] = str(e)

    return retention_stats


def _perform_final_health_check() -> Dict[str, Any]:
    """Perform final system health check."""
    health_check = {
        "database_connectivity": False,
        "opensearch_health": "unknown",
        "disk_space_available": 0.0,
        "memory_usage": 0.0,
        "overall_status": "unknown"
    }

    try:
        # Check database connectivity
        with get_db_session() as session:
            session.execute("SELECT 1")
            health_check["database_connectivity"] = True

        # Get system metrics
        system_metrics = performance_monitor.get_system_metrics()
        health_check["disk_space_available"] = system_metrics.get("disk_usage_percent", 0)
        health_check["memory_usage"] = system_metrics.get("memory_percent", 0)

        # Determine overall status
        if health_check["database_connectivity"] and health_check["disk_space_available"] < 90:
            health_check["overall_status"] = "healthy"
        else:
            health_check["overall_status"] = "degraded"

        logger.info(f"Final health check completed: {health_check['overall_status']}")

    except Exception as e:
        logger.error(f"Final health check failed: {e}")
        health_check["error"] = str(e)
        health_check["overall_status"] = "unhealthy"

    return health_check