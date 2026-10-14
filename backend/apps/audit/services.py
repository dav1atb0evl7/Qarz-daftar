import logging
from .models import AuditLog, AuditAction, AuditSource
from .middleware import get_current_request

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {'password', 'password_confirm', 'token', 'secret', 'secret_key', 'refresh'}


def sanitize_payload(data):
    if not isinstance(data, dict):
        return data
    sanitized = {}
    for k, v in data.items():
        if any(s in k.lower() for s in SENSITIVE_KEYS):
            sanitized[k] = "******"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_payload(v)
        else:
            sanitized[k] = str(v)
    return sanitized


class AuditService:
    @staticmethod
    def log_action(
        action,
        entity_type,
        entity_id,
        user=None,
        shop=None,
        request=None,
        changes=None,
        source=AuditSource.WEB
    ):
        """
        Creates an immutable audit log record. Never breaks caller execution.
        """
        try:
            req = request or get_current_request()
            ip = getattr(req, 'client_ip', None) if req else None
            user_agent = getattr(req, 'client_user_agent', None) if req else None

            if not user and req and hasattr(req, 'user') and req.user.is_authenticated:
                user = req.user

            sanitized_changes = sanitize_payload(changes or {})

            AuditLog.objects.create(
                shop=shop,
                user=user,
                action=action,
                source=source,
                entity_type=entity_type,
                entity_id=str(entity_id),
                changes=sanitized_changes,
                ip_address=ip,
                user_agent=user_agent
            )
        except Exception as e:
            logger.error("Failed to write audit log: %s", e)
