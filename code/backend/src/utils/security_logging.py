"""
Enterprise-grade security logging with sensitive data masking and compliance features
"""
import logging
import re
import json
import hashlib
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from contextvars import ContextVar
import structlog
from functools import wraps

from ..config import settings

# Context variables for distributed tracing
correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
trace_id_context: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
span_id_context: ContextVar[Optional[str]] = ContextVar('span_id', default=None)
user_id_context: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
organization_id_context: ContextVar[Optional[str]] = ContextVar('organization_id', default=None)


class SensitiveDataMasker:
    """Advanced sensitive data masking for logs"""

    def __init__(self):
        # Patterns for sensitive data
        self.patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
            'ssn': re.compile(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b'),
            'credit_card': re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'),
            'api_key': re.compile(r'\b[A-Za-z0-9]{32,}\b'),  # Generic API key pattern
            'password': re.compile(r'(?i)(password|passwd|pwd)[\'"]?\s*[:=]\s*[\'"]([^\'"]+)[\'"]'),
            'token': re.compile(r'\bBearer\s+[A-Za-z0-9-_.]+\b', re.IGNORECASE),
            'jwt': re.compile(r'eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+'),
        }

        # Custom patterns that can be added
        self.custom_patterns: Dict[str, re.Pattern] = {}

    def add_pattern(self, name: str, pattern: str, flags: int = 0):
        """Add custom masking pattern"""
        self.custom_patterns[name] = re.compile(pattern, flags)

    def mask_sensitive_data(self, data: Any) -> Any:
        """Recursively mask sensitive data in any data structure"""
        if isinstance(data, str):
            return self._mask_string(data)
        elif isinstance(data, dict):
            return {key: self.mask_sensitive_data(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.mask_sensitive_data(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(self.mask_sensitive_data(item) for item in data)
        else:
            return data

    def _mask_string(self, text: str) -> str:
        """Mask sensitive data in a string"""
        masked = text

        # Apply all patterns
        all_patterns = {**self.patterns, **self.custom_patterns}

        for pattern_name, pattern in all_patterns.items():
            masked = pattern.sub(self._get_mask_replacement(pattern_name), masked)

        return masked

    def _get_mask_replacement(self, pattern_name: str) -> str:
        """Get appropriate mask replacement for pattern"""
        replacements = {
            'email': '[EMAIL_MASKED]',
            'phone': '[PHONE_MASKED]',
            'ssn': '[SSN_MASKED]',
            'credit_card': '[CREDIT_CARD_MASKED]',
            'api_key': '[API_KEY_MASKED]',
            'password': r'\1: [PASSWORD_MASKED]',
            'token': '[TOKEN_MASKED]',
            'jwt': '[JWT_MASKED]',
        }
        return replacements.get(pattern_name, f'[{pattern_name.upper()}_MASKED]')


class SecurityEventLogger:
    """Specialized logger for security events"""

    def __init__(self, masker: SensitiveDataMasker = None):
        self.masker = masker or SensitiveDataMasker()
        self.logger = structlog.get_logger('security')

        # Security event types
        self.event_types = {
            'auth_success': 'INFO',
            'auth_failure': 'WARNING',
            'auth_suspicious': 'WARNING',
            'access_denied': 'WARNING',
            'access_granted': 'INFO',
            'data_access': 'INFO',
            'data_modification': 'INFO',
            'security_violation': 'ERROR',
            'intrusion_attempt': 'ERROR',
            'policy_violation': 'WARNING',
            'audit_event': 'INFO',
        }

    def log_security_event(
        self,
        event_type: str,
        message: str,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        severity: Optional[str] = None
    ):
        """Log a security event with structured data"""
        # Determine log level
        log_level = severity or self.event_types.get(event_type, 'INFO')

        # Prepare structured log data
        log_data = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'correlation_id': correlation_id_context.get(),
            'trace_id': trace_id_context.get(),
            'span_id': span_id_context.get(),
            'user_id': user_id or user_id_context.get(),
            'organization_id': organization_id or organization_id_context.get(),
            'ip_address': ip_address,
            'user_agent': user_agent,
            'resource': resource,
            'action': action,
            'severity': log_level,
        }

        # Add metadata if provided
        if metadata:
            # Mask sensitive data in metadata
            masked_metadata = self.masker.mask_sensitive_data(metadata)
            log_data['metadata'] = masked_metadata

        # Mask sensitive data in message
        masked_message = self.masker.mask_sensitive_data(message)

        # Log with appropriate level
        if log_level == 'ERROR':
            self.logger.error(masked_message, **log_data)
        elif log_level == 'WARNING':
            self.logger.warning(masked_message, **log_data)
        elif log_level == 'DEBUG':
            self.logger.debug(masked_message, **log_data)
        else:
            self.logger.info(masked_message, **log_data)

    def log_auth_success(self, user_id: str, method: str = 'password', **kwargs):
        """Log successful authentication"""
        self.log_security_event(
            'auth_success',
            f'User {user_id} authenticated successfully via {method}',
            user_id=user_id,
            action='login',
            **kwargs
        )

    def log_auth_failure(self, identifier: str, reason: str = 'invalid_credentials', **kwargs):
        """Log authentication failure"""
        self.log_security_event(
            'auth_failure',
            f'Authentication failed for {identifier}: {reason}',
            action='login_attempt',
            metadata={'failure_reason': reason},
            **kwargs
        )

    def log_access_denied(self, user_id: Optional[str], resource: str, action: str, **kwargs):
        """Log access denial"""
        self.log_security_event(
            'access_denied',
            f'Access denied to {resource} for action {action}',
            user_id=user_id,
            resource=resource,
            action=action,
            **kwargs
        )

    def log_suspicious_activity(self, activity_type: str, details: Dict[str, Any], **kwargs):
        """Log suspicious activity"""
        self.log_security_event(
            'intrusion_attempt',
            f'Suspicious activity detected: {activity_type}',
            metadata=details,
            severity='ERROR',
            **kwargs
        )


class ComplianceLogger:
    """Logger for compliance and audit requirements"""

    def __init__(self, masker: SensitiveDataMasker = None):
        self.masker = masker or SensitiveDataMasker()
        self.logger = structlog.get_logger('compliance')

    def log_gdpr_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        data_types: List[str] = None,
        purpose: Optional[str] = None,
        legal_basis: Optional[str] = None,
        **kwargs
    ):
        """Log GDPR compliance event"""
        log_data = {
            'compliance_framework': 'GDPR',
            'event_type': event_type,
            'user_id': user_id,
            'data_types': data_types or [],
            'purpose': purpose,
            'legal_basis': legal_basis,
            'timestamp': datetime.utcnow().isoformat(),
            'correlation_id': correlation_id_context.get(),
        }

        # Add additional context
        log_data.update(kwargs)

        message = f"GDPR Event: {event_type} for user {user_id or 'unknown'}"
        self.logger.info(message, **log_data)

    def log_data_processing(self, operation: str, data_subjects: int, **kwargs):
        """Log data processing activity"""
        self.log_gdpr_event(
            'data_processing',
            event_type=f'data_{operation}',
            data_subjects_affected=data_subjects,
            **kwargs
        )

    def log_data_deletion(self, user_id: str, data_types: List[str], **kwargs):
        """Log data deletion for GDPR right to erasure"""
        self.log_gdpr_event(
            'data_deletion',
            user_id=user_id,
            event_type='right_to_erasure',
            data_types=data_types,
            **kwargs
        )

    def log_consent_change(self, user_id: str, consent_type: str, granted: bool, **kwargs):
        """Log consent changes"""
        self.log_gdpr_event(
            'consent_change',
            user_id=user_id,
            event_type='consent_update',
            consent_type=consent_type,
            consent_granted=granted,
            **kwargs
        )


class PerformanceLogger:
    """Logger for performance monitoring with security context"""

    def __init__(self, masker: SensitiveDataMasker = None):
        self.masker = masker or SensitiveDataMasker()
        self.logger = structlog.get_logger('performance')

    def log_performance_metric(
        self,
        operation: str,
        duration: float,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log performance metric"""
        log_data = {
            'operation': operation,
            'duration_seconds': duration,
            'success': success,
            'timestamp': datetime.utcnow().isoformat(),
            'correlation_id': correlation_id_context.get(),
            'trace_id': trace_id_context.get(),
            'user_id': user_id_context.get(),
            'organization_id': organization_id_context.get(),
        }

        # Add metadata
        if metadata:
            masked_metadata = self.masker.mask_sensitive_data(metadata)
            log_data['metadata'] = masked_metadata

        # Add additional context
        log_data.update(kwargs)

        # Determine log level based on performance
        if not success:
            self.logger.error(f"Operation {operation} failed", **log_data)
        elif duration > 10.0:  # Slow operation
            self.logger.warning(f"Slow operation: {operation}", **log_data)
        else:
            self.logger.info(f"Operation completed: {operation}", **log_data)

    def log_request_performance(self, endpoint: str, method: str, duration: float, status_code: int, **kwargs):
        """Log HTTP request performance"""
        success = 200 <= status_code < 400
        self.log_performance_metric(
            f"http_{method.lower()}_{endpoint}",
            duration,
            success,
            metadata={'status_code': status_code, 'endpoint': endpoint, 'method': method},
            **kwargs
        )


class AuditLogger:
    """Comprehensive audit logger for all system activities"""

    def __init__(self):
        self.masker = SensitiveDataMasker()
        self.security_logger = SecurityEventLogger(self.masker)
        self.compliance_logger = ComplianceLogger(self.masker)
        self.performance_logger = PerformanceLogger(self.masker)

    def log_audit_event(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        compliance_level: str = 'standard'
    ):
        """Log comprehensive audit event"""
        # Create audit event data
        audit_data = {
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'user_id': user_id,
            'organization_id': organization_id,
            'success': success,
            'error_message': error_message,
            'compliance_level': compliance_level,
            'timestamp': datetime.utcnow().isoformat(),
            'correlation_id': correlation_id_context.get(),
            'trace_id': trace_id_context.get(),
            'span_id': span_id_context.get(),
        }

        # Add masked metadata
        if metadata:
            audit_data['metadata'] = self.masker.mask_sensitive_data(metadata)

        # Determine appropriate logger based on action type
        if action in ['login', 'logout', 'password_change', 'api_key_create']:
            self.security_logger.log_security_event(
                f'auth_{action}',
                f'User {user_id or "unknown"} performed {action}',
                user_id=user_id,
                organization_id=organization_id,
                action=action,
                metadata=metadata
            )
        elif action in ['data_access', 'data_export', 'data_delete']:
            self.compliance_logger.log_gdpr_event(
                action,
                user_id=user_id,
                metadata=metadata
            )
        else:
            # General audit event
            logger = structlog.get_logger('audit')
            message = f"Audit: {action} on {resource_type}"
            if not success:
                logger.warning(message, **audit_data)
            else:
                logger.info(message, **audit_data)


# Global instances
sensitive_data_masker = SensitiveDataMasker()
security_logger = SecurityEventLogger(sensitive_data_masker)
compliance_logger = ComplianceLogger(sensitive_data_masker)
performance_logger = PerformanceLogger(sensitive_data_masker)
audit_logger = AuditLogger()


def set_correlation_context(correlation_id: str, trace_id: str = None, span_id: str = None):
    """Set distributed tracing context"""
    correlation_id_context.set(correlation_id)
    if trace_id:
        trace_id_context.set(trace_id)
    if span_id:
        span_id_context.set(span_id)


def set_user_context(user_id: str, organization_id: str = None):
    """Set user context for logging"""
    user_id_context.set(user_id)
    if organization_id:
        organization_id_context.set(organization_id)


def audit_log(action: str, resource_type: str):
    """Decorator for audit logging"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user and resource info (simplified)
            user_id = user_id_context.get()
            organization_id = organization_id_context.get()

            try:
                result = await func(*args, **kwargs)
                audit_logger.log_audit_event(
                    action=action,
                    resource_type=resource_type,
                    user_id=user_id,
                    organization_id=organization_id,
                    success=True
                )
                return result
            except Exception as e:
                audit_logger.log_audit_event(
                    action=action,
                    resource_type=resource_type,
                    user_id=user_id,
                    organization_id=organization_id,
                    success=False,
                    error_message=str(e)
                )
                raise
        return wrapper
    return decorator


def security_log(event_type: str, message: str):
    """Decorator for security event logging"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                security_logger.log_security_event(
                    event_type=event_type,
                    message=message,
                    user_id=user_id_context.get(),
                    organization_id=organization_id_context.get()
                )
                return result
            except Exception as e:
                security_logger.log_security_event(
                    event_type=f"{event_type}_failed",
                    message=f"{message} - Error: {str(e)}",
                    user_id=user_id_context.get(),
                    organization_id=organization_id_context.get(),
                    severity='ERROR'
                )
                raise
        return wrapper
    return decorator