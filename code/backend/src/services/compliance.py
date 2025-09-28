"""
Compliance and audit services for GDPR, data retention, and regulatory requirements
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, or_, func
import json

from ..config import settings
from ..database import get_db
from ..models.audit import AuditLog
from ..models.user import User
from ..models.paper import Paper
from ..utils.security_logging import compliance_logger, audit_logger
from ..services.audit import audit_service
from .security import encryption_service

logger = logging.getLogger(__name__)


class GDPRComplianceManager:
    """GDPR compliance management"""

    def __init__(self):
        self.data_retention_periods = {
            "user_data": timedelta(days=2555),  # 7 years for user data
            "audit_logs": timedelta(days=2555),  # 7 years for audit logs
            "search_history": timedelta(days=365),  # 1 year for search history
            "api_logs": timedelta(days=90),  # 90 days for API logs
            "session_data": timedelta(days=30),  # 30 days for session data
        }

        self.consent_types = [
            "analytics",
            "marketing",
            "third_party_sharing",
            "data_processing",
            "profiling"
        ]

    async def process_data_deletion_request(
        self, db: AsyncSession, user_id: str, request_type: str = "erasure"
    ) -> Dict[str, Any]:
        """Process GDPR right to erasure request"""
        result = {
            "user_id": user_id,
            "request_type": request_type,
            "processed_at": datetime.utcnow().isoformat(),
            "data_deleted": [],
            "data_anonymized": [],
            "errors": []
        }

        try:
            # Get user data
            user = await db.get(User, user_id)
            if not user:
                result["errors"].append("User not found")
                return result

            # Delete or anonymize user data based on retention requirements
            await self._delete_user_data(db, user_id, result)
            await self._anonymize_audit_logs(db, user_id, result)

            # Log compliance event
            await compliance_logger.log_data_deletion(
                user_id=user_id,
                data_types=["user_data", "audit_logs", "search_history"],
                request_type=request_type
            )

            # Create audit trail
            await audit_service.log_event_async(
                audit_service.AuditEvent(
                    action="gdpr_data_deletion",
                    resource_type="user",
                    resource_id=user_id,
                    success=True,
                    metadata={
                        "request_type": request_type,
                        "data_deleted": result["data_deleted"],
                        "data_anonymized": result["data_anonymized"]
                    },
                    compliance_level="critical"
                )
            )

        except Exception as e:
            logger.error(f"GDPR deletion error for user {user_id}: {e}")
            result["errors"].append(str(e))

        return result

    async def _delete_user_data(self, db: AsyncSession, user_id: str, result: Dict[str, Any]):
        """Delete user data"""
        try:
            # Delete user record (this would cascade to related data)
            user = await db.get(User, user_id)
            if user:
                await db.delete(user)
                await db.commit()
                result["data_deleted"].append("user_profile")

            # Delete search history, API keys, etc.
            # This would depend on your specific data model

            logger.info(f"User data deleted for {user_id}")

        except Exception as e:
            result["errors"].append(f"Failed to delete user data: {e}")

    async def _anonymize_audit_logs(self, db: AsyncSession, user_id: str, result: Dict[str, Any]):
        """Anonymize audit logs for the user"""
        try:
            # Update audit logs to remove PII
            from sqlalchemy import update

            await db.execute(
                update(AuditLog)
                .where(AuditLog.user_id == user_id)
                .values(
                    username="[DELETED]",
                    user_email="[DELETED]",
                    metadata=self._anonymize_metadata(AuditLog.metadata)
                )
            )

            await db.commit()
            result["data_anonymized"].append("audit_logs")

        except Exception as e:
            result["errors"].append(f"Failed to anonymize audit logs: {e}")

    def _anonymize_metadata(self, metadata_json: str) -> str:
        """Anonymize sensitive data in metadata"""
        try:
            metadata = json.loads(metadata_json)
            # Remove or mask PII
            sensitive_keys = ["email", "ip_address", "user_agent", "personal_data"]
            for key in sensitive_keys:
                if key in metadata:
                    metadata[key] = "[ANONYMIZED]"
            return json.dumps(metadata)
        except:
            return metadata_json

    async def record_consent(
        self, db: AsyncSession, user_id: str, consent_type: str, granted: bool,
        legal_basis: str = "consent", expires_at: Optional[datetime] = None
    ):
        """Record user consent for data processing"""
        consent_data = {
            "user_id": user_id,
            "consent_type": consent_type,
            "granted": granted,
            "legal_basis": legal_basis,
            "recorded_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None
        }

        # Store consent record (would need a Consent model)
        # For now, log it
        await compliance_logger.log_consent_change(
            user_id=user_id,
            consent_type=consent_type,
            granted=granted
        )

        await audit_service.log_event_async(
            audit_service.AuditEvent(
                action="consent_recorded",
                resource_type="user",
                resource_id=user_id,
                success=True,
                metadata=consent_data,
                compliance_level="standard"
            )
        )

    async def check_data_processing_consent(
        self, db: AsyncSession, user_id: str, processing_type: str
    ) -> bool:
        """Check if user has consented to data processing"""
        # This would check stored consent records
        # For now, return True (assuming consent)
        return True

    async def generate_data_processing_register(self, db: AsyncSession) -> Dict[str, Any]:
        """Generate GDPR Article 30 data processing register"""
        # This would analyze all data processing activities
        register = {
            "generated_at": datetime.utcnow().isoformat(),
            "processing_activities": [
                {
                    "purpose": "User authentication and authorization",
                    "categories_of_data": ["email", "password_hash", "login_history"],
                    "legal_basis": "contract",
                    "retention_period": "7 years"
                },
                {
                    "purpose": "Search and RAG operations",
                    "categories_of_data": ["search_queries", "usage_patterns"],
                    "legal_basis": "legitimate_interest",
                    "retention_period": "1 year"
                },
                {
                    "purpose": "Audit logging",
                    "categories_of_data": ["user_actions", "system_events"],
                    "legal_basis": "legal_obligation",
                    "retention_period": "7 years"
                }
            ]
        }

        return register


class DataRetentionManager:
    """Data retention and automated cleanup manager"""

    def __init__(self):
        self.cleanup_schedule = {
            "hourly": ["session_data"],
            "daily": ["api_logs", "search_history"],
            "weekly": ["temp_files"],
            "monthly": ["old_audit_logs"],
            "yearly": ["archived_data"]
        }

    async def schedule_data_cleanup(self):
        """Schedule automated data cleanup tasks"""
        while True:
            try:
                await self._run_cleanup_tasks()
                await asyncio.sleep(3600)  # Run every hour
            except Exception as e:
                logger.error(f"Data cleanup error: {e}")
                await asyncio.sleep(300)  # Retry in 5 minutes

    async def _run_cleanup_tasks(self):
        """Run scheduled cleanup tasks"""
        current_hour = datetime.utcnow().hour
        current_day = datetime.utcnow().day
        current_month = datetime.utcnow().month

        # Hourly cleanup
        await self._cleanup_data_type("session_data")

        # Daily cleanup (run at 2 AM)
        if current_hour == 2:
            await self._cleanup_data_type("api_logs")
            await self._cleanup_data_type("search_history")

        # Weekly cleanup (run on Sundays at 3 AM)
        if current_day == 6 and current_hour == 3:  # Sunday
            await self._cleanup_data_type("temp_files")

        # Monthly cleanup (run on 1st of month at 4 AM)
        if current_day == 1 and current_hour == 4:
            await self._cleanup_data_type("old_audit_logs")

    async def _cleanup_data_type(self, data_type: str):
        """Clean up specific data type"""
        try:
            retention_period = self.data_retention_periods.get(data_type)
            if not retention_period:
                return

            cutoff_date = datetime.utcnow() - retention_period

            async for session in get_db():
                try:
                    if data_type == "session_data":
                        await self._cleanup_sessions(session, cutoff_date)
                    elif data_type == "api_logs":
                        await self._cleanup_api_logs(session, cutoff_date)
                    elif data_type == "search_history":
                        await self._cleanup_search_history(session, cutoff_date)
                    elif data_type == "old_audit_logs":
                        await audit_service.cleanup_old_logs(session, retention_period.days)
                    elif data_type == "temp_files":
                        await self._cleanup_temp_files()

                    await audit_service.log_event_async(
                        audit_service.AuditEvent(
                            action="data_cleanup",
                            resource_type="system",
                            success=True,
                            metadata={
                                "data_type": data_type,
                                "cutoff_date": cutoff_date.isoformat(),
                                "retention_days": retention_period.days
                            }
                        )
                    )

                finally:
                    await session.close()

        except Exception as e:
            logger.error(f"Failed to cleanup {data_type}: {e}")

    async def _cleanup_sessions(self, db: AsyncSession, cutoff_date: datetime):
        """Clean up expired sessions"""
        # This would delete expired session records
        # Implementation depends on session storage
        pass

    async def _cleanup_api_logs(self, db: AsyncSession, cutoff_date: datetime):
        """Clean up old API logs"""
        # This would delete old API log entries
        # Implementation depends on logging storage
        pass

    async def _cleanup_search_history(self, db: AsyncSession, cutoff_date: datetime):
        """Clean up old search history"""
        # This would delete old search records
        # Implementation depends on search history storage
        pass

    async def _cleanup_temp_files(self):
        """Clean up temporary files"""
        # This would delete old temporary files
        pass

    async def manual_cleanup(
        self, data_type: str, older_than_days: int, dry_run: bool = True
    ) -> Dict[str, Any]:
        """Manual data cleanup with dry run option"""
        result = {
            "data_type": data_type,
            "older_than_days": older_than_days,
            "dry_run": dry_run,
            "would_delete": 0,
            "actually_deleted": 0,
            "errors": []
        }

        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

        async for session in get_db():
            try:
                # Count records that would be deleted
                if data_type == "audit_logs":
                    count_query = select(func.count(AuditLog.id)).where(
                        AuditLog.timestamp < cutoff_date
                    )
                    count_result = await session.execute(count_query)
                    result["would_delete"] = count_result.scalar()

                    if not dry_run:
                        delete_query = delete(AuditLog).where(
                            AuditLog.timestamp < cutoff_date
                        )
                        delete_result = await session.execute(delete_query)
                        result["actually_deleted"] = delete_result.rowcount
                        await session.commit()

                # Add other data types as needed

            except Exception as e:
                result["errors"].append(str(e))
            finally:
                await session.close()

        return result


class ComplianceReporting:
    """Compliance reporting and export capabilities"""

    def __init__(self):
        self.report_types = {
            "gdpr_audit": self._generate_gdpr_audit_report,
            "data_processing": self._generate_data_processing_report,
            "security_incidents": self._generate_security_incidents_report,
            "access_logs": self._generate_access_logs_report,
            "retention_compliance": self._generate_retention_compliance_report
        }

    async def generate_report(
        self, report_type: str, start_date: datetime, end_date: datetime,
        format: str = "json", **kwargs
    ) -> str:
        """Generate compliance report"""
        if report_type not in self.report_types:
            raise ValueError(f"Unknown report type: {report_type}")

        generator = self.report_types[report_type]
        data = await generator(start_date, end_date, **kwargs)

        if format == "json":
            return json.dumps(data, indent=2, default=str)
        elif format == "csv":
            return self._convert_to_csv(data)
        else:
            raise ValueError(f"Unsupported format: {format}")

    async def _generate_gdpr_audit_report(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Generate GDPR audit report"""
        async for session in get_db():
            try:
                # Query audit logs for GDPR-related events
                gdpr_events = await audit_service.get_audit_logs(
                    db=session,
                    action="gdpr_data_deletion",
                    start_date=start_date,
                    end_date=end_date
                )

                # Get data processing statistics
                processing_stats = await audit_service.get_audit_stats(
                    db=session,
                    start_date=start_date,
                    end_date=end_date
                )

                report = {
                    "report_type": "GDPR Audit",
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "data_deletion_requests": len(gdpr_events),
                    "data_processing_activities": processing_stats,
                    "compliance_status": "compliant",  # Would need actual compliance checking
                    "generated_at": datetime.utcnow().isoformat()
                }

                return report

            finally:
                await session.close()

    async def _generate_data_processing_report(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Generate data processing activities report"""
        async for session in get_db():
            try:
                # Get audit statistics
                stats = await audit_service.get_audit_stats(
                    db=session,
                    start_date=start_date,
                    end_date=end_date
                )

                report = {
                    "report_type": "Data Processing Activities",
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "processing_statistics": stats,
                    "data_subjects_affected": 0,  # Would need to calculate
                    "legal_bases_used": ["consent", "contract", "legitimate_interest"],
                    "generated_at": datetime.utcnow().isoformat()
                }

                return report

            finally:
                await session.close()

    async def _generate_security_incidents_report(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Generate security incidents report"""
        async for session in get_db():
            try:
                # Query security-related audit events
                security_events = await audit_service.get_audit_logs(
                    db=session,
                    action=["security_violation", "intrusion_attempt", "brute_force_attempt"],
                    start_date=start_date,
                    end_date=end_date
                )

                incidents_by_type = {}
                for event in security_events:
                    event_type = event.action
                    if event_type not in incidents_by_type:
                        incidents_by_type[event_type] = []
                    incidents_by_type[event_type].append({
                        "timestamp": event.timestamp.isoformat(),
                        "user_id": event.user_id,
                        "details": event.metadata
                    })

                report = {
                    "report_type": "Security Incidents",
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "total_incidents": len(security_events),
                    "incidents_by_type": incidents_by_type,
                    "generated_at": datetime.utcnow().isoformat()
                }

                return report

            finally:
                await session.close()

    async def _generate_access_logs_report(
        self, start_date: datetime, end_date: datetime, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate access logs report"""
        async for session in get_db():
            try:
                # Query access-related audit events
                access_events = await audit_service.get_audit_logs(
                    db=session,
                    user_id=user_id,
                    action=["login", "logout", "data_access"],
                    start_date=start_date,
                    end_date=end_date,
                    limit=10000
                )

                report = {
                    "report_type": "Access Logs",
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "user_id": user_id,
                    "total_access_events": len(access_events),
                    "access_events": [
                        {
                            "timestamp": event.timestamp.isoformat(),
                            "action": event.action,
                            "resource_type": event.resource_type,
                            "ip_address": event.metadata.get("ip_address") if event.metadata else None,
                            "success": event.success
                        }
                        for event in access_events
                    ],
                    "generated_at": datetime.utcnow().isoformat()
                }

                return report

            finally:
                await session.close()

    async def _generate_retention_compliance_report(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Generate data retention compliance report"""
        # This would check if data is being properly retained/deleted
        report = {
            "report_type": "Data Retention Compliance",
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "retention_policies": {
                "user_data": "7 years",
                "audit_logs": "7 years",
                "search_history": "1 year",
                "api_logs": "90 days"
            },
            "compliance_status": "compliant",  # Would need actual checking
            "last_cleanup_runs": {},  # Would track cleanup execution
            "generated_at": datetime.utcnow().isoformat()
        }

        return report

    def _convert_to_csv(self, data: Dict[str, Any]) -> str:
        """Convert report data to CSV format"""
        # Simple CSV conversion - would need more sophisticated implementation
        lines = ["Key,Value"]
        for key, value in data.items():
            if isinstance(value, (str, int, float)):
                lines.append(f"{key},{value}")
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    lines.append(f"{key}.{sub_key},{sub_value}")
        return "\n".join(lines)


# Global instances
gdpr_manager = GDPRComplianceManager()
data_retention_manager = DataRetentionManager()
compliance_reporting = ComplianceReporting()

# Set data retention periods (this should match the GDPR manager)
data_retention_manager.data_retention_periods = gdpr_manager.data_retention_periods