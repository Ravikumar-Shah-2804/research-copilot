"""
Distributed tracing utilities
"""
import logging
from contextvars import ContextVar
from typing import Optional, Dict, Any
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

# Context variables for tracing
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
span_id_var: ContextVar[Optional[str]] = ContextVar('span_id', default=None)


class TracingContext:
    """Context manager for tracing spans"""

    def __init__(self, operation: str, parent_span_id: Optional[str] = None):
        self.operation = operation
        self.parent_span_id = parent_span_id
        self.span_id = None
        self.start_time = None

    async def __aenter__(self):
        import uuid
        import time

        # Generate span ID
        self.span_id = str(uuid.uuid4())[:16]
        self.start_time = time.time()

        # Set span ID in context
        self._span_token = span_id_var.set(self.span_id)

        logger.info(
            f"Starting span: {self.operation}",
            extra={
                "operation": self.operation,
                "span_id": self.span_id,
                "parent_span_id": self.parent_span_id,
                "correlation_id": get_correlation_id(),
                "trace_id": get_trace_id()
            }
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        import time

        duration = time.time() - self.start_time

        if exc_type:
            logger.error(
                f"Span failed: {self.operation}",
                extra={
                    "operation": self.operation,
                    "span_id": self.span_id,
                    "duration": duration,
                    "error": str(exc_val),
                    "correlation_id": get_correlation_id(),
                    "trace_id": get_trace_id()
                }
            )
        else:
            logger.info(
                f"Span completed: {self.operation}",
                extra={
                    "operation": self.operation,
                    "span_id": self.span_id,
                    "duration": duration,
                    "correlation_id": get_correlation_id(),
                    "trace_id": get_trace_id()
                }
            )

        # Reset span context
        span_id_var.reset(self._span_token)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID"""
    return correlation_id_var.get()


def get_trace_id() -> Optional[str]:
    """Get current trace ID"""
    return trace_id_var.get()


def get_span_id() -> Optional[str]:
    """Get current span ID"""
    return span_id_var.get()


def set_tracing_context(correlation_id: str, trace_id: str, span_id: Optional[str] = None):
    """Set tracing context for current execution"""
    correlation_id_var.set(correlation_id)
    trace_id_var.set(trace_id)
    if span_id:
        span_id_var.set(span_id)


def extract_tracing_from_request(request) -> Dict[str, str]:
    """Extract tracing information from request"""
    return {
        "correlation_id": getattr(request.state, 'correlation_id', None) or request.headers.get("X-Correlation-ID"),
        "trace_id": getattr(request.state, 'trace_id', None) or request.headers.get("X-Trace-ID"),
        "span_id": getattr(request.state, 'span_id', None) or request.headers.get("X-Span-ID"),
        "parent_span_id": getattr(request.state, 'parent_span_id', None) or request.headers.get("X-Parent-Span-ID")
    }


def inject_tracing_into_request(request, correlation_id: str, trace_id: str, span_id: str):
    """Inject tracing information into request state"""
    request.state.correlation_id = correlation_id
    request.state.trace_id = trace_id
    request.state.span_id = span_id


def traced_operation(operation: str):
    """Decorator to trace async function operations"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with TracingContext(operation):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


def traced_sync_operation(operation: str):
    """Decorator to trace sync function operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            import uuid

            span_id = str(uuid.uuid4())[:16]
            start_time = time.time()

            logger.info(
                f"Starting sync span: {operation}",
                extra={
                    "operation": operation,
                    "span_id": span_id,
                    "correlation_id": get_correlation_id(),
                    "trace_id": get_trace_id()
                }
            )

            try:
                result = func(*args, **kwargs)

                duration = time.time() - start_time
                logger.info(
                    f"Sync span completed: {operation}",
                    extra={
                        "operation": operation,
                        "span_id": span_id,
                        "duration": duration,
                        "correlation_id": get_correlation_id(),
                        "trace_id": get_trace_id()
                    }
                )

                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Sync span failed: {operation}",
                    extra={
                        "operation": operation,
                        "span_id": span_id,
                        "duration": duration,
                        "error": str(e),
                        "correlation_id": get_correlation_id(),
                        "trace_id": get_trace_id()
                    }
                )
                raise

        return wrapper
    return decorator


class TracingClient:
    """HTTP client with tracing support"""

    def __init__(self, session=None):
        self.session = session

    async def request(self, method: str, url: str, **kwargs):
        """Make traced HTTP request"""
        import httpx

        # Add tracing headers
        headers = kwargs.get('headers', {})
        correlation_id = get_correlation_id()
        trace_id = get_trace_id()
        span_id = get_span_id()

        if correlation_id:
            headers['X-Correlation-ID'] = correlation_id
        if trace_id:
            headers['X-Trace-ID'] = trace_id
        if span_id:
            headers['X-Parent-Span-ID'] = span_id

        kwargs['headers'] = headers

        async with TracingContext(f"http_{method.lower()}_{url}"):
            if self.session:
                return await self.session.request(method, url, **kwargs)
            else:
                async with httpx.AsyncClient() as client:
                    return await client.request(method, url, **kwargs)


# Global tracing client instance
tracing_client = TracingClient()