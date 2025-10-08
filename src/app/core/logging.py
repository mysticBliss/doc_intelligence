import logging
import sys
import structlog
from typing import Optional

def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Configures and returns a structlog logger with enterprise-grade settings.

    Args:
        name: Hierarchical logger name (e.g., 'api.endpoints', 'processor.ocr')

    Returns:
        A configured structlog BoundLogger instance
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger(name)


class LoggerRegistry:
    """
    Enterprise logger registry with standardized naming conventions.

    This class provides factory methods for creating loggers with consistent
    hierarchical naming patterns across the application.
    """

    @staticmethod
    def get_api_logger(endpoint: str) -> structlog.stdlib.BoundLogger:
        """Get a logger for API endpoints."""
        return get_logger(f"api.{endpoint}")

    @staticmethod
    def get_processor_logger(processor_name: str) -> structlog.stdlib.BoundLogger:
        """Get a logger for processors."""
        return get_logger(f"processor.{processor_name}")

    @staticmethod
    def get_service_logger(service_name: str) -> structlog.stdlib.BoundLogger:
        """Get a logger for services."""
        return get_logger(f"service.{service_name}")

    @staticmethod
    def get_pipeline_logger() -> structlog.stdlib.BoundLogger:
        """Get a logger for pipeline execution."""
        return get_logger("pipeline.execution")

    @staticmethod
    def get_infrastructure_logger(component: str) -> structlog.stdlib.BoundLogger:
        """Get a logger for infrastructure components."""
        return get_logger(f"infrastructure.{component}")

    @staticmethod
    def get_security_logger() -> structlog.stdlib.BoundLogger:
        """Get a logger for security and audit events."""
        return get_logger("security.audit")

    @staticmethod
    def get_decorator_logger(processor_name: str, step_name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
        """Get a logger for decorator instrumentation."""
        if step_name:
            return get_logger(f"processor.{processor_name}.{step_name}")
        return get_logger(f"processor.{processor_name}")


# Convenience aliases for backward compatibility
def get_api_logger(endpoint: str) -> structlog.stdlib.BoundLogger:
    """Convenience function for API loggers."""
    return LoggerRegistry.get_api_logger(endpoint)

def get_processor_logger(processor_name: str) -> structlog.stdlib.BoundLogger:
    """Convenience function for processor loggers."""
    return LoggerRegistry.get_processor_logger(processor_name)

def get_service_logger(service_name: str) -> structlog.stdlib.BoundLogger:
    """Convenience function for service loggers."""
    return LoggerRegistry.get_service_logger(service_name)