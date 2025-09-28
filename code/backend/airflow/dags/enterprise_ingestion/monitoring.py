"""
Comprehensive monitoring and metrics collection for enterprise ingestion pipeline.
"""

import logging
import os
from typing import Dict, Any
from datetime import datetime

# Add the src directory to the path
sys_path = os.path.join(os.path.dirname(__file__), '../../../src')
if sys_path not in os.sys.path:
    os.sys.path.insert(0, sys_path)

from services.monitoring import performance_monitor
from services.audit import AuditService

logger = logging.getLogger(__name__)


def monitor_ingestion_pipeline(pipeline_results: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Collect comprehensive monitoring data and generate reports for the ingestion pipeline.

    :param pipeline_results: Results from all pipeline stages
    :param config: Enterprise configuration
    :returns: Monitoring report
    """
    logger.info("Starting comprehensive pipeline monitoring and reporting")

    monitoring_report = {
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "pipeline_overview": {},
        "performance_metrics": {},
        "organization_metrics": {},
        "error_analysis": {},
        "recommendations": [],
        "alerts": [],
        "audit_entries": [],
        "errors": []
    }

    try:
        # Calculate pipeline overview
        monitoring_report["pipeline_overview"] = _calculate_pipeline_overview(pipeline_results)

        # Collect performance metrics
        monitoring_report["performance_metrics"] = _collect_performance_metrics(pipeline_results)

        # Analyze organization metrics
        monitoring_report["organization_metrics"] = _analyze_organization_metrics(pipeline_results)

        # Perform error analysis
        monitoring_report["error_analysis"] = _analyze_pipeline_errors(pipeline_results)

        # Generate recommendations
        monitoring_report["recommendations"] = _generate_recommendations(pipeline_results, config)

        # Check for alerts
        monitoring_report["alerts"] = _check_pipeline_alerts(pipeline_results, config)

        # Create audit entries
        monitoring_report["audit_entries"] = _create_audit_entries(pipeline_results)

        # Record comprehensive metrics
        _record_monitoring_metrics(monitoring_report, config)

        monitoring_report["status"] = "success"
        monitoring_report["message"] = "Pipeline monitoring and reporting completed successfully"

        logger.info("Pipeline monitoring and reporting completed")
        return monitoring_report

    except Exception as e:
        error_msg = f"Pipeline monitoring failed: {str(e)}"
        monitoring_report["status"] = "failed"
        monitoring_report["message"] = error_msg
        monitoring_report["errors"].append(error_msg)
        logger.error(error_msg)
        return monitoring_report


def _calculate_pipeline_overview(pipeline_results: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate overall pipeline performance overview."""
    overview = {
        "total_duration_seconds": 0,
        "pipeline_success_rate": 0.0,
        "total_papers_processed": 0,
        "total_organizations_processed": 0,
        "stages_completed": 0,
        "stages_failed": 0
    }

    try:
        stages = ["setup", "security", "fetch", "assignment", "processing", "indexing"]
        successful_stages = 0
        failed_stages = 0

        for stage in stages:
            stage_result = pipeline_results.get(stage, {})
            if stage_result.get("status") == "success":
                successful_stages += 1
            elif stage_result.get("status") == "failed":
                failed_stages += 1

        overview["stages_completed"] = successful_stages
        overview["stages_failed"] = failed_stages
        overview["pipeline_success_rate"] = successful_stages / len(stages) if stages else 0

        # Aggregate metrics across stages
        fetch_result = pipeline_results.get("fetch", {})
        processing_result = pipeline_results.get("processing", {})
        indexing_result = pipeline_results.get("indexing", {})

        overview["total_papers_processed"] = (
            fetch_result.get("total_papers_fetched", 0) +
            processing_result.get("total_papers_processed", 0) +
            indexing_result.get("total_papers_indexed", 0)
        ) // 3  # Average across stages

        overview["total_organizations_processed"] = (
            fetch_result.get("organizations_processed", 0) or
            processing_result.get("organizations_processed", 0) or
            indexing_result.get("organizations_processed", 0) or 0
        )

        # Calculate total duration
        stage_timestamps = []
        for stage_result in pipeline_results.values():
            if isinstance(stage_result, dict) and "timestamp" in stage_result:
                try:
                    stage_timestamps.append(datetime.fromisoformat(stage_result["timestamp"]))
                except:
                    pass

        if len(stage_timestamps) >= 2:
            overview["total_duration_seconds"] = (max(stage_timestamps) - min(stage_timestamps)).total_seconds()

    except Exception as e:
        logger.error(f"Failed to calculate pipeline overview: {e}")

    return overview


def _collect_performance_metrics(pipeline_results: Dict[str, Any]) -> Dict[str, Any]:
    """Collect detailed performance metrics from all pipeline stages."""
    metrics = {
        "stage_performance": {},
        "resource_utilization": {},
        "throughput_metrics": {},
        "quality_metrics": {}
    }

    try:
        # Collect stage-specific performance
        for stage_name, stage_result in pipeline_results.items():
            if isinstance(stage_result, dict) and "performance_metrics" in stage_result:
                metrics["stage_performance"][stage_name] = stage_result["performance_metrics"]

        # Aggregate throughput metrics
        fetch_perf = pipeline_results.get("fetch", {}).get("performance_metrics", {})
        processing_perf = pipeline_results.get("processing", {}).get("performance_metrics", {})
        indexing_perf = pipeline_results.get("indexing", {}).get("performance_metrics", {})

        metrics["throughput_metrics"] = {
            "avg_papers_per_second": (
                fetch_perf.get("papers_per_second", 0) +
                processing_perf.get("papers_per_second", 0) +
                indexing_perf.get("papers_per_second", 0)
            ) / 3,
            "total_processing_time": (
                fetch_perf.get("total_duration_seconds", 0) +
                processing_perf.get("total_duration_seconds", 0) +
                indexing_perf.get("total_duration_seconds", 0)
            )
        }

        # Collect system resource metrics
        metrics["resource_utilization"] = performance_monitor.get_system_metrics()

        # Quality metrics
        assignment_result = pipeline_results.get("assignment", {})
        metrics["quality_metrics"] = {
            "assignment_rate": assignment_result.get("assignment_rate", 0),
            "unassigned_papers": assignment_result.get("unassigned_papers", 0),
            "organization_balance_score": _calculate_organization_balance(pipeline_results)
        }

    except Exception as e:
        logger.error(f"Failed to collect performance metrics: {e}")

    return metrics


def _analyze_organization_metrics(pipeline_results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze metrics by organization."""
    org_metrics = {
        "organization_performance": {},
        "load_distribution": {},
        "success_rates": {}
    }

    try:
        # Collect per-organization metrics from different stages
        fetch_orgs = pipeline_results.get("fetch", {}).get("organization_stats", {})
        processing_orgs = pipeline_results.get("processing", {}).get("organization_results", {})
        indexing_orgs = pipeline_results.get("indexing", {}).get("organization_results", {})

        all_org_ids = set(fetch_orgs.keys()) | set(processing_orgs.keys()) | set(indexing_orgs.keys())

        for org_id in all_org_ids:
            org_metrics["organization_performance"][org_id] = {
                "papers_fetched": fetch_orgs.get(org_id, {}).get("papers_fetched", 0),
                "papers_processed": processing_orgs.get(org_id, {}).get("papers_processed", 0),
                "papers_indexed": indexing_orgs.get(org_id, {}).get("papers_indexed", 0),
                "fetch_status": fetch_orgs.get(org_id, {}).get("status"),
                "processing_status": processing_orgs.get(org_id, {}).get("status"),
                "indexing_status": indexing_orgs.get(org_id, {}).get("status")
            }

        # Calculate load distribution
        total_papers = sum(org.get("papers_fetched", 0) for org in org_metrics["organization_performance"].values())
        org_metrics["load_distribution"] = {
            "total_papers": total_papers,
            "organizations_count": len(org_metrics["organization_performance"]),
            "avg_papers_per_org": total_papers / len(org_metrics["organization_performance"]) if org_metrics["organization_performance"] else 0
        }

        # Calculate success rates
        successful_orgs = sum(1 for org in org_metrics["organization_performance"].values()
                            if all(status == "success" for status in [
                                org.get("fetch_status"),
                                org.get("processing_status"),
                                org.get("indexing_status")
                            ] if status is not None))

        org_metrics["success_rates"] = {
            "successful_organizations": successful_orgs,
            "total_organizations": len(org_metrics["organization_performance"]),
            "success_rate": successful_orgs / len(org_metrics["organization_performance"]) if org_metrics["organization_performance"] else 0
        }

    except Exception as e:
        logger.error(f"Failed to analyze organization metrics: {e}")

    return org_metrics


def _analyze_pipeline_errors(pipeline_results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze errors across the pipeline."""
    error_analysis = {
        "total_errors": 0,
        "errors_by_stage": {},
        "error_categories": {},
        "critical_errors": []
    }

    try:
        for stage_name, stage_result in pipeline_results.items():
            if isinstance(stage_result, dict):
                stage_errors = stage_result.get("errors", [])
                error_analysis["total_errors"] += len(stage_errors)
                error_analysis["errors_by_stage"][stage_name] = len(stage_errors)

                # Categorize errors
                for error in stage_errors:
                    category = _categorize_error(error)
                    if category not in error_analysis["error_categories"]:
                        error_analysis["error_categories"][category] = 0
                    error_analysis["error_categories"][category] += 1

                    # Check for critical errors
                    if _is_critical_error(error):
                        error_analysis["critical_errors"].append({
                            "stage": stage_name,
                            "error": error,
                            "category": category
                        })

    except Exception as e:
        logger.error(f"Failed to analyze pipeline errors: {e}")

    return error_analysis


def _generate_recommendations(pipeline_results: Dict[str, Any], config: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on pipeline performance."""
    recommendations = []

    try:
        overview = _calculate_pipeline_overview(pipeline_results)
        error_analysis = _analyze_pipeline_errors(pipeline_results)

        # Performance recommendations
        if overview.get("pipeline_success_rate", 0) < 0.8:
            recommendations.append("Pipeline success rate is below 80%. Consider increasing retry limits and improving error handling.")

        if overview.get("total_duration_seconds", 0) > 3600:  # More than 1 hour
            recommendations.append("Pipeline execution time exceeds 1 hour. Consider increasing distributed workers or optimizing processing.")

        # Error-based recommendations
        if error_analysis.get("total_errors", 0) > 10:
            recommendations.append("High error count detected. Review error logs and consider implementing circuit breakers.")

        if error_analysis.get("critical_errors"):
            recommendations.append(f"{len(error_analysis['critical_errors'])} critical errors found. Immediate investigation required.")

        # Resource recommendations
        throughput = pipeline_results.get("performance_metrics", {}).get("throughput_metrics", {})
        if throughput.get("avg_papers_per_second", 0) < 1:
            recommendations.append("Low throughput detected. Consider scaling distributed workers or optimizing resource allocation.")

    except Exception as e:
        logger.error(f"Failed to generate recommendations: {e}")

    return recommendations


def _check_pipeline_alerts(pipeline_results: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check for pipeline alerts that require attention."""
    alerts = []

    try:
        overview = _calculate_pipeline_overview(pipeline_results)

        # Critical alerts
        if overview.get("pipeline_success_rate", 0) < 0.5:
            alerts.append({
                "level": "critical",
                "message": "Pipeline success rate critically low",
                "metric": "pipeline_success_rate",
                "value": overview.get("pipeline_success_rate", 0),
                "threshold": 0.5
            })

        if overview.get("stages_failed", 0) > 2:
            alerts.append({
                "level": "critical",
                "message": "Multiple pipeline stages failed",
                "metric": "stages_failed",
                "value": overview.get("stages_failed", 0),
                "threshold": 2
            })

        # Warning alerts
        if overview.get("total_duration_seconds", 0) > 7200:  # 2 hours
            alerts.append({
                "level": "warning",
                "message": "Pipeline execution time excessively long",
                "metric": "total_duration_seconds",
                "value": overview.get("total_duration_seconds", 0),
                "threshold": 7200
            })

    except Exception as e:
        logger.error(f"Failed to check pipeline alerts: {e}")

    return alerts


def _create_audit_entries(pipeline_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create audit entries for the pipeline execution."""
    audit_entries = []

    try:
        audit_entries.append({
            "timestamp": datetime.now().isoformat(),
            "action": "enterprise_ingestion_pipeline_completed",
            "details": {
                "stages_executed": list(pipeline_results.keys()),
                "overall_status": "success" if all(
                    stage.get("status") == "success"
                    for stage in pipeline_results.values()
                    if isinstance(stage, dict)
                ) else "failed"
            }
        })

    except Exception as e:
        logger.error(f"Failed to create audit entries: {e}")

    return audit_entries


def _record_monitoring_metrics(monitoring_report: Dict[str, Any], config: Dict[str, Any]):
    """Record monitoring metrics to the performance monitor."""
    try:
        overview = monitoring_report.get("pipeline_overview", {})

        # Record key metrics
        performance_monitor.record_paper_ingestion("pipeline_completion", "success", overview.get("total_papers_processed", 0))

        # Record system health
        system_metrics = monitoring_report.get("performance_metrics", {}).get("resource_utilization", {})
        if system_metrics:
            performance_monitor.update_system_metrics()

    except Exception as e:
        logger.error(f"Failed to record monitoring metrics: {e}")


def _calculate_organization_balance(pipeline_results: Dict[str, Any]) -> float:
    """Calculate how balanced the load is across organizations."""
    try:
        org_metrics = _analyze_organization_metrics(pipeline_results)
        org_performance = org_metrics.get("organization_performance", {})

        if not org_performance:
            return 0.0

        paper_counts = [org.get("papers_fetched", 0) for org in org_performance.values()]
        if not paper_counts:
            return 0.0

        avg_papers = sum(paper_counts) / len(paper_counts)
        if avg_papers == 0:
            return 1.0  # Perfect balance if no papers

        # Calculate coefficient of variation (lower is better balance)
        variance = sum((count - avg_papers) ** 2 for count in paper_counts) / len(paper_counts)
        std_dev = variance ** 0.5
        cv = std_dev / avg_papers if avg_papers > 0 else 0

        # Return balance score (1.0 = perfect balance, 0.0 = poor balance)
        return max(0, 1.0 - cv)

    except Exception:
        return 0.0


def _categorize_error(error: str) -> str:
    """Categorize an error message."""
    error_lower = error.lower()

    if "connection" in error_lower or "network" in error_lower:
        return "connectivity"
    elif "timeout" in error_lower:
        return "timeout"
    elif "permission" in error_lower or "access" in error_lower:
        return "permission"
    elif "memory" in error_lower or "disk" in error_lower:
        return "resource"
    elif "parsing" in error_lower or "format" in error_lower:
        return "data_format"
    else:
        return "general"


def _is_critical_error(error: str) -> bool:
    """Determine if an error is critical."""
    critical_keywords = ["critical", "fatal", "security", "encryption", "database corruption"]
    error_lower = error.lower()

    return any(keyword in error_lower for keyword in critical_keywords)