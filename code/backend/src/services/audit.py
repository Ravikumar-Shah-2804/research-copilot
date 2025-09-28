"""
Audit logging service for compliance and tracking
"""
import logging
import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, delete

from ..models.audit import AuditLog, AuditEvent, AUDIT_ACTIONS
from ..utils.tracing import get_correlation_id

logger = logging.getLogger(__name__)


class AuditService:
    """Service for managing audit logs"""

    def __init__(self):
        self._queue = asyncio.Queue()
        self._worker_task = None
        self._running = False

    async def start_background_worker(self):
        """Start the background audit logging worker"""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._process_audit_queue())
        logger.info("Audit logging background worker started")

    async def stop_background_worker(self):
        """Stop the background audit logging worker"""
        if not self._running:
            return

        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Audit logging background worker stopped")

    async def log_event(
        self,
        db: AsyncSession,
        event: AuditEvent,
        request_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an audit event"""
        try:
            # Enrich event with request information
            if request_info:
                event.metadata.update({
                    'ip_address': request_info.get('ip_address'),
                    'user_agent': request_info.get('user_agent'),
                    'method': request_info.get('method'),
                    'endpoint': request_info.get('endpoint'),
                    'status_code': request_info.get('status_code'),
                    'session_id': request_info.get('session_id')
                })

            # Create audit log entry
            event_dict = event.to_dict()
            correlation_id = event_dict.pop('correlation_id', None) or get_correlation_id()
            audit_log = AuditLog(
                correlation_id=correlation_id,
                audit_metadata=event_dict.pop('metadata', {}),
                **event_dict
            )

            # Add user information if available
            if event.user_id:
                from ..models.user import User
                user = await db.get(User, event.user_id)
                if user:
                    audit_log.username = user.username
                    audit_log.user_email = user.email
                    audit_log.organization_id = user.organization_id

            db.add(audit_log)
            await db.commit()

            logger.debug(f"Audit log created: {event.action} on {event.resource_type}")

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")

    async def log_event_async(
        self,
        event: AuditEvent,
        request_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an audit event asynchronously via queue"""
        await self._queue.put((event, request_info))

    async def _process_audit_queue(self):
        """Process audit events from the queue"""
        from ..database import get_db

        while self._running:
            try:
                # Wait for audit event with timeout
                event, request_info = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )

                # Process the event
                async for session in get_db():
                    try:
                        await self.log_event(session, event, request_info)
                        break
                    except Exception as e:
                        logger.error(f"Failed to process audit event from queue: {e}")
                    finally:
                        await session.close()

                self._queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Audit queue processing error: {e}")

    async def get_audit_logs(
        self,
        db: AsyncSession,
        user_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        success: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """Query audit logs with filters"""
        query = select(AuditLog)

        # Apply filters
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if organization_id:
            query = query.where(AuditLog.organization_id == organization_id)
        if action:
            query = query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if start_date:
            query = query.where(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.where(AuditLog.timestamp <= end_date)
        if success is not None:
            query = query.where(AuditLog.success == success)

        # Order by timestamp descending
        query = query.order_by(desc(AuditLog.timestamp))

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def get_audit_stats(
        self,
        db: AsyncSession,
        organization_id: Optional[UUID] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get audit statistics"""
        start_date = datetime.utcnow() - timedelta(days=days)

        # Base query
        base_query = select(func.count(AuditLog.id)).where(
            AuditLog.timestamp >= start_date
        )
        if organization_id:
            base_query = base_query.where(AuditLog.organization_id == organization_id)

        # Total events
        total_result = await db.execute(base_query)
        total_events = total_result.scalar()

        # Events by action
        action_query = select(
            AuditLog.action,
            func.count(AuditLog.id).label('count')
        ).where(
            AuditLog.timestamp >= start_date
        )
        if organization_id:
            action_query = action_query.where(AuditLog.organization_id == organization_id)
        action_query = action_query.group_by(AuditLog.action).order_by(desc('count'))

        action_result = await db.execute(action_query)
        actions = {row.action: row.count for row in action_result}

        # Events by resource type
        resource_query = select(
            AuditLog.resource_type,
            func.count(AuditLog.id).label('count')
        ).where(
            AuditLog.timestamp >= start_date
        )
        if organization_id:
            resource_query = resource_query.where(AuditLog.organization_id == organization_id)
        resource_query = resource_query.group_by(AuditLog.resource_type).order_by(desc('count'))

        resource_result = await db.execute(resource_query)
        resources = {row.resource_type: row.count for row in resource_result}

        # Success/failure ratio
        success_query = select(
            AuditLog.success,
            func.count(AuditLog.id).label('count')
        ).where(
            AuditLog.timestamp >= start_date
        )
        if organization_id:
            success_query = success_query.where(AuditLog.organization_id == organization_id)
        success_query = success_query.group_by(AuditLog.success)

        success_result = await db.execute(success_query)
        success_stats = {row.success: row.count for row in success_result}

        return {
            "period_days": days,
            "total_events": total_events,
            "events_by_action": actions,
            "events_by_resource": resources,
            "success_stats": success_stats,
            "organization_id": str(organization_id) if organization_id else None
        }

    async def cleanup_old_logs(self, db: AsyncSession, days_to_keep: int = 365) -> int:
        """Clean up old audit logs based on retention policy"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        # Delete logs older than cutoff
        delete_query = delete(AuditLog).where(
            and_(
                AuditLog.timestamp < cutoff_date,
                AuditLog.retention_days <= days_to_keep
            )
        )

        result = await db.execute(delete_query)
        deleted_count = result.rowcount

        await db.commit()

        logger.info(f"Cleaned up {deleted_count} old audit logs")
        return deleted_count

    async def export_audit_logs(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        organization_id: Optional[UUID] = None,
        format: str = "json"
    ) -> str:
        """Export audit logs for compliance"""
        logs = await self.get_audit_logs(
            db=db,
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000  # Reasonable limit for export
        )

        if format.lower() == "json":
            import json
            return json.dumps([{
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
            } for log in logs], indent=2)

        # Could add CSV export here
        return ""

    async def get_audit_trail(
        self,
        db: AsyncSession,
        user_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get audit trail for analytics"""
        # Get total count
        count_query = select(func.count(AuditLog.id))
        if user_id:
            count_query = count_query.where(AuditLog.user_id == user_id)
        if organization_id:
            count_query = count_query.where(AuditLog.organization_id == organization_id)

        total_result = await db.execute(count_query)
        total_events = total_result.scalar()

        # Get events
        logs = await self.get_audit_logs(
            db=db,
            user_id=user_id,
            organization_id=organization_id,
            limit=limit,
            offset=offset
        )

        events = []
        for log in logs:
            events.append({
                "id": str(log.id),
                "timestamp": log.timestamp.isoformat(),
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": str(log.resource_id) if log.resource_id else None,
                "ip_address": log.audit_metadata.get('ip_address'),
                "user_agent": log.audit_metadata.get('user_agent'),
                "success": log.success
            })

        return {
            "total_events": total_events,
            "events": events,
            "pagination": {
                "page": (offset // limit) + 1,
                "per_page": limit,
                "total_pages": (total_events + limit - 1) // limit
            }
        }


# Global audit service instance
audit_service = AuditService()


# Convenience functions for common audit events
async def log_user_action(db: AsyncSession, action: str, user_id: UUID, **kwargs):
    """Log a user action"""
    event = AuditEvent(
        action=action,
        resource_type="user",
        resource_id=str(user_id),
        user_id=str(user_id),
        **kwargs
    )
    await audit_service.log_event(db, event)


async def log_organization_action(db: AsyncSession, action: str, org_id: UUID, user_id: UUID, **kwargs):
    """Log an organization action"""
    event = AuditEvent(
        action=action,
        resource_type="organization",
        resource_id=str(org_id),
        user_id=str(user_id),
        organization_id=str(org_id),
        **kwargs
    )
    await audit_service.log_event(db, event)


# Specialized audit loggers for different modules
class SearchAuditLogger:
    """Audit logger for search operations"""

    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service

    async def log_search(self, db: AsyncSession, user_id: UUID, query: str, results_count: int, **kwargs):
        """Log a search operation"""
        event = AuditEvent(
            action="search_perform",
            resource_type="search",
            user_id=str(user_id),
            metadata={
                "query": query,
                "results_count": results_count,
                **kwargs
            }
        )
        await self.audit_service.log_event(db, event)

    async def log_rag_query(self, db: AsyncSession, user_id: UUID, query: str, sources_count: int, **kwargs):
        """Log a RAG query operation"""
        event = AuditEvent(
            action="rag_query",
            resource_type="rag",
            user_id=str(user_id),
            metadata={
                "query": query,
                "sources_count": sources_count,
                **kwargs
            }
        )
        await self.audit_service.log_event(db, event)


# Global instances
audit_logger = audit_service  # General audit logger
search_audit_logger = SearchAuditLogger(audit_service)


async def log_security_event(db: AsyncSession, action: str, user_id: Optional[UUID] = None, **kwargs):
    """Log a security event"""
    event = AuditEvent(
        action=action,
        resource_type="security",
        user_id=str(user_id) if user_id else None,
        compliance_level="critical",
        **kwargs
    )
    await audit_service.log_event(db, event)