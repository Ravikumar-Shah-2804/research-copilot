"""
Audit log models for compliance and tracking
"""
from sqlalchemy import Column, String, Text, DateTime, func, JSON, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from ..database import Base


class AuditLog(Base):
    """Audit log for tracking all system activities"""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Who performed the action
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    username = Column(String(100), nullable=True)
    user_email = Column(String(255), nullable=True)
    organization_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # What action was performed
    action = Column(String(100), nullable=False, index=True)  # e.g., 'login', 'create_paper', 'update_user'
    resource_type = Column(String(50), nullable=False, index=True)  # e.g., 'user', 'paper', 'organization'
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Action details
    method = Column(String(10), nullable=True)  # HTTP method
    endpoint = Column(String(500), nullable=True)  # API endpoint
    status_code = Column(Integer, nullable=True)  # HTTP status code

    # Request/Response data (sanitized)
    request_data = Column(JSON, nullable=True)  # Request payload (sensitive data removed)
    response_data = Column(JSON, nullable=True)  # Response data (sensitive data removed)
    audit_metadata = Column(JSON, nullable=True)  # Additional context

    # Result
    success = Column(Boolean, default=True, index=True)
    error_message = Column(Text, nullable=True)

    # Compliance
    compliance_level = Column(String(20), default='standard')  # standard, sensitive, critical
    retention_days = Column(Integer, default=365)  # How long to keep this log

    # Correlation
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    session_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    def __str__(self):
        return f"{self.timestamp} - {self.action} on {self.resource_type} by {self.username or 'system'}"


class AuditEvent:
    """Helper class for creating audit events"""

    def __init__(
        self,
        action: str,
        resource_type: str,
        resource_id: str = None,
        user_id: str = None,
        organization_id: str = None,
        success: bool = True,
        error_message: str = None,
        metadata: dict = None,
        compliance_level: str = 'standard',
        correlation_id: str = None
    ):
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.user_id = user_id
        self.organization_id = organization_id
        self.success = success
        self.error_message = error_message
        self.metadata = metadata or {}
        self.compliance_level = compliance_level
        self.correlation_id = correlation_id

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion"""
        return {
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'success': self.success,
            'error_message': self.error_message,
            'metadata': self.metadata,
            'compliance_level': self.compliance_level,
            'correlation_id': self.correlation_id
        }


# Predefined audit actions
AUDIT_ACTIONS = {
    # Authentication
    'login': 'User login',
    'logout': 'User logout',
    'login_failed': 'Failed login attempt',
    'token_refresh': 'Token refresh',
    'password_change': 'Password change',

    # User management
    'user_create': 'User created',
    'user_update': 'User updated',
    'user_delete': 'User deleted',
    'user_activate': 'User activated',
    'user_deactivate': 'User deactivated',

    # Organization management
    'org_create': 'Organization created',
    'org_update': 'Organization updated',
    'org_delete': 'Organization deleted',
    'user_org_add': 'User added to organization',
    'user_org_remove': 'User removed from organization',

    # Role management
    'role_assign': 'Role assigned to user',
    'role_remove': 'Role removed from user',
    'permission_create': 'Permission created',
    'permission_update': 'Permission updated',
    'permission_delete': 'Permission deleted',

    # API key management
    'api_key_create': 'API key created',
    'api_key_update': 'API key updated',
    'api_key_delete': 'API key deleted',
    'api_key_used': 'API key used',

    # Research operations
    'paper_create': 'Research paper created',
    'paper_update': 'Research paper updated',
    'paper_delete': 'Research paper deleted',
    'search_perform': 'Search performed',
    'rag_query': 'RAG query executed',

    # System operations
    'admin_action': 'Administrative action',
    'config_change': 'Configuration changed',
    'backup_create': 'Backup created',
    'system_alert': 'System alert',

    # Security events
    'suspicious_activity': 'Suspicious activity detected',
    'rate_limit_exceeded': 'Rate limit exceeded',
    'auth_failure': 'Authentication failure',
    'access_denied': 'Access denied'
}