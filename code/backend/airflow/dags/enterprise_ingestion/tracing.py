"""
Langfuse tracing integration for enterprise DAG operations.

This module provides comprehensive observability for the enterprise paper ingestion pipeline,
including multi-tenant organization context, error tracking, and performance metrics.
"""

import logging
import os
import sys
from contextlib import contextmanager
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import threading
import time
from functools import wraps

# Add the src directory to the path
sys_path = os.path.join(os.path.dirname(__file__), '../../../src')
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

logger = logging.getLogger(__name__)

try:
    from langfuse import Langfuse
    from langfuse.api.resources.commons.errors.not_found_error import NotFoundError
    LANGFUSE_AVAILABLE = True
except ImportError:
    logger.warning("Langfuse not available, tracing will be disabled")
    LANGFUSE_AVAILABLE = False
    Langfuse = None

from services.monitoring import performance_monitor
from config import Settings


class EnterpriseDAGTracer:
    """
    Langfuse-based tracer for enterprise DAG operations.

    Provides comprehensive observability with:
    - Multi-tenant organization context
    - Non-blocking error handling
    - Performance metrics integration
    - Pipeline success scoring
    """

    def __init__(self, dag_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the enterprise DAG tracer.

        :param dag_id: The DAG identifier
        :param config: Enterprise configuration
        """
        self.dag_id = dag_id
        self.config = config or {}
        self.langfuse = None
        self.trace = None
        self.organization_context = {}
        self.pipeline_start_time = None
        self._lock = threading.Lock()

        # Initialize Langfuse if available
        self._initialize_langfuse()

    def _initialize_langfuse(self):
        """Initialize Langfuse client with graceful fallback."""
        if not LANGFUSE_AVAILABLE:
            logger.info("Langfuse not available, using no-op tracing")
            return

        try:
            settings = Settings()
            if hasattr(settings, 'LANGFUSE_PUBLIC_KEY') and settings.LANGFUSE_PUBLIC_KEY:
                self.langfuse = Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=getattr(settings, 'LANGFUSE_SECRET_KEY', ''),
                    host=getattr(settings, 'LANGFUSE_HOST', None)
                )
                logger.info("Langfuse tracing initialized successfully")
            else:
                logger.warning("Langfuse credentials not configured, tracing disabled")
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse: {e}, tracing disabled")

    def start_pipeline_trace(self, execution_date: datetime, organizations: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Start a new pipeline trace.

        :param execution_date: DAG execution date
        :param organizations: List of organizations involved
        :returns: Trace ID
        """
        self.pipeline_start_time = time.time()

        if not self.langfuse:
            # Return a mock trace ID for no-op mode
            return f"mock-{self.dag_id}-{int(time.time())}"

        try:
            with self._lock:
                trace_name = f"enterprise_paper_ingestion_{self.dag_id}"
                self.trace = self.langfuse.trace(
                    name=trace_name,
                    metadata={
                        "dag_id": self.dag_id,
                        "execution_date": execution_date.isoformat(),
                        "pipeline_type": "enterprise_ingestion",
                        "organizations_count": len(organizations) if organizations else 0,
                        "start_time": datetime.now().isoformat()
                    }
                )

                # Set organization context for multi-tenant observability
                if organizations:
                    self.organization_context = {
                        "organization_ids": [org.get("id") for org in organizations],
                        "organization_names": [org.get("name") for org in organizations],
                        "total_organizations": len(organizations)
                    }
                    self.trace.update(metadata={**self.trace.metadata, **self.organization_context})

                logger.info(f"Started pipeline trace: {self.trace.id}")
                return self.trace.id

        except Exception as e:
            logger.warning(f"Failed to start pipeline trace: {e}")
            return f"fallback-{self.dag_id}-{int(time.time())}"

    def end_pipeline_trace(self, status: str, metrics: Optional[Dict[str, Any]] = None):
        """
        End the pipeline trace with final status and metrics.

        :param status: Pipeline completion status
        :param metrics: Final pipeline metrics
        """
        if not self.trace:
            return

        try:
            duration = time.time() - self.pipeline_start_time if self.pipeline_start_time else 0

            # Calculate pipeline success score
            success_score = self._calculate_pipeline_score(status, metrics)

            final_metadata = {
                "end_time": datetime.now().isoformat(),
                "duration_seconds": duration,
                "final_status": status,
                "success_score": success_score,
                **self.organization_context
            }

            if metrics:
                final_metadata.update(metrics)

            self.trace.update(metadata=final_metadata)

            # Record final score as a generation for observability
            if self.langfuse:
                self.trace.generation(
                    name="pipeline_completion",
                    model="enterprise_pipeline",
                    input={"organizations": self.organization_context.get("organization_ids", [])},
                    output={"status": status, "metrics": metrics or {}},
                    metadata={"success_score": success_score}
                )

            logger.info(f"Ended pipeline trace: {self.trace.id}, status: {status}, score: {success_score}")

        except Exception as e:
            logger.warning(f"Failed to end pipeline trace: {e}")

    @contextmanager
    def trace_task(self, task_id: str, organization_id: Optional[str] = None, **metadata):
        """
        Context manager for tracing individual DAG tasks.

        :param task_id: Task identifier
        :param organization_id: Organization context for the task
        :param metadata: Additional metadata for the span
        """
        span = None
        start_time = time.time()

        try:
            if self.trace and self.langfuse:
                span_metadata = {
                    "task_id": task_id,
                    "dag_id": self.dag_id,
                    "start_time": datetime.now().isoformat(),
                    **metadata
                }

                if organization_id:
                    span_metadata["organization_id"] = organization_id

                span = self.trace.span(
                    name=f"task_{task_id}",
                    metadata=span_metadata
                )

            yield span

        except Exception as e:
            logger.warning(f"Failed to create task span for {task_id}: {e}")
            yield None

        finally:
            if span:
                try:
                    duration = time.time() - start_time
                    span.end(metadata={
                        "duration_seconds": duration,
                        "end_time": datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Failed to end task span for {task_id}: {e}")

    def record_task_metric(self, task_id: str, metric_name: str, value: Union[int, float], organization_id: Optional[str] = None):
        """
        Record a metric for a specific task.

        :param task_id: Task identifier
        :param metric_name: Name of the metric
        :param value: Metric value
        :param organization_id: Organization context
        """
        if not self.trace or not self.langfuse:
            return

        try:
            metadata = {
                "task_id": task_id,
                "metric_name": metric_name,
                "metric_value": value,
                "recorded_at": datetime.now().isoformat()
            }

            if organization_id:
                metadata["organization_id"] = organization_id

            # Record as an event/score
            self.trace.score(
                name=f"{task_id}_{metric_name}",
                value=value,
                metadata=metadata
            )

        except Exception as e:
            logger.warning(f"Failed to record task metric {metric_name} for {task_id}: {e}")

    def record_error(self, task_id: str, error: Exception, organization_id: Optional[str] = None, severity: str = "error"):
        """
        Record an error in the trace.

        :param task_id: Task where error occurred
        :param error: The exception that occurred
        :param organization_id: Organization context
        :param severity: Error severity level
        """
        if not self.trace or not self.langfuse:
            return

        try:
            error_metadata = {
                "task_id": task_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "severity": severity,
                "recorded_at": datetime.now().isoformat()
            }

            if organization_id:
                error_metadata["organization_id"] = organization_id

            # Record error as a score with negative value
            self.trace.score(
                name=f"{task_id}_error",
                value=-1,  # Negative score for errors
                metadata=error_metadata
            )

            logger.info(f"Recorded error in trace: {task_id} - {error}")

        except Exception as e:
            logger.warning(f"Failed to record error for {task_id}: {e}")

    def record_organization_metric(self, organization_id: str, metric_name: str, value: Union[int, float], task_context: Optional[str] = None):
        """
        Record organization-specific metrics for multi-tenant observability.

        :param organization_id: Organization identifier
        :param metric_name: Metric name
        :param value: Metric value
        :param task_context: Task context where metric was recorded
        """
        if not self.trace or not self.langfuse:
            return

        try:
            metadata = {
                "organization_id": organization_id,
                "metric_name": metric_name,
                "metric_value": value,
                "recorded_at": datetime.now().isoformat()
            }

            if task_context:
                metadata["task_context"] = task_context

            self.trace.score(
                name=f"org_{organization_id}_{metric_name}",
                value=value,
                metadata=metadata
            )

        except Exception as e:
            logger.warning(f"Failed to record organization metric {metric_name} for {organization_id}: {e}")

    def _calculate_pipeline_score(self, status: str, metrics: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate a success score for the pipeline execution.

        :param status: Pipeline status
        :param metrics: Pipeline metrics
        :returns: Score between 0.0 and 1.0
        """
        try:
            base_score = 1.0 if status == "success" else 0.0

            if not metrics:
                return base_score

            # Adjust score based on key metrics
            adjustments = []

            # Success rate adjustment
            success_rate = metrics.get("pipeline_success_rate", 1.0)
            adjustments.append(success_rate * 0.3)

            # Error count penalty
            error_count = metrics.get("total_errors", 0)
            error_penalty = min(error_count * 0.1, 0.5)  # Max 50% penalty
            adjustments.append(-error_penalty)

            # Performance adjustment (faster is better, but not too strict)
            duration = metrics.get("total_duration_seconds", 0)
            if duration > 3600:  # Over 1 hour
                adjustments.append(-0.1)
            elif duration < 600:  # Under 10 minutes
                adjustments.append(0.1)

            # Organization processing success
            org_success_rate = metrics.get("organization_success_rate", 1.0)
            adjustments.append(org_success_rate * 0.2)

            final_score = max(0.0, min(1.0, base_score + sum(adjustments)))
            return round(final_score, 2)

        except Exception as e:
            logger.warning(f"Failed to calculate pipeline score: {e}")
            return 0.5  # Neutral score on error


def traced_enterprise_task(task_name: str):
    """
    Decorator for tracing enterprise DAG tasks.

    :param task_name: Name of the task for tracing
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get tracer from kwargs or global context
            tracer = kwargs.get('tracer')
            organization_id = kwargs.get('organization_id')

            if tracer:
                with tracer.trace_task(task_name, organization_id=organization_id):
                    return func(*args, **kwargs)
            else:
                # Fallback without tracing
                return func(*args, **kwargs)

        return wrapper
    return decorator


# Global tracer instance for the enterprise DAG
enterprise_tracer = EnterpriseDAGTracer("enterprise_paper_ingestion")