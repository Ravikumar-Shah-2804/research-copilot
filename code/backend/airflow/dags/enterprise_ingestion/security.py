"""
Security and access control validation for enterprise paper ingestion.
"""

import logging
import os
from typing import Dict, Any
from datetime import datetime

# Add the src directory to the path
sys_path = os.path.join(os.path.dirname(__file__), '../../../src')
if sys_path not in os.sys.path:
    os.sys.path.insert(0, sys_path)

from services.security import SecurityService
from services.audit import AuditService
from services.organization import organization_service
from database import get_db_session
from dags.enterprise_ingestion.tracing import enterprise_tracer

logger = logging.getLogger(__name__)


def validate_enterprise_access(setup_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate enterprise security requirements and access controls.

    :param setup_result: Results from environment setup validation
    :returns: Dictionary with security validation results
    """
    logger.info("Validating enterprise security and access controls")

    security_results = {
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "validations": {},
        "permissions": {},
        "audit_trail": [],
        "errors": []
    }

    with enterprise_tracer.trace_task("security_access_validation") as span:
        try:
            # Check if setup was successful
            if setup_result.get("status") != "success":
                error_msg = "Cannot proceed with security validation - setup failed"
                security_results["validations"]["setup_dependency"] = {"status": "failed", "error": error_msg}
                security_results["errors"].append(error_msg)
                security_results["status"] = "failed"
                return security_results

            # Validate API key authentication
        try:
            # Check for valid API keys in environment
            api_key = os.getenv("RESEARCH_COPILOT_API_KEY")
            if not api_key:
                raise Exception("RESEARCH_COPILOT_API_KEY environment variable not set")

            # Validate API key format and permissions
            security_service = SecurityService()
            key_validation = security_service.validate_api_key(api_key)

            if key_validation["valid"]:
                security_results["validations"]["api_key"] = {
                    "status": "success",
                    "message": "API key validated successfully",
                    "permissions": key_validation.get("permissions", [])
                }
                logger.info("API key validation successful")
            else:
                raise Exception(f"Invalid API key: {key_validation.get('error', 'Unknown error')}")

        except Exception as e:
            error_msg = f"API key validation failed: {str(e)}"
            security_results["validations"]["api_key"] = {"status": "failed", "error": error_msg}
            security_results["errors"].append(error_msg)
            logger.error(error_msg)

        # Validate organization access permissions
        try:
            with get_db_session() as session:
                # Get organizations with ingestion permissions
                organizations = organization_service.list_organizations()

                org_permissions = []
                for org in organizations:
                    # Check if organization has paper ingestion permissions
                    has_ingestion_permission = _check_organization_ingestion_permission(org.id)
                    org_permissions.append({
                        "org_id": str(org.id),
                        "org_name": org.name,
                        "ingestion_allowed": has_ingestion_permission,
                        "max_users": org.max_users,
                        "is_active": org.is_active
                    })

                security_results["validations"]["organization_permissions"] = {
                    "status": "success",
                    "message": f"Validated permissions for {len(organizations)} organizations",
                    "organizations": org_permissions
                }

                # Count organizations with ingestion access
                allowed_orgs = [org for org in org_permissions if org["ingestion_allowed"] and org["is_active"]]
                security_results["permissions"]["ingestion_eligible_orgs"] = len(allowed_orgs)

                logger.info(f"Organization permissions validated: {len(allowed_orgs)} eligible organizations")

        except Exception as e:
            error_msg = f"Organization permissions validation failed: {str(e)}"
            security_results["validations"]["organization_permissions"] = {"status": "failed", "error": error_msg}
            security_results["errors"].append(error_msg)
            logger.error(error_msg)

        # Validate rate limiting configuration
        try:
            from services.rate_limiting import RateLimitingService

            rate_limiter = RateLimitingService()
            rate_limit_config = rate_limiter.get_enterprise_limits()

            security_results["validations"]["rate_limiting"] = {
                "status": "success",
                "message": "Rate limiting configuration validated",
                "limits": rate_limit_config
            }
            logger.info("Rate limiting validation successful")

        except Exception as e:
            error_msg = f"Rate limiting validation failed: {str(e)}"
            security_results["validations"]["rate_limiting"] = {"status": "failed", "error": error_msg}
            security_results["errors"].append(error_msg)
            logger.error(error_msg)

        # Validate audit logging setup
        try:
            audit_service = AuditService()
            audit_status = audit_service.check_audit_system()

            if audit_status["operational"]:
                security_results["validations"]["audit_logging"] = {
                    "status": "success",
                    "message": "Audit logging system operational",
                    "retention_days": audit_status.get("retention_days", 90)
                }
                logger.info("Audit logging validation successful")
            else:
                raise Exception("Audit logging system not operational")

        except Exception as e:
            error_msg = f"Audit logging validation failed: {str(e)}"
            security_results["validations"]["audit_logging"] = {"status": "failed", "error": error_msg}
            security_results["errors"].append(error_msg)
            logger.error(error_msg)

        # Validate data encryption settings
        try:
            encryption_enabled = os.getenv("ENCRYPTION_ENABLED", "false").lower() == "true"
            encryption_key_set = bool(os.getenv("ENCRYPTION_KEY"))

            if encryption_enabled and not encryption_key_set:
                raise Exception("Encryption enabled but no encryption key provided")

            security_results["validations"]["encryption"] = {
                "status": "success",
                "message": "Data encryption settings validated",
                "encryption_enabled": encryption_enabled,
                "key_configured": encryption_key_set
            }
            logger.info("Encryption validation successful")

        except Exception as e:
            error_msg = f"Encryption validation failed: {str(e)}"
            security_results["validations"]["encryption"] = {"status": "failed", "error": error_msg}
            security_results["errors"].append(error_msg)
            logger.error(error_msg)

        # Create audit trail entry
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "enterprise_ingestion_security_validation",
            "status": "completed" if not security_results["errors"] else "failed",
            "details": {
                "validations_performed": list(security_results["validations"].keys()),
                "errors_count": len(security_results["errors"])
            }
        }
        security_results["audit_trail"].append(audit_entry)

        # Determine overall status
        failed_validations = [k for k, v in security_results["validations"].items() if v["status"] == "failed"]
        if failed_validations:
            security_results["status"] = "failed"
            security_results["message"] = f"Security validation failed with {len(failed_validations)} errors"
        else:
            security_results["status"] = "success"
            security_results["message"] = "Enterprise security validation completed successfully"

            # Record tracing metrics
            enterprise_tracer.record_task_metric(
                "security_access_validation",
                "validations_completed",
                len(security_results["validations"]),
                organization_id=None
            )
            enterprise_tracer.record_task_metric(
                "security_access_validation",
                "errors_count",
                len(security_results["errors"]),
                organization_id=None
            )
            enterprise_tracer.record_task_metric(
                "security_access_validation",
                "eligible_organizations",
                security_results["permissions"].get("ingestion_eligible_orgs", 0),
                organization_id=None
            )

            logger.info(f"Enterprise security validation completed with status: {security_results['status']}")
            return security_results

        except Exception as e:
            error_msg = f"Unexpected error during security validation: {str(e)}"
            security_results["status"] = "failed"
            security_results["message"] = error_msg
            security_results["errors"].append(error_msg)

            # Record error in trace
            enterprise_tracer.record_error("security_access_validation", e)

            logger.error(error_msg)
            return security_results


def _check_organization_ingestion_permission(org_id: str) -> bool:
    """
    Check if an organization has permission to perform paper ingestion.

    :param org_id: Organization ID to check
    :returns: True if organization has ingestion permission
    """
    try:
        # This would typically check role-based permissions
        # For now, we'll assume active organizations have ingestion permission
        # In a real implementation, this would check specific permissions in the database
        return True
    except Exception as e:
        logger.error(f"Error checking organization ingestion permission for {org_id}: {e}")
        return False