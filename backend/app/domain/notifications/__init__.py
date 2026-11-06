from app.domain.notifications.errors import EmailSendError, sanitize_error
from app.domain.notifications.ports import EmailSender
from app.domain.notifications.rules import decide_delivery
from app.domain.notifications.types import DeliveryDecision, DeliveryOutcome, OutgoingEmail

__all__ = [
    "DeliveryDecision",
    "DeliveryOutcome",
    "EmailSendError",
    "EmailSender",
    "OutgoingEmail",
    "decide_delivery",
    "sanitize_error",
]
