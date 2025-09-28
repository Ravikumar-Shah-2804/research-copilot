"""
Enhanced circuit breaker pattern implementation with advanced error recovery
"""
import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Any, Dict, Optional, List, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass
import random

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, requests rejected
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: float = 60.0  # Seconds to wait before trying again
    expected_exception: tuple = (Exception,)  # Exceptions that count as failures
    success_threshold: int = 3  # Successes needed to close circuit in half-open state
    timeout: float = 10.0  # Request timeout
    slow_call_duration_threshold: float = 5.0  # Duration threshold for slow calls
    slow_call_rate_threshold: float = 0.5  # Rate threshold for slow calls (0.0-1.0)
    enable_adaptive_timeout: bool = True  # Adapt timeout based on performance
    enable_metrics_collection: bool = True  # Collect detailed metrics


@dataclass
class RetryConfig:
    """Configuration for retry mechanisms"""
    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay
    backoff_factor: float = 2.0  # Exponential backoff factor
    jitter: bool = True  # Add random jitter to delays
    retry_on_exceptions: tuple = (Exception,)  # Exceptions to retry on
    retry_on_status_codes: tuple = (500, 502, 503, 504)  # HTTP status codes to retry


@dataclass
class FallbackConfig:
    """Configuration for fallback mechanisms"""
    enabled: bool = True
    fallback_timeout: float = 5.0  # Timeout for fallback execution
    cache_fallback_results: bool = True  # Cache fallback results
    cache_ttl: int = 300  # Cache TTL in seconds


class CircuitBreakerStats:
    """Enhanced statistics for circuit breaker"""

    def __init__(self):
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.total_timeouts = 0
        self.total_slow_calls = 0
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.response_times: List[float] = []
        self.max_response_times_window = 100  # Keep last 100 response times

    def record_success(self, response_time: float = 0.0):
        """Record successful request"""
        self.total_requests += 1
        self.total_successes += 1
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.last_success_time = time.time()
        self._add_response_time(response_time)

    def record_failure(self, response_time: float = 0.0, is_timeout: bool = False):
        """Record failed request"""
        self.total_requests += 1
        self.total_failures += 1
        if is_timeout:
            self.total_timeouts += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_failure_time = time.time()
        self._add_response_time(response_time)

    def record_slow_call(self, response_time: float):
        """Record slow call"""
        self.total_slow_calls += 1
        self._add_response_time(response_time)

    def _add_response_time(self, response_time: float):
        """Add response time to rolling window"""
        self.response_times.append(response_time)
        if len(self.response_times) > self.max_response_times_window:
            self.response_times.pop(0)

    def get_avg_response_time(self) -> float:
        """Get average response time"""
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0.0

    def get_slow_call_rate(self) -> float:
        """Get rate of slow calls"""
        if not self.total_requests:
            return 0.0
        return self.total_slow_calls / self.total_requests

    def reset(self):
        """Reset statistics"""
        self.consecutive_failures = 0
        self.consecutive_successes = 0


class CircuitBreaker:
    """Circuit breaker implementation"""

    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                await self._transition_to_half_open()
            else:
                raise CircuitBreakerOpenException(self.name)

        if self.state == CircuitBreakerState.HALF_OPEN:
            # Allow limited requests in half-open state
            pass

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )

            await self._on_success()
            return result

        except self.config.expected_exception as e:
            await self._on_failure()
            raise
        except asyncio.TimeoutError:
            await self._on_failure()
            raise CircuitBreakerTimeoutException(self.name, self.config.timeout)

    async def _on_success(self):
        """Handle successful request"""
        async with self._lock:
            self.stats.record_success()

            if self.state == CircuitBreakerState.HALF_OPEN:
                if self.stats.consecutive_successes >= self.config.success_threshold:
                    await self._transition_to_closed()

    async def _on_failure(self):
        """Handle failed request"""
        async with self._lock:
            self.stats.record_failure()

            if self.state == CircuitBreakerState.CLOSED:
                if self.stats.consecutive_failures >= self.config.failure_threshold:
                    await self._transition_to_open()
            elif self.state == CircuitBreakerState.HALF_OPEN:
                await self._transition_to_open()

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit"""
        if self.stats.last_failure_time is None:
            return True

        return (time.time() - self.stats.last_failure_time) >= self.config.recovery_timeout

    async def _transition_to_open(self):
        """Transition to open state"""
        self.state = CircuitBreakerState.OPEN
        logger.warning(f"Circuit breaker '{self.name}' opened")

    async def _transition_to_half_open(self):
        """Transition to half-open state"""
        self.state = CircuitBreakerState.HALF_OPEN
        self.stats.reset()
        logger.info(f"Circuit breaker '{self.name}' half-opened")

    async def _transition_to_closed(self):
        """Transition to closed state"""
        self.state = CircuitBreakerState.CLOSED
        self.stats.reset()
        logger.info(f"Circuit breaker '{self.name}' closed")

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "total_requests": self.stats.total_requests,
            "total_failures": self.stats.total_failures,
            "total_successes": self.stats.total_successes,
            "total_timeouts": self.stats.total_timeouts,
            "total_slow_calls": self.stats.total_slow_calls,
            "consecutive_failures": self.stats.consecutive_failures,
            "consecutive_successes": self.stats.consecutive_successes,
            "avg_response_time": self.stats.get_avg_response_time(),
            "slow_call_rate": self.stats.get_slow_call_rate(),
            "last_failure_time": self.stats.last_failure_time,
            "last_success_time": self.stats.last_success_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
                "slow_call_duration_threshold": self.config.slow_call_duration_threshold,
                "slow_call_rate_threshold": self.config.slow_call_rate_threshold
            }
        }


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers"""

    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}

    def get_or_create(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """Get existing circuit breaker or create new one"""
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(name, config)
        return self.breakers[name]

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        return {name: breaker.get_stats() for name, breaker in self.breakers.items()}

    async def reset_all(self):
        """Reset all circuit breakers to closed state"""
        for breaker in self.breakers.values():
            async with breaker._lock:
                breaker.state = CircuitBreakerState.CLOSED
                breaker.stats.reset()
        logger.info("All circuit breakers reset")


# Global circuit breaker registry
circuit_breaker_registry = CircuitBreakerRegistry()


class RetryMechanism:
    """Advanced retry mechanism with exponential backoff and jitter"""

    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()

    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except self.config.retry_on_exceptions as e:
                last_exception = e

                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.debug(f"Retry attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.warning(f"All {self.config.max_attempts} retry attempts failed")
                    raise last_exception
            except Exception as e:
                # Don't retry for unexpected exceptions
                raise e

        raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter"""
        delay = min(
            self.config.base_delay * (self.config.backoff_factor ** attempt),
            self.config.max_delay
        )

        if self.config.jitter:
            # Add random jitter (±25% of delay)
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)


class FallbackMechanism:
    """Fallback mechanism for graceful degradation"""

    def __init__(self, config: FallbackConfig = None):
        self.config = config or FallbackConfig()
        self._cache = {}  # Simple in-memory cache for fallback results

    async def execute_with_fallback(
        self,
        primary_func: Callable,
        fallback_func: Callable,
        cache_key: str = None,
        *args,
        **kwargs
    ) -> Any:
        """Execute primary function with fallback"""
        # Try cache first if enabled
        if self.config.cache_fallback_results and cache_key and cache_key in self._cache:
            cached_result, cached_time = self._cache[cache_key]
            if time.time() - cached_time < self.config.cache_ttl:
                logger.debug(f"Using cached fallback result for {cache_key}")
                return cached_result

        try:
            # Try primary function
            return await primary_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Primary function failed, executing fallback: {e}")

            try:
                # Execute fallback with timeout
                result = await asyncio.wait_for(
                    fallback_func(*args, **kwargs),
                    timeout=self.config.fallback_timeout
                )

                # Cache result if enabled
                if self.config.cache_fallback_results and cache_key:
                    self._cache[cache_key] = (result, time.time())

                return result
            except Exception as fallback_error:
                logger.error(f"Fallback function also failed: {fallback_error}")
                raise fallback_error

    def clear_cache(self, key: str = None):
        """Clear fallback cache"""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()


class ResilienceManager:
    """Comprehensive resilience manager combining circuit breaker, retry, and fallback"""

    def __init__(
        self,
        name: str,
        circuit_config: CircuitBreakerConfig = None,
        retry_config: RetryConfig = None,
        fallback_config: FallbackConfig = None
    ):
        self.name = name
        self.circuit_breaker = CircuitBreaker(name, circuit_config)
        self.retry_mechanism = RetryMechanism(retry_config)
        self.fallback_mechanism = FallbackMechanism(fallback_config)

    async def execute_resilient(
        self,
        func: Callable,
        fallback_func: Callable = None,
        cache_key: str = None,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with full resilience (circuit breaker + retry + fallback)"""
        start_time = time.time()

        try:
            # Execute with circuit breaker and retry
            result = await self.circuit_breaker.call(
                self.retry_mechanism.execute_with_retry,
                func, *args, **kwargs
            )

            response_time = time.time() - start_time
            self.circuit_breaker.stats.record_success(response_time)

            # Check for slow calls
            if response_time > self.circuit_breaker.config.slow_call_duration_threshold:
                self.circuit_breaker.stats.record_slow_call(response_time)

            return result

        except CircuitBreakerOpenException:
            # Circuit is open, try fallback if available
            if fallback_func:
                logger.info(f"Circuit breaker open for {self.name}, using fallback")
                return await self.fallback_mechanism.execute_with_fallback(
                    lambda: None,  # Primary already failed
                    fallback_func,
                    cache_key,
                    *args,
                    **kwargs
                )
            else:
                raise

        except Exception as e:
            response_time = time.time() - start_time
            is_timeout = isinstance(e, asyncio.TimeoutError)
            self.circuit_breaker.stats.record_failure(response_time, is_timeout)
            raise e

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive resilience statistics"""
        return {
            "name": self.name,
            "circuit_breaker": self.circuit_breaker.get_stats(),
            "retry_config": {
                "max_attempts": self.retry_mechanism.config.max_attempts,
                "base_delay": self.retry_mechanism.config.base_delay,
                "backoff_factor": self.retry_mechanism.config.backoff_factor
            },
            "fallback_enabled": self.fallback_mechanism.config.enabled,
            "cache_size": len(self.fallback_mechanism._cache)
        }


class ResilienceRegistry:
    """Registry for managing multiple resilience managers"""

    def __init__(self):
        self.managers: Dict[str, ResilienceManager] = {}

    def get_or_create(
        self,
        name: str,
        circuit_config: CircuitBreakerConfig = None,
        retry_config: RetryConfig = None,
        fallback_config: FallbackConfig = None
    ) -> ResilienceManager:
        """Get existing resilience manager or create new one"""
        if name not in self.managers:
            self.managers[name] = ResilienceManager(
                name, circuit_config, retry_config, fallback_config
            )
        return self.managers[name]

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all resilience managers"""
        return {name: manager.get_stats() for name, manager in self.managers.items()}


class CircuitBreakerService:
    """Circuit breaker service for analytics endpoints"""

    def __init__(self):
        self.registry = circuit_breaker_registry

    async def get_all_status(self) -> Dict[str, Any]:
        """Get status of all circuit breakers"""
        stats = self.registry.get_all_stats()
        circuit_breakers = {}

        for name, stat in stats.items():
            circuit_breakers[name] = {
                "state": stat["state"],
                "failure_count": stat["consecutive_failures"],
                "last_failure_time": stat["last_failure_time"],
                "next_retry_time": None  # Simplified
            }

        summary = {
            "total": len(circuit_breakers),
            "open": sum(1 for cb in circuit_breakers.values() if cb["state"] == "open"),
            "half_open": sum(1 for cb in circuit_breakers.values() if cb["state"] == "half_open"),
            "closed": sum(1 for cb in circuit_breakers.values() if cb["state"] == "closed")
        }

        return {
            "circuit_breakers": circuit_breakers,
            "summary": summary
        }

    async def reset_all(self) -> Dict[str, Any]:
        """Reset all circuit breakers"""
        await self.registry.reset_all()
        return {
            "reset": True,
            "circuit_breakers_reset": list(self.registry.breakers.keys()),
            "message": "All circuit breakers reset successfully"
        }


# Global resilience registry
resilience_registry = ResilienceRegistry()
circuit_breaker_service = CircuitBreakerService()


class CircuitBreakerException(Exception):
    """Base exception for circuit breaker"""
    pass


class CircuitBreakerOpenException(CircuitBreakerException):
    """Exception raised when circuit breaker is open"""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Circuit breaker '{name}' is open")


class CircuitBreakerTimeoutException(CircuitBreakerException):
    """Exception raised when request times out"""

    def __init__(self, name: str, timeout: float):
        self.name = name
        self.timeout = timeout
        super().__init__(f"Request to '{name}' timed out after {timeout}s")


# Decorators for easy use
def circuit_breaker(name: str, config: CircuitBreakerConfig = None):
    """Decorator to apply circuit breaker to async function"""
    breaker = circuit_breaker_registry.get_or_create(name, config)

    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


def resilient_service(
    name: str,
    circuit_config: CircuitBreakerConfig = None,
    retry_config: RetryConfig = None,
    fallback_config: FallbackConfig = None
):
    """Decorator to apply full resilience (circuit breaker + retry + fallback)"""
    manager = resilience_registry.get_or_create(name, circuit_config, retry_config, fallback_config)

    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await manager.execute_resilient(func, *args, **kwargs)
        return wrapper
    return decorator


def with_retry(config: RetryConfig = None):
    """Decorator to apply retry mechanism"""
    retry = RetryMechanism(config)

    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await retry.execute_with_retry(func, *args, **kwargs)
        return wrapper
    return decorator


@asynccontextmanager
async def circuit_breaker_context(name: str, config: CircuitBreakerConfig = None):
    """Context manager for circuit breaker"""
    breaker = circuit_breaker_registry.get_or_create(name, config)

    async def dummy_call():
        # This is just to trigger the circuit breaker logic
        # The actual operation should be performed inside the context
        pass

    try:
        yield breaker
    except Exception as e:
        await breaker._on_failure()
        raise
    else:
        await breaker._on_success()


@asynccontextmanager
async def resilient_context(
    name: str,
    circuit_config: CircuitBreakerConfig = None,
    retry_config: RetryConfig = None,
    fallback_config: FallbackConfig = None
):
    """Context manager for full resilience"""
    manager = resilience_registry.get_or_create(name, circuit_config, retry_config, fallback_config)

    try:
        yield manager
    except Exception as e:
        # Error handling is managed by the resilience manager
        raise