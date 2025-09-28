"""
Audit log router for compliance and monitoring
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..services.auth import get_current_active_user
from ..services.audit import audit_service
from ..models.audit import AuditLog

router = APIRouter()


@router.get("/logs", response_model=List[dict])
async def get_audit_logs(
    user_id: Optional[UUID] = None,
    organization_id: Optional[UUID] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    success: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get audit logs with filtering"""
    # Permission check: users can see their own logs, admins can see all
    if not current_user.is_superuser:
        if user_id and user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Cannot view other users' audit logs"
            )
        if organization_id and current_user.organization_id != organization_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot view other organizations' audit logs"
            )
        # If no specific filters, limit to user's organization
        if not user_id and not organization_id:
            organization_id = current_user.organization_id

    try:
        logs = await audit_service.get_audit_logs(
            db=db,
            user_id=user_id,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            start_date=start_date,
            end_date=end_date,
            success=success,
            limit=limit,
            offset=offset
        )

        # Convert to dict format for response
        return [{
            "id": str(log.id),
            "timestamp": log.timestamp.isoformat(),
            "user_id": str(log.user_id) if log.user_id else None,
            "username": log.username,
            "organization_id": str(log.organization_id) if log.organization_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            "success": log.success,
            "error_message": log.error_message,
            "correlation_id": str(log.correlation_id) if log.correlation_id else None,
            "metadata": log.metadata
        } for log in logs]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit logs: {str(e)}")


@router.get("/stats")
async def get_audit_stats(
    organization_id: Optional[UUID] = None,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get audit statistics"""
    # Permission check
    if not current_user.is_superuser and organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot view other organizations' audit stats"
        )

    try:
        return await audit_service.get_audit_stats(
            db=db,
            organization_id=organization_id,
            days=days
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get audit stats: {str(e)}")


@router.get("/export")
async def export_audit_logs(
    start_date: datetime = Query(..., description="Start date for export"),
    end_date: datetime = Query(..., description="End date for export"),
    organization_id: Optional[UUID] = None,
    format: str = Query("json", regex="^(json|csv)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Export audit logs for compliance"""
    # Permission check: only superusers can export
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can export audit logs"
        )

    try:
        data = await audit_service.export_audit_logs(
            db=db,
            start_date=start_date,
            end_date=end_date,
            organization_id=organization_id,
            format=format
        )

        # Return as streaming response
        def generate():
            yield data

        return StreamingResponse(
            generate(),
            media_type="application/json" if format == "json" else "text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=audit_logs_{start_date.date()}_{end_date.date()}.{format}"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export audit logs: {str(e)}")


@router.post("/cleanup")
async def cleanup_audit_logs(
    days_to_keep: int = Query(365, ge=30, le=2555),  # Min 30 days, max ~7 years
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Clean up old audit logs (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Only superusers can cleanup audit logs"
        )

    try:
        deleted_count = await audit_service.cleanup_old_logs(db, days_to_keep)
        return {
            "message": f"Cleaned up {deleted_count} audit log entries older than {days_to_keep} days"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup audit logs: {str(e)}")


@router.get("/actions")
async def get_audit_actions():
    """Get list of available audit actions"""
    from ..models.audit import AUDIT_ACTIONS
    return AUDIT_ACTIONS


@router.get("/user/{user_id}/activity")
async def get_user_activity(
    user_id: UUID,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get activity summary for a specific user"""
    # Permission check
    if not current_user.is_superuser and user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Cannot view other users' activity"
        )

    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get user's recent activity
        logs = await audit_service.get_audit_logs(
            db=db,
            user_id=user_id,
            start_date=start_date,
            limit=1000
        )

        # Aggregate activity
        activity_summary = {
            "user_id": str(user_id),
            "period_days": days,
            "total_actions": len(logs),
            "actions_by_type": {},
            "recent_actions": []
        }

        for log in logs[:50]:  # Last 50 actions
            action_type = log.action
            if action_type not in activity_summary["actions_by_type"]:
                activity_summary["actions_by_type"][action_type] = 0
            activity_summary["actions_by_type"][action_type] += 1

            activity_summary["recent_actions"].append({
                "timestamp": log.timestamp.isoformat(),
                "action": log.action,
                "resource_type": log.resource_type,
                "success": log.success
            })

        return activity_summary

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user activity: {str(e)}")


@router.get("/compliance/report")
async def generate_compliance_report(
    start_date: datetime = Query(..., description="Start date for compliance report"),
    end_date: datetime = Query(..., description="End date for compliance report"),
    organization_id: Optional[UUID] = None,
    report_type: str = Query("summary", regex="^(summary|detailed|security)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate compliance report for audit trails"""
    # Only superusers can generate compliance reports
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can generate compliance reports"
        )

    try:
        # Get audit statistics
        audit_stats = await audit_service.get_audit_stats(
            db=db,
            organization_id=organization_id,
            days=(end_date - start_date).days
        )

        # Get security events
        security_logs = await audit_service.get_audit_logs(
            db=db,
            organization_id=organization_id,
            action="security_violation",
            start_date=start_date,
            end_date=end_date,
            limit=1000
        )

        # Get failed authentication attempts
        failed_auth_logs = await audit_service.get_audit_logs(
            db=db,
            organization_id=organization_id,
            action="login_failed",
            start_date=start_date,
            end_date=end_date,
            limit=1000
        )

        compliance_report = {
            "report_type": report_type,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "organization_id": str(organization_id) if organization_id else None,
            "generated_at": datetime.utcnow().isoformat(),
            "generated_by": str(current_user.id),
            "summary": {
                "total_audit_events": audit_stats["total_events"],
                "security_events_count": len(security_logs),
                "failed_auth_attempts": len(failed_auth_logs),
                "success_rate": audit_stats["success_stats"].get(True, 0) / max(audit_stats["total_events"], 1)
            }
        }

        if report_type == "detailed":
            compliance_report["detailed"] = {
                "security_events": [{
                    "timestamp": log.timestamp.isoformat(),
                    "user_id": str(log.user_id) if log.user_id else None,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "metadata": log.metadata
                } for log in security_logs],
                "failed_authentications": [{
                    "timestamp": log.timestamp.isoformat(),
                    "username": log.username,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "error_message": log.error_message
                } for log in failed_auth_logs],
                "audit_statistics": audit_stats
            }

        elif report_type == "security":
            compliance_report["security_analysis"] = {
                "unique_ips_with_failures": len(set(
                    log.ip_address for log in failed_auth_logs if log.ip_address
                )),
                "most_common_failure_reasons": {},
                "suspicious_patterns": [],  # Could implement pattern detection
                "recommendations": [
                    "Implement IP-based rate limiting" if len(failed_auth_logs) > 10 else None,
                    "Review user access patterns" if len(security_logs) > 5 else None,
                    "Enable multi-factor authentication" if len(failed_auth_logs) > 20 else None
                ]
            }
            # Remove None values
            compliance_report["security_analysis"]["recommendations"] = [
                rec for rec in compliance_report["security_analysis"]["recommendations"] if rec
            ]

        return compliance_report

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate compliance report: {str(e)}")


@router.get("/compliance/data-retention")
async def check_data_retention_compliance(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Check data retention compliance"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can check data retention compliance"
        )

    try:
        # Check for logs older than retention periods
        from datetime import timedelta

        retention_periods = {
            "standard": 365,  # 1 year
            "sensitive": 2555,  # 7 years
            "critical": 2555   # 7 years
        }

        compliance_status = {}

        for level, days in retention_periods.items():
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Count logs that should have been deleted
            result = await db.execute(
                select(func.count(AuditLog.id)).where(
                    and_(
                        AuditLog.timestamp < cutoff_date,
                        AuditLog.compliance_level == level
                    )
                )
            )

            overdue_count = result.scalar()
            compliance_status[level] = {
                "retention_days": days,
                "overdue_records": overdue_count,
                "compliant": overdue_count == 0
            }

        return {
            "data_retention_compliance": compliance_status,
            "overall_compliant": all(
                status["compliant"] for status in compliance_status.values()
            ),
            "checked_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check data retention compliance: {str(e)}")


@router.get("/compliance/gdpr")
async def gdpr_compliance_check(
    user_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Check GDPR compliance for user data"""
    # Users can check their own data, admins can check anyone's
    if user_id and not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot access other users' GDPR data"
        )

    target_user_id = user_id or current_user.id

    try:
        # Get all audit logs for the user
        user_logs = await audit_service.get_audit_logs(
            db=db,
            user_id=target_user_id,
            limit=10000  # High limit for compliance check
        )

        # Analyze data processing activities
        data_processing = {
            "profile_data": False,
            "search_history": False,
            "api_usage": False,
            "login_history": False
        }

        for log in user_logs:
            if "search" in log.action:
                data_processing["search_history"] = True
            elif "login" in log.action:
                data_processing["login_history"] = True
            elif log.action in ["user_create", "user_update"]:
                data_processing["profile_data"] = True
            elif log.action in ["rag_query", "paper_create", "paper_update"]:
                data_processing["api_usage"] = True

        # Check data retention compliance
        oldest_log = min((log.timestamp for log in user_logs), default=None)
        retention_compliant = True
        if oldest_log:
            max_age_days = (datetime.utcnow() - oldest_log).days
            retention_compliant = max_age_days <= 365  # 1 year for standard data

        return {
            "user_id": str(target_user_id),
            "gdpr_compliance": {
                "data_processing_activities": data_processing,
                "data_retention_compliant": retention_compliant,
                "total_data_points": len(user_logs),
                "data_categories_processed": sum(data_processing.values()),
                "oldest_data_point": oldest_log.isoformat() if oldest_log else None,
                "right_to_access": True,  # We provide access via this endpoint
                "right_to_rectification": True,  # Users can update their profiles
                "right_to_erasure": False  # Not implemented yet
            },
            "checked_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check GDPR compliance: {str(e)}")