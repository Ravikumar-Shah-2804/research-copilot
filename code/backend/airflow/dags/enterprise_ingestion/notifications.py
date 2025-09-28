"""
Notification system for enterprise paper ingestion pipeline.
"""

import logging
import os
from typing import Dict, Any
from datetime import datetime

# Add the src directory to the path
sys_path = os.path.join(os.path.dirname(__file__), '../../../src')
if sys_path not in os.sys.path:
    os.sys_path.insert(0, sys_path)

from services.email import EmailService
from services.monitoring import performance_monitor

logger = logging.getLogger(__name__)


def send_pipeline_notification(status: str, result: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send notifications about pipeline completion.

    :param status: Pipeline status (success, failed, skipped)
    :param result: Pipeline result data
    :param config: Enterprise configuration
    :returns: Notification result
    """
    logger.info(f"Sending pipeline notification for status: {status}")

    notification_result = {
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "notification_type": "pipeline_completion",
        "recipients_notified": 0,
        "channels_used": [],
        "errors": []
    }

    try:
        # Determine notification priority and content
        if status == "success":
            notification_result["priority"] = "normal"
            notification_result["subject"] = "Enterprise Paper Ingestion Pipeline - Success"
            notification_result["message"] = _format_success_notification(result)
        elif status == "failed":
            notification_result["priority"] = "high"
            notification_result["subject"] = "Enterprise Paper Ingestion Pipeline - FAILED"
            notification_result["message"] = _format_failure_notification(result)
        elif status == "skipped":
            notification_result["priority"] = "low"
            notification_result["subject"] = "Enterprise Paper Ingestion Pipeline - Skipped"
            notification_result["message"] = _format_skipped_notification(result)
        else:
            notification_result["priority"] = "normal"
            notification_result["subject"] = f"Enterprise Paper Ingestion Pipeline - {status.title()}"
            notification_result["message"] = f"Pipeline completed with status: {status}"

        # Send email notifications
        email_result = _send_email_notification(notification_result, config)
        if email_result["success"]:
            notification_result["channels_used"].append("email")
            notification_result["recipients_notified"] += email_result.get("recipients", 0)

        # Send monitoring alerts for failures
        if status == "failed":
            alert_result = _send_monitoring_alert(notification_result, result, config)
            if alert_result["success"]:
                notification_result["channels_used"].append("monitoring_alert")

        # Log notification metrics
        performance_monitor.record_request(
            endpoint="pipeline_notification",
            method="POST",
            status_code=200 if notification_result["channels_used"] else 500,
            duration=0.0,
            user_type="system"
        )

        notification_result["status"] = "success" if notification_result["channels_used"] else "partial_success"
        logger.info(f"Pipeline notification sent via {len(notification_result['channels_used'])} channels")

        return notification_result

    except Exception as e:
        error_msg = f"Pipeline notification failed: {str(e)}"
        notification_result["status"] = "failed"
        notification_result["errors"].append(error_msg)
        logger.error(error_msg)
        return notification_result


def _format_success_notification(result: Dict[str, Any]) -> str:
    """Format success notification message."""
    try:
        overview = result.get("pipeline_overview", {})
        metrics = result.get("performance_metrics", {})

        message = f"""
Enterprise Paper Ingestion Pipeline completed successfully!

📊 Pipeline Overview:
• Total Papers Processed: {overview.get('total_papers_processed', 0)}
• Organizations Processed: {overview.get('total_organizations_processed', 0)}
• Pipeline Success Rate: {overview.get('pipeline_success_rate', 0):.1%}
• Total Duration: {overview.get('total_duration_seconds', 0):.1f} seconds

⚡ Performance Metrics:
• Average Papers/Second: {metrics.get('throughput_metrics', {}).get('avg_papers_per_second', 0):.2f}
• System CPU Usage: {metrics.get('resource_utilization', {}).get('cpu_percent', 0):.1f}%
• Memory Usage: {metrics.get('resource_utilization', {}).get('memory_percent', 0):.1f}%

✅ All pipeline stages completed successfully.
"""

        return message.strip()

    except Exception as e:
        logger.error(f"Failed to format success notification: {e}")
        return "Enterprise Paper Ingestion Pipeline completed successfully!"


def _format_failure_notification(result: Dict[str, Any]) -> str:
    """Format failure notification message."""
    try:
        overview = result.get("pipeline_overview", {})
        error_analysis = result.get("error_analysis", {})

        message = f"""
🚨 Enterprise Paper Ingestion Pipeline FAILED!

❌ Pipeline Status:
• Stages Completed: {overview.get('stages_completed', 0)}
• Stages Failed: {overview.get('stages_failed', 0)}
• Total Errors: {error_analysis.get('total_errors', 0)}
• Critical Errors: {len(error_analysis.get('critical_errors', []))}

⚠️ Error Summary:
"""

        # Add error details
        errors_by_stage = error_analysis.get("errors_by_stage", {})
        for stage, count in errors_by_stage.items():
            if count > 0:
                message += f"• {stage.title()}: {count} errors\n"

        # Add critical errors
        critical_errors = error_analysis.get("critical_errors", [])
        if critical_errors:
            message += "\n🚨 Critical Errors:\n"
            for error in critical_errors[:5]:  # Limit to first 5
                message += f"• {error.get('stage', 'unknown')}: {error.get('error', 'unknown error')[:100]}...\n"

        message += "\n🔍 Please check the pipeline logs for detailed error information."

        return message.strip()

    except Exception as e:
        logger.error(f"Failed to format failure notification: {e}")
        return "🚨 Enterprise Paper Ingestion Pipeline FAILED! Please check logs for details."


def _format_skipped_notification(result: Dict[str, Any]) -> str:
    """Format skipped notification message."""
    try:
        message = f"""
⏭️ Enterprise Paper Ingestion Pipeline was SKIPPED

Reason: {result.get('message', 'No active organizations available for processing')}

This is normal behavior when no organizations require paper ingestion at this time.
"""

        return message.strip()

    except Exception as e:
        logger.error(f"Failed to format skipped notification: {e}")
        return "Enterprise Paper Ingestion Pipeline was skipped."


def _send_email_notification(notification_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Send email notification."""
    email_result = {"success": False, "recipients": 0, "errors": []}

    try:
        # Get email configuration
        email_recipients = os.getenv("PIPELINE_NOTIFICATION_EMAILS", "").split(",")
        email_recipients = [email.strip() for email in email_recipients if email.strip()]

        if not email_recipients:
            logger.warning("No email recipients configured for pipeline notifications")
            return email_result

        # Initialize email service
        email_service = EmailService()

        # Send notification email
        email_service.send_email(
            to=email_recipients,
            subject=notification_data["subject"],
            body=notification_data["message"],
            priority=notification_data.get("priority", "normal")
        )

        email_result["success"] = True
        email_result["recipients"] = len(email_recipients)
        logger.info(f"Email notification sent to {len(email_recipients)} recipients")

    except Exception as e:
        error_msg = f"Email notification failed: {str(e)}"
        email_result["errors"].append(error_msg)
        logger.error(error_msg)

    return email_result


def _send_monitoring_alert(notification_data: Dict[str, Any], result: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Send monitoring alert for pipeline failures."""
    alert_result = {"success": False, "alerts_triggered": 0, "errors": []}

    try:
        # Record critical error in monitoring system
        performance_monitor.record_request(
            endpoint="pipeline_failure",
            method="POST",
            status_code=500,
            duration=result.get("pipeline_overview", {}).get("total_duration_seconds", 0),
            user_type="system"
        )

        # Update service health status
        performance_monitor.update_service_health("ingestion_pipeline", False)

        # In a real implementation, you might integrate with external monitoring systems
        # like PagerDuty, Slack, or other alerting services

        alert_result["success"] = True
        alert_result["alerts_triggered"] = 1
        logger.info("Monitoring alert sent for pipeline failure")

    except Exception as e:
        error_msg = f"Monitoring alert failed: {str(e)}"
        alert_result["errors"].append(error_msg)
        logger.error(error_msg)

    return alert_result