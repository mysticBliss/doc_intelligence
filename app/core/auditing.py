import structlog
from app.domain.models import AuditEvent

logger = structlog.get_logger(__name__)


def log_audit_event(event: AuditEvent):
    """
    Logs an audit event in a structured format.

    In a production system, this could write to a dedicated audit trail,
    a message queue, or a time-series database. For now, it logs to stdout
    as a structured JSON log.
    """
    logger.info(
        "audit_event",
        event_type="api_request",
        **event.model_dump(exclude_none=True),
    )