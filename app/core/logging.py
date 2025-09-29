import logging
import sys
import structlog
from core.context import get_request_context

def correlation_id_processor(logger, method_name, event_dict):
    """Add correlation_id to the log record if it exists in the context."""
    context = get_request_context()
    if context and context.correlation_id:
        event_dict['correlation_id'] = context.correlation_id
    return event_dict

def configure_logging():
    """Configure structured logging for the application."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            correlation_id_processor,  # Add our custom processor
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )