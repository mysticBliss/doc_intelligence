from contextvars import ContextVar
from typing import Optional
from domain.models import RequestContext
import uuid

# The context variable to hold the request context.
_request_context_var: ContextVar[Optional[RequestContext]] = ContextVar(
    "request_context", default=None
)


def set_request_context(context: RequestContext) -> None:
    """Sets the request context for the current async task."""
    _request_context_var.set(context)


def get_request_context() -> Optional[RequestContext]:
    """Gets the request context for the current async task."""
    return _request_context_var.get()


def get_correlation_id() -> str:
    """Gets the correlation ID from the current request context."""
    context = get_request_context()
    if context:
        return context.correlation_id
    # Fallback to a new UUID if the context is not available,
    # though in a properly configured middleware setup, this should not happen.
    return str(uuid.uuid4())