"""
Logging configuration for Research Copilot
"""
import logging
import sys
from typing import Any, Dict

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

from ..config import settings


def setup_logging():
    """Setup structured logging"""
    if not STRUCTLOG_AVAILABLE:
        # Fallback to standard logging
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("logs/app.log", encoding='utf-8')
            ]
        )
        return

    # Configure structlog
    if settings.log_format == "json":
        # JSON logging for production
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, settings.log_level.upper())
            ),
            context_class=dict,
            logger_factory=structlog.WriteLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Human-readable logging for development
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, settings.log_level.upper())
            ),
            context_class=dict,
            logger_factory=structlog.WriteLoggerFactory(),
            cache_logger_on_first_use=True,
        )

    # Add file handler for structlog
    file_handler = logging.FileHandler("logs/app.log", encoding='utf-8')
    file_handler.setLevel(getattr(logging, settings.log_level.upper()))
    if settings.log_format == "json":
        file_handler.setFormatter(logging.Formatter('%(message)s'))
    else:
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/app.log", encoding='utf-8')
        ]
    )

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("opensearch").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)


def get_logger(name: str) -> Any:
    """Get a logger instance"""
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    else:
        return logging.getLogger(name)